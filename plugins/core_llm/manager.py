# plugins/core_llm/manager.py

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, AsyncIterator, Any
from dotenv import find_dotenv, get_key, set_key, unset_key, load_dotenv
import logging

logger = logging.getLogger(__name__)


class KeyStatus(str, Enum):
    """定义 API 密钥的健康状态。"""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    BANNED = "banned"


@dataclass
class KeyInfo:
    """存储单个 API 密钥及其状态信息。"""
    key_string: str
    status: KeyStatus = KeyStatus.AVAILABLE
    rate_limit_until: float = 0.0

    def is_available(self) -> bool:
        """检查密钥当前是否可用。"""
        if self.status == KeyStatus.BANNED:
            return False
        if self.status == KeyStatus.RATE_LIMITED:
            if time.time() < self.rate_limit_until:
                return False
            self.status = KeyStatus.AVAILABLE
            self.rate_limit_until = 0.0
        return self.status == KeyStatus.AVAILABLE


class CredentialManager:
    """负责从环境变量加载和解析密钥。"""

    def load_keys_from_env(self, env_variable: str) -> List[str]:
        """从指定的环境变量中加载 API 密钥。"""
        keys_str = os.getenv(env_variable)
        if not keys_str:
            return []
        
        keys = [key.strip() for key in keys_str.split(',') if key.strip()]
        return keys


class ProviderKeyPool:
    """管理特定提供商的一组 API 密钥。"""
    def __init__(self, provider_name: str, keys: List[str]):
        self.provider_name = provider_name
        self._keys: List[KeyInfo] = [KeyInfo(key_string=k) for k in keys]
        self._semaphore = asyncio.Semaphore(len(self._keys))

    def _get_next_available_key(self) -> Optional[KeyInfo]:
        for key_info in self._keys:
            if key_info.is_available():
                return key_info
        return None

    def get_key_by_string(self, key_string: str) -> Optional[KeyInfo]:
        for key in self._keys:
            if key.key_string == key_string:
                return key
        return None

    def get_key_count(self) -> int:
        return len(self._keys)
        
    @asynccontextmanager
    async def acquire_key(self) -> AsyncIterator[KeyInfo]:
        await self._semaphore.acquire()
        try:
            key_info = self._get_next_available_key()
            if not key_info:
                raise RuntimeError(f"No available keys in pool '{self.provider_name}' despite acquiring semaphore.")
            yield key_info
        finally:
            self._semaphore.release()

    def mark_as_rate_limited(self, key_string: str, duration_seconds: int = 60):
        for key in self._keys:
            if key.key_string == key_string:
                key.status = KeyStatus.RATE_LIMITED
                key.rate_limit_until = time.time() + duration_seconds
                logger.info(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' marked as rate-limited for {duration_seconds}s.")
                break

    async def mark_as_banned(self, key_string: str):
        for key in self._keys:
            if key.key_string == key_string and key.status != KeyStatus.BANNED:
                key.status = KeyStatus.BANNED
                # --- [核心修复] ---
                # 移除对信号量的操作。信号量只应该在 acquire/release 周期中被管理。
                # 密钥状态的改变已经足够让 acquire_key 逻辑跳过这个密钥。
                # await self._semaphore.acquire() 
                logger.warning(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' permanently banned.")
                break


class KeyPoolManager:
    """顶层管理器，负责协调 .env 的读写和内存状态。"""
    def __init__(self, credential_manager: CredentialManager):
        self._pools: Dict[str, ProviderKeyPool] = {}
        self._cred_manager = credential_manager
        self._provider_env_vars: Dict[str, str] = {}
        self._dotenv_path = find_dotenv()
        if not self._dotenv_path:
            self._dotenv_path = os.path.join(os.getcwd(), '.env')
            logger.warning(f".env file not found. Will attempt to create it at: {self._dotenv_path}")

    def register_provider(self, provider_name: str, env_variable: str):
        self._provider_env_vars[provider_name] = env_variable
        keys = self._cred_manager.load_keys_from_env(env_variable)
        self._pools[provider_name] = ProviderKeyPool(provider_name, keys)
        if keys:
            logger.info(f"Registered provider '{provider_name}' with {len(keys)} keys from '{env_variable}'.")
        else:
            logger.info(f"Registered provider '{provider_name}' with 0 keys (env var '{env_variable}' is empty or not set). Pool is ready.")

    def reload_keys(self, provider_name: str):
        if provider_name not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_name}' is not registered.")
        
        env_variable = self._provider_env_vars[provider_name]
        load_dotenv(dotenv_path=self._dotenv_path, override=True)
        
        keys = self._cred_manager.load_keys_from_env(env_variable)
        self._pools[provider_name] = ProviderKeyPool(provider_name, keys)
        logger.info(f"Reloaded provider '{provider_name}' with {len(keys)} keys from '{env_variable}'.")

    def add_key_to_provider(self, provider_name: str, new_key: str):
        if provider_name not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_name}' is not registered.")
        
        env_var = self._provider_env_vars[provider_name]
        current_keys_str = get_key(self._dotenv_path, env_var) or ""
        keys = [k.strip() for k in current_keys_str.split(',') if k.strip()]

        if new_key in keys:
            logger.warning(f"Key already exists for provider '{provider_name}'. Skipping.")
            return

        keys.append(new_key)
        set_key(self._dotenv_path, env_var, ",".join(keys))
        logger.info(f"Successfully wrote new key to .env for provider '{provider_name}'.")
        self.reload_keys(provider_name) 

    def remove_key_from_provider(self, provider_name: str, key_suffix_to_remove: str):
        if not os.path.exists(self._dotenv_path):
             logger.warning(f"Cannot remove key, .env file not found at {self._dotenv_path}.")
             return

        if provider_name not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_name}' is not registered.")

        env_var = self._provider_env_vars[provider_name]
        current_keys_str = get_key(self._dotenv_path, env_var) or ""
        keys = [k.strip() for k in current_keys_str.split(',') if k.strip()]

        key_found = False
        updated_keys = []
        for key in keys:
            if key.endswith(key_suffix_to_remove):
                key_found = True
            else:
                updated_keys.append(key)
        
        if not key_found:
            logger.warning(f"Key with suffix '...{key_suffix_to_remove}' not found for provider '{provider_name}'.")
            return

        # --- [核心修复] ---
        # 移除对 os.environ 的直接操作。
        # 让 load_dotenv(override=True) 在 reload_keys 中全权负责刷新。
        # if env_var in os.environ:
        #     del os.environ[env_var]
        #     logger.debug(f"Temporarily removed '{env_var}' from os.environ to ensure clean reload.")

        if not updated_keys:
            unset_key(self._dotenv_path, env_var)
            logger.info(f"Removed last key for '{env_var}' from .env file.")
        else:
            set_key(self._dotenv_path, env_var, ",".join(updated_keys))
            logger.info(f"Removed key ending in '...{key_suffix_to_remove}' from .env file.")
        
        # reload_keys 将会负责从更新后的 .env 文件中读取正确的状态
        self.reload_keys(provider_name)

    def get_pool(self, provider_name: str) -> Optional[ProviderKeyPool]:
        return self._pools.get(provider_name)

    @asynccontextmanager
    async def acquire_key(self, provider_name: str) -> AsyncIterator[KeyInfo]:
        pool = self.get_pool(provider_name)
        if not pool:
            raise ValueError(f"No key pool registered for provider '{provider_name}'.")
        
        async with pool.acquire_key() as key_info:
            yield key_info

    def mark_as_rate_limited(self, provider_name: str, key_string: str, duration_seconds: int = 60):
        pool = self.get_pool(provider_name)
        if pool:
            pool.mark_as_rate_limited(key_string, duration_seconds)

    async def mark_as_banned(self, provider_name: str, key_string: str):
        pool = self.get_pool(provider_name)
        if pool:
            await pool.mark_as_banned(key_string)

    def unregister_provider(self, provider_name: str):
        """注销提供商及其密钥池。"""
        if provider_name in self._pools:
            self._pools.pop(provider_name, None)
            self._provider_env_vars.pop(provider_name, None)
            logger.info(f"Unregistered provider '{provider_name}' and its key pool from KeyPoolManager.")
        else:
            logger.warning(f"Attempted to unregister a non-existent provider from KeyPoolManager: '{provider_name}'.")
    
    def get_custom_provider_config(self) -> Dict[str, Any]:
        load_dotenv(dotenv_path=self._dotenv_path, override=True)
        return {
            "base_url": os.getenv("OPENAI_CUSTOM_BASE_URL"),
            "model_mapping": os.getenv("OPENAI_CUSTOM_MODEL_MAPPING"),
        }

    def set_custom_provider_config(self, base_url: Optional[str], model_mapping: Optional[str]):
        # --- [核心修复] ---
        # 移除对 os.environ 的直接操作，让 load_dotenv(override=True) 在 reload_keys 中处理
        # if "OPENAI_CUSTOM_BASE_URL" in os.environ: 
        #     del os.environ["OPENAI_CUSTOM_BASE_URL"]
        # if "OPENAI_CUSTOM_MODEL_MAPPING" in os.environ: 
        #     del os.environ["OPENAI_CUSTOM_MODEL_MAPPING"]

        if base_url:
            set_key(self._dotenv_path, "OPENAI_CUSTOM_BASE_URL", base_url)
            logger.info(f"Set OPENAI_CUSTOM_BASE_URL in .env file.")
        else:
            unset_key(self._dotenv_path, "OPENAI_CUSTOM_BASE_URL")
            logger.info(f"Unset OPENAI_CUSTOM_BASE_URL from .env file.")
            
        if model_mapping:
            set_key(self._dotenv_path, "OPENAI_CUSTOM_MODEL_MAPPING", model_mapping)
            logger.info(f"Set OPENAI_CUSTOM_MODEL_MAPPING in .env file.")
        else:
            unset_key(self._dotenv_path, "OPENAI_CUSTOM_MODEL_MAPPING")
            logger.info(f"Unset OPENAI_CUSTOM_MODEL_MAPPING from .env file.")

        for provider_name in list(self._provider_env_vars.keys()):
            self.reload_keys(provider_name)
        logger.info("All provider pools have been reloaded after config change.")

    # --- [新增] ---
    def add_provider_config(self, provider_id: str, config: Dict[str, Any]):
        """
        向 .env 文件添加一个全新的提供商配置。
        这是一个原子性操作，如果失败则不应该留下部分配置。
        """
        # 1. 检查是否已在HEVNO_LLM_PROVIDERS中存在
        current_providers_str = get_key(self._dotenv_path, "HEVNO_LLM_PROVIDERS") or ""
        provider_ids = [p.strip() for p in current_providers_str.split(',') if p.strip()]
        if provider_id in provider_ids:
            raise ValueError(f"Provider with ID '{provider_id}' already exists in HEVNO_LLM_PROVIDERS.")

        # 2. 检查是否已在内存中注册
        if provider_id in self._provider_env_vars:
            raise ValueError(f"Provider with ID '{provider_id}' already registered in memory.")

        # 3. 更新 HEVNO_LLM_PROVIDERS 列表
        provider_ids.append(provider_id)
        
        # 4. 准备所有要写入的 .env 键值对
        prefix = f"PROVIDER_{provider_id.upper()}_"
        keys_env_var = f"{prefix}API_KEYS" # 约定：密钥的环境变量名是自动生成的
        
        config_to_write = {
            "HEVNO_LLM_PROVIDERS": ",".join(provider_ids),
            f"{prefix}TYPE": config['type'],
            f"{prefix}BASE_URL": config['base_url'],
            f"{prefix}KEYS_ENV": keys_env_var,
        }
        # Model mapping 是可选的
        if config.get('model_mapping'):
            mapping_str = ",".join([f"{k}:{v}" for k, v in config['model_mapping'].items()])
            config_to_write[f"{prefix}MODEL_MAPPING"] = mapping_str
        
        # 5. 执行写入
        try:
            for key, value in config_to_write.items():
                set_key(self._dotenv_path, key, value)
            # 还需要确保密钥变量存在，即使是空的
            if not get_key(self._dotenv_path, keys_env_var):
                set_key(self._dotenv_path, keys_env_var, "")

            logger.info(f"Successfully wrote configuration for new provider '{provider_id}' to .env.")
        except Exception as e:
            # 简单的回滚尝试
            for key in config_to_write:
                unset_key(self._dotenv_path, key)
            raise IOError(f"Failed to write provider config to .env: {e}") from e

    # --- [新增] ---
    def remove_provider_config(self, provider_id: str):
        """从 .env 文件中移除一个提供商的所有相关配置。"""
        if provider_id not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_id}' not registered, cannot remove.")

        # 1. 从 HEVNO_LLM_PROVIDERS 列表中移除
        current_providers_str = get_key(self._dotenv_path, "HEVNO_LLM_PROVIDERS") or ""
        provider_ids = [p.strip() for p in current_providers_str.split(',') if p.strip() and p != provider_id]
        
        if not provider_ids:
            unset_key(self._dotenv_path, "HEVNO_LLM_PROVIDERS")
        else:
            set_key(self._dotenv_path, "HEVNO_LLM_PROVIDERS", ",".join(provider_ids))

        # 2. 移除该提供商的所有特定变量
        prefix = f"PROVIDER_{provider_id.upper()}_"
        keys_to_remove = [
            f"{prefix}TYPE",
            f"{prefix}BASE_URL",
            f"{prefix}KEYS_ENV",
            f"{prefix}MODEL_MAPPING",
            self._provider_env_vars[provider_id] # 删除密钥本身的环境变量
        ]
        for key in keys_to_remove:
            unset_key(self._dotenv_path, key)
        
        logger.info(f"Successfully removed all .env configuration for provider '{provider_id}'.")