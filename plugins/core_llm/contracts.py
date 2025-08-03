# plugins/core_llm/contracts.py

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

# --- Enums for Status and Error Types (公共契约) ---

class LLMResponseStatus(str, Enum):
    """定义 LLM 响应的标准化状态。"""
    SUCCESS = "success"
    FILTERED = "filtered"
    ERROR = "error"


class LLMErrorType(str, Enum):
    """定义标准化的 LLM 错误类型，用于驱动重试和故障转移逻辑。"""
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    PROVIDER_ERROR = "provider_error"
    NETWORK_ERROR = "network_error"
    INVALID_REQUEST_ERROR = "invalid_request_error"
    UNKNOWN_ERROR = "unknown_error"


# --- Core Data Models (公共契约) ---

class LLMError(BaseModel):
    """一个标准化的错误对象，用于封装来自任何提供商的错误信息。"""
    error_type: LLMErrorType
    message: str
    is_retryable: bool
    retry_after_seconds: Optional[int] = None
    provider_details: Optional[Dict[str, Any]] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """一个标准化的响应对象，用于封装来自任何提供商的成功、过滤或错误结果。"""
    status: LLMResponseStatus
    content: Optional[str] = None
    model_name: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    error_details: Optional[LLMError] = None


# --- Custom Exception (公共契约) ---

class LLMRequestFailedError(Exception):
    """在所有重试和故障转移策略都用尽后，由 LLMService 抛出的最终异常。"""
    def __init__(self, message: str, last_error: Optional[LLMError] = None):
        super().__init__(message)
        self.last_error = last_error

    def __str__(self):
        if self.last_error:
            return f"{super().__str__()}\nLast known error ({self.last_error.error_type.value}): {self.last_error.message}"
        return super().__str__()


# --- Service Interface (公共契约) ---

class LLMServiceInterface(ABC):
    """
    定义了 LLM 网关服务必须提供的核心能力的抽象接口。
    其他插件应该依赖于这个接口，而不是具体的 LLMService 类。
    """
    @abstractmethod
    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs: Any
    ) -> LLMResponse:
        """
        向指定的 LLM 发起请求，并处理重试逻辑。
        """
        raise NotImplementedError