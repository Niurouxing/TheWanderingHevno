# plugins/core_llm/manager.py

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, AsyncIterator
from dotenv import find_dotenv, get_key, set_key, unset_key, load_dotenv


# --- Enums and Data Classes for Key State Management ---

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
    rate_limit_until: float = 0.0  # Unix timestamp until which the key is rate-limited

    def is_available(self) -> bool:
        """检查密钥当前是否可用。"""
        if self.status == KeyStatus.BANNED:
            return False
        if self.status == KeyStatus.RATE_LIMITED:
            if time.time() < self.rate_limit_until:
                return False
            # 如果限速时间已过，自动恢复为可用
            self.status = KeyStatus.AVAILABLE
            self.rate_limit_until = 0.0
        return self.status == KeyStatus.AVAILABLE


# --- Core Manager Components ---

class CredentialManager:
    """负责从环境变量中安全地加载和解析密钥。"""

    def load_keys_from_env(self, env_variable: str) -> List[str]:
        """
        从指定的环境变量中加载 API 密钥。
        密钥应以逗号分隔。

        :param env_variable: 环境变量的名称 (e.g., 'GEMINI_API_KEYS').
        :return: 一个包含 API 密钥字符串的列表。
        """
        keys_str = os.getenv(env_variable)
        if not keys_str:
            # 这不再是一个警告，而是一个正常情况
            return []
        
        # 按逗号分割，并去除每个密钥前后的空白字符
        keys = [key.strip() for key in keys_str.split(',') if key.strip()]
        return keys


class ProviderKeyPool:
    """
    管理特定提供商（如 'gemini'）的一组 API 密钥。
    内置并发控制和密钥选择逻辑。
    """
    def __init__(self, provider_name: str, keys: List[str]):
        # [FIX] 移除对空列表的错误检查，允许创建空的密钥池
        self.provider_name = provider_name
        self._keys: List[KeyInfo] = [KeyInfo(key_string=k) for k in keys]
        
        # 使用 Semaphore 控制对该提供商的并发请求数量，如果无密钥则为0
        self._semaphore = asyncio.Semaphore(len(self._keys))

    def _get_next_available_key(self) -> Optional[KeyInfo]:
        """循环查找下一个可用的密钥。"""
        # 简单的轮询策略
        for key_info in self._keys:
            if key_info.is_available():
                return key_info
        return None

    def get_key_by_string(self, key_string: str) -> Optional[KeyInfo]:
        """按密钥字符串查找 KeyInfo 对象。主要用于测试。"""
        for key in self._keys:
            if key.key_string == key_string:
                return key
        return None


    def get_key_count(self) -> int:
        """返回池中密钥的总数。"""
        return len(self._keys)
        

    @asynccontextmanager
    async def acquire_key(self) -> AsyncIterator[KeyInfo]:
        """
        一个安全的异步上下文管理器，用于获取和释放密钥。
        这是与该池交互的主要方式。

        :yields: 一个可用的 KeyInfo 对象。
        :raises asyncio.TimeoutError: 如果在指定时间内无法获取密钥。
        :raises RuntimeError: 如果池中已无任何可用密钥。
        """
        # 1. 获取信号量，这会阻塞直到有空闲的“插槽”
        await self._semaphore.acquire()

        try:
            # 2. 从池中选择一个当前可用的密钥
            key_info = self._get_next_available_key()
            if not key_info:
                # 这种情况理论上不应该发生，因为信号量应该反映可用密钥数
                # 但作为防御性编程，我们处理它
                raise RuntimeError(f"No available keys in pool '{self.provider_name}' despite acquiring semaphore.")
            
            # 3. 将密钥提供给调用者
            yield key_info
        finally:
            # 4. 无论发生什么，都释放信号量
            self._semaphore.release()

    def mark_as_rate_limited(self, key_string: str, duration_seconds: int = 60):
        """标记一个密钥为被限速状态。"""
        for key in self._keys:
            if key.key_string == key_string:
                key.status = KeyStatus.RATE_LIMITED
                key.rate_limit_until = time.time() + duration_seconds
                print(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' marked as rate-limited for {duration_seconds}s.")
                break

    async def mark_as_banned(self, key_string: str):
        """永久性地标记一个密钥为被禁用，并减少并发信号量。"""
        for key in self._keys:
            if key.key_string == key_string and key.status != KeyStatus.BANNED:
                key.status = KeyStatus.BANNED
                # 关键一步：永久性地减少一个并发“插槽”
                # 我们通过尝试获取然后不释放来实现
                # 注意：这假设信号量初始值与密钥数相同
                await self._semaphore.acquire()
                print(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' permanently banned. Concurrency reduced.")
                break


class KeyPoolManager:
    """
    顶层管理器，现在还负责协调对 .env 文件的读写。
    """
    def __init__(self, credential_manager: CredentialManager):
        self._pools: Dict[str, ProviderKeyPool] = {}
        self._cred_manager = credential_manager
        self._provider_env_vars: Dict[str, str] = {}
        # [FIX] 如果 .env 文件不存在，则定义其在当前工作目录的路径
        self._dotenv_path = find_dotenv()
        if not self._dotenv_path:
            self._dotenv_path = os.path.join(os.getcwd(), '.env')

    def register_provider(self, provider_name: str, env_variable: str):
        self._provider_env_vars[provider_name] = env_variable
        keys = self._cred_manager.load_keys_from_env(env_variable)
        
        # [FIX] 无论是否有密钥，都为提供商创建一个池
        self._pools[provider_name] = ProviderKeyPool(provider_name, keys)
        
        if keys:
            print(f"Registered provider '{provider_name}' with {len(keys)} keys from '{env_variable}'.")
        else:
            print(f"Registered provider '{provider_name}' with 0 keys (env var '{env_variable}' is empty or not set). Pool is ready.")

    def reload_keys(self, provider_name: str):
        """从 .env 文件重新加载指定提供商的密钥，并更新内存中的密钥池。"""
        if provider_name not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_name}' is not registered.")
        
        # [FIX] 强制从文件系统重新加载环境变量到当前进程
        load_dotenv(dotenv_path=self._dotenv_path, override=True)
        
        env_var = self._provider_env_vars[provider_name]
        keys = self._cred_manager.load_keys_from_env(env_var)
        
        # 重新创建密钥池以反映最新状态
        self._pools[provider_name] = ProviderKeyPool(provider_name, keys)
        print(f"Reloaded provider '{provider_name}' with {len(keys)} keys from '{env_variable}'.")

    def add_key_to_provider(self, provider_name: str, new_key: str):
        # [FIX] `set_key` 会自动创建 .env 文件，不再需要手动检查
        if provider_name not in self._provider_env_vars:
            raise ValueError(f"Provider '{provider_name}' is not registered.")
        
        env_var = self._provider_env_vars[provider_name]
        current_keys_str = get_key(self._dotenv_path, env_var) or ""
        keys = [k.strip() for k in current_keys_str.split(',') if k.strip()]

        if new_key in keys:
            print(f"Key already exists for provider '{provider_name}'. Skipping.")
            return

        keys.append(new_key)
        set_key(self._dotenv_path, env_var, ",".join(keys))
        self.reload_keys(provider_name) # 立即重载

    def remove_key_from_provider(self, provider_name: str, key_suffix_to_remove: str):
        # [FIX] 确保文件存在性被 `python-dotenv` 库处理
        if not os.path.exists(self._dotenv_path):
             print(f"Cannot remove key, .env file not found at {self._dotenv_path}.")
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
            print(f"Key with suffix '...{key_suffix_to_remove}' not found for provider '{provider_name}'.")
            return

        if not updated_keys:
            # 如果列表为空，我们移除这个环境变量
            unset_key(self._dotenv_path, env_var)
        else:
            set_key(self._dotenv_path, env_var, ",".join(updated_keys))
        
        self.reload_keys(provider_name) # 立即重载

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