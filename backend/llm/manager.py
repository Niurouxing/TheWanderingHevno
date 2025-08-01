# backend/llm/manager.py

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, AsyncIterator


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
            print(f"Warning: Environment variable '{env_variable}' not set. No keys loaded.")
            return []
        
        # 按逗号分割，并去除每个密钥前后的空白字符
        keys = [key.strip() for key in keys_str.split(',') if key.strip()]
        if not keys:
            print(f"Warning: Environment variable '{env_variable}' is set but contains no valid keys.")
        return keys


class ProviderKeyPool:
    """
    管理特定提供商（如 'gemini'）的一组 API 密钥。
    内置并发控制和密钥选择逻辑。
    """
    def __init__(self, provider_name: str, keys: List[str]):
        if not keys:
            raise ValueError(f"Cannot initialize ProviderKeyPool for '{provider_name}' with an empty key list.")
        
        self.provider_name = provider_name
        self._keys: List[KeyInfo] = [KeyInfo(key_string=k) for k in keys]
        
        # 使用 Semaphore 控制对该提供商的并发请求数量，初始值等于可用密钥数
        self._semaphore = asyncio.Semaphore(len(self._keys))

    def _get_next_available_key(self) -> Optional[KeyInfo]:
        """循环查找下一个可用的密钥。"""
        # 简单的轮询策略
        for key_info in self._keys:
            if key_info.is_available():
                return key_info
        return None

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
    顶层管理器，聚合了所有提供商的密钥池。
    这是上层服务（LLMService）与之交互的唯一入口。
    """
    def __init__(self, credential_manager: CredentialManager):
        self._pools: Dict[str, ProviderKeyPool] = {}
        self._cred_manager = credential_manager

    def register_provider(self, provider_name: str, env_variable: str):
        """

        从环境变量加载密钥，并为提供商创建一个密钥池。
        :param provider_name: 提供商的名称 (e.g., 'gemini').
        :param env_variable: 包含该提供商密钥的环境变量。
        """
        keys = self._cred_manager.load_keys_from_env(env_variable)
        if keys:
            self._pools[provider_name] = ProviderKeyPool(provider_name, keys)
            print(f"Registered provider '{provider_name}' with {len(keys)} keys from '{env_variable}'.")

    def get_pool(self, provider_name: str) -> Optional[ProviderKeyPool]:
        """获取指定提供商的密钥池。"""
        return self._pools.get(provider_name)

    # 为了方便上层服务调用，我们将核心方法直接暴露在这里
    
    @asynccontextmanager
    async def acquire_key(self, provider_name: str) -> AsyncIterator[KeyInfo]:
        """
        从指定提供商的池中获取一个密钥。
        """
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