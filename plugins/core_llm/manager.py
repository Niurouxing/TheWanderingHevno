# plugins/core_llm/manager.py

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, AsyncIterator, Any, Tuple
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
    """
    [核心修改] 存储单个 API 密钥及其并发状态信息。
    """
    key_string: str
    max_concurrency: int = 1  # [新增] 该密钥允许的最大并发数
    status: KeyStatus = KeyStatus.AVAILABLE
    rate_limit_until: float = 0.0
    # [新增] 每个密钥实例拥有自己的信号量
    _semaphore: asyncio.Semaphore = field(init=False, repr=False)

    def __post_init__(self):
        """在对象初始化后，根据并发数创建独立的信号量。"""
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

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

    def load_keys_from_env(self, env_variable: str) -> List[Tuple[str, int]]:
        """
        [核心修改] 从指定的环境变量中加载 API 密钥及其并发配置。
        """
        keys_str = os.getenv(env_variable)
        if not keys_str:
            return []
        
        parsed_keys = []
        key_entries = [key.strip() for key in keys_str.split(',') if key.strip()]
        for entry in key_entries:
            if ':' in entry:
                parts = entry.rsplit(':', 1)
                key = parts[0]
                try:
                    concurrency = int(parts[1])
                    parsed_keys.append((key, max(1, concurrency))) # 保证并发数至少为1
                except ValueError:
                    # 如果冒号后的部分不是数字，则将其视为密钥的一部分
                    parsed_keys.append((entry, 1))
            else:
                # 没有冒号，使用默认并发数1
                parsed_keys.append((entry, 1))

        return parsed_keys


class ProviderKeyPool:
    """[核心修改] 管理特定提供商的一组 API 密钥，现在支持密钥级并发。"""
    def __init__(self, provider_name: str, keys_with_concurrency: List[Tuple[str, int]]):
        self.provider_name = provider_name
        # [修改] 使用新的 KeyInfo 构造方式
        self._keys: List[KeyInfo] = [
            KeyInfo(key_string=k, max_concurrency=c) for k, c in keys_with_concurrency
        ]
        # [移除] 不再需要池级别的信号量
        # self._semaphore = asyncio.Semaphore(len(self._keys))

    @asynccontextmanager
    async def acquire_key(self) -> AsyncIterator[KeyInfo]:
        """
        [核心重构] 并发地尝试获取池中任何一个可用密钥的许可。
        """
        while True:
            # 1. 筛选出所有当前健康状况良好的密钥
            available_keys = [key for key in self._keys if key.is_available()]
            
            if not available_keys:
                # 如果所有密钥都被禁用或限速，则等待一段时间后重试
                await asyncio.sleep(1) 
                continue

            # 2. 创建一个任务列表，每个任务都尝试获取一个可用密钥的信号量
            tasks = [asyncio.create_task(key._semaphore.acquire(), name=key.key_string) for key in available_keys]
            
            # 3. 等待第一个成功的任务完成
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # 4. 取消所有其他未完成的等待任务，避免资源泄露
            for task in pending:
                task.cancel()

            # 5. 获取成功获取到信号量的那个任务和对应的KeyInfo
            acquired_task = done.pop()
            acquired_key_string = acquired_task.get_name()
            acquired_key_info = next((k for k in available_keys if k.key_string == acquired_key_string), None)

            if acquired_key_info:
                try:
                    # 成功获取，将密钥信息交由调用方使用
                    yield acquired_key_info
                    return # 任务完成，退出循环
                finally:
                    # 无论调用方代码块发生什么，最终都会释放这个特定密钥的信号量
                    acquired_key_info._semaphore.release()
            else:
                # 理论上不应该发生，但作为保险
                await asyncio.sleep(0.1)

    def get_key_by_string(self, key_string: str) -> Optional[KeyInfo]:
        for key in self._keys:
            if key.key_string == key_string:
                return key
        return None

    def get_key_count(self) -> int:
        return len(self._keys)

    def mark_as_rate_limited(self, key_string: str, duration_seconds: int = 60):
        key_info = self.get_key_by_string(key_string)
        if key_info:
            key_info.status = KeyStatus.RATE_LIMITED
            key_info.rate_limit_until = time.time() + duration_seconds
            logger.info(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' marked as rate-limited for {duration_seconds}s.")

    async def mark_as_banned(self, key_string: str):
        key_info = self.get_key_by_string(key_string)
        if key_info and key_info.status != KeyStatus.BANNED:
            key_info.status = KeyStatus.BANNED
            # 当密钥被禁用时，我们不需要操作它的信号量，
            # is_available() 检查会阻止它被再次选中。
            logger.warning(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' permanently banned.")


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
        # [修改] 现在加载的是带并发信息的数据
        keys_with_concurrency = self._cred_manager.load_keys_from_env(env_variable)
        self._pools[provider_name] = ProviderKeyPool(provider_name, keys_with_concurrency)
        key_count = len(keys_with_concurrency)
        if key_count > 0:
            logger.info(f"Registered provider '{provider_name}' with {key_count} keys from '{env_variable}'.")
        else:
            logger.info(f"Registered provider '{provider_name}' with 0 keys (env var '{env_variable}' is empty or not set). Pool is ready.")

    def reload_keys(self, provider_name: str):
        if provider_name not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_name}' is not registered.")
        
        env_variable = self._provider_env_vars[provider_name]
        load_dotenv(dotenv_path=self._dotenv_path, override=True)
        
        # [修改]
        keys_with_concurrency = self._cred_manager.load_keys_from_env(env_variable)
        self._pools[provider_name] = ProviderKeyPool(provider_name, keys_with_concurrency)
        logger.info(f"Reloaded provider '{provider_name}' with {len(keys_with_concurrency)} keys from '{env_variable}'.")

    def add_key_to_provider(self, provider_name: str, new_key_entry: str):
        """
        [核心修改] 向 .env 添加一个新的密钥条目。
        new_key_entry 可以是 'mykey' 或 'mykey:10' 的格式。
        """
        if provider_name not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_name}' is not registered.")
        
        env_var = self._provider_env_vars[provider_name]
        current_keys_str = get_key(self._dotenv_path, env_var) or ""
        # 我们比较时不考虑并发数
        key_part_to_add = new_key_entry.split(':', 1)[0]
        
        keys = [k.strip() for k in current_keys_str.split(',') if k.strip()]
        existing_key_parts = [k.split(':', 1)[0] for k in keys]

        if key_part_to_add in existing_key_parts:
            logger.warning(f"Key '{key_part_to_add}' already exists for provider '{provider_name}'. Skipping.")
            return

        keys.append(new_key_entry)
        set_key(self._dotenv_path, env_var, ",".join(keys))
        logger.info(f"Successfully wrote new key entry to .env for provider '{provider_name}'.")
        self.reload_keys(provider_name) 

    def remove_key_from_provider(self, provider_name: str, key_suffix_to_remove: str):
        """
        [核心修改] 移除密钥时，只匹配密钥字符串部分。
        """
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
        for key_entry in keys:
            key_part = key_entry.split(':', 1)[0]
            if key_part.endswith(key_suffix_to_remove):
                key_found = True
            else:
                updated_keys.append(key_entry)
        
        if not key_found:
            logger.warning(f"Key with suffix '...{key_suffix_to_remove}' not found for provider '{provider_name}'.")
            return

        if not updated_keys:
            unset_key(self._dotenv_path, env_var)
            logger.info(f"Removed last key for '{env_var}' from .env file.")
        else:
            set_key(self._dotenv_path, env_var, ",".join(updated_keys))
            logger.info(f"Removed key entry ending in '...{key_suffix_to_remove}' from .env file.")
        
        self.reload_keys(provider_name)

    def update_key_concurrency(self, provider_name: str, key_suffix: str, new_concurrency: int):
        """
        更新指定密钥的并发数。
        """
        if provider_name not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_name}' is not registered.")

        env_var = self._provider_env_vars[provider_name]
        current_keys_str = get_key(self._dotenv_path, env_var) or ""
        keys = [k.strip() for k in current_keys_str.split(',') if k.strip()]

        updated_keys = []
        key_found = False
        
        for key_entry in keys:
            key_part = key_entry.split(':', 1)[0]
            if key_part.endswith(key_suffix):
                # 找到要更新的密钥，更新其并发数
                updated_keys.append(f"{key_part}:{new_concurrency}")
                key_found = True
                logger.info(f"Updated concurrency for key ending in '...{key_suffix}' to {new_concurrency}")
            else:
                updated_keys.append(key_entry)
        
        if not key_found:
            raise ValueError(f"Key with suffix '...{key_suffix}' not found for provider '{provider_name}'.")

        # 更新 .env 文件
        set_key(self._dotenv_path, env_var, ",".join(updated_keys))
        logger.info(f"Updated key concurrency in .env file for provider '{provider_name}'.")
        
        # 重新加载密钥池
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

    def update_provider_config(self, provider_id: str, new_config: Dict[str, Any]):
        if provider_id not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_id}' not registered, cannot update.")

        prefix = f"PROVIDER_{provider_id.upper()}_"
        
        try:
            set_key(self._dotenv_path, f"{prefix}TYPE", new_config['type'])
            set_key(self._dotenv_path, f"{prefix}BASE_URL", new_config['base_url'])

            model_mapping_key = f"{prefix}MODEL_MAPPING"
            if new_config.get('model_mapping'):
                mapping_str = ",".join([f"{k}:{v}" for k, v in new_config['model_mapping'].items()])
                set_key(self._dotenv_path, model_mapping_key, mapping_str)
            else:
                unset_key(self._dotenv_path, model_mapping_key)
            
            logger.info(f"Successfully updated configuration for provider '{provider_id}' in .env.")

        except Exception as e:
            raise IOError(f"Failed to write updated provider config to .env for '{provider_id}': {e}") from e

    def add_provider_config(self, provider_id: str, config: Dict[str, Any]):
        current_providers_str = get_key(self._dotenv_path, "HEVNO_LLM_PROVIDERS") or ""
        provider_ids = [p.strip() for p in current_providers_str.split(',') if p.strip()]
        if provider_id in provider_ids:
            raise ValueError(f"Provider with ID '{provider_id}' already exists in HEVNO_LLM_PROVIDERS.")

        if provider_id in self._provider_env_vars:
            raise ValueError(f"Provider with ID '{provider_id}' already registered in memory.")

        provider_ids.append(provider_id)
        
        prefix = f"PROVIDER_{provider_id.upper()}_"
        keys_env_var = f"{prefix}API_KEYS"
        
        config_to_write = {
            "HEVNO_LLM_PROVIDERS": ",".join(provider_ids),
            f"{prefix}TYPE": config['type'],
            f"{prefix}BASE_URL": config['base_url'],
            f"{prefix}KEYS_ENV": keys_env_var,
        }
        if config.get('model_mapping'):
            mapping_str = ",".join([f"{k}:{v}" for k, v in config['model_mapping'].items()])
            config_to_write[f"{prefix}MODEL_MAPPING"] = mapping_str
        
        try:
            for key, value in config_to_write.items():
                set_key(self._dotenv_path, key, value)
            if not get_key(self._dotenv_path, keys_env_var):
                set_key(self._dotenv_path, keys_env_var, "")

            logger.info(f"Successfully wrote configuration for new provider '{provider_id}' to .env.")
        except Exception as e:
            for key in config_to_write:
                unset_key(self._dotenv_path, key)
            raise IOError(f"Failed to write provider config to .env: {e}") from e

    def remove_provider_config(self, provider_id: str):
        if provider_id not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_id}' not registered, cannot remove.")

        current_providers_str = get_key(self._dotenv_path, "HEVNO_LLM_PROVIDERS") or ""
        provider_ids = [p.strip() for p in current_providers_str.split(',') if p.strip() and p != provider_id]
        
        if not provider_ids:
            unset_key(self._dotenv_path, "HEVNO_LLM_PROVIDERS")
        else:
            set_key(self._dotenv_path, "HEVNO_LLM_PROVIDERS", ",".join(provider_ids))

        prefix = f"PROVIDER_{provider_id.upper()}_"
        keys_to_remove = [
            f"{prefix}TYPE",
            f"{prefix}BASE_URL",
            f"{prefix}KEYS_ENV",
            f"{prefix}MODEL_MAPPING",
            self._provider_env_vars[provider_id]
        ]
        for key in keys_to_remove:
            unset_key(self._dotenv_path, key)
        
        logger.info(f"Successfully removed all .env configuration for provider '{provider_id}'.")