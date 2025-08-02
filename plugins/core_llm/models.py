# plugins/core_llm/models.py

from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


# --- Enums for Status and Error Types ---

class LLMResponseStatus(str, Enum):
    """定义 LLM 响应的标准化状态。"""
    SUCCESS = "success"
    FILTERED = "filtered"
    ERROR = "error"


class LLMErrorType(str, Enum):
    """定义标准化的 LLM 错误类型，用于驱动重试和故障转移逻辑。"""
    AUTHENTICATION_ERROR = "authentication_error"  # 密钥无效或权限不足
    RATE_LIMIT_ERROR = "rate_limit_error"          # 达到速率限制
    PROVIDER_ERROR = "provider_error"              # 服务商侧 5xx 或其他服务器错误
    NETWORK_ERROR = "network_error"                # 网络连接问题
    INVALID_REQUEST_ERROR = "invalid_request_error"  # 请求格式错误 (4xx)
    UNKNOWN_ERROR = "unknown_error"                # 未知或未分类的错误


# --- Core Data Models ---

class LLMError(BaseModel):
    """
    一个标准化的错误对象，用于封装来自任何提供商的错误信息。
    """
    error_type: LLMErrorType = Field(
        ...,
        description="错误的标准化类别。"
    )
    message: str = Field(
        ...,
        description="可读的错误信息。"
    )
    is_retryable: bool = Field(
        ...,
        description="此错误是否适合重试（例如，网络错误或某些服务端错误）。"
    )
    retry_after_seconds: Optional[int] = Field(
        default=None,
        description="如果提供商明确告知，需要等待多少秒后才能重试。"
    )
    provider_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="原始的、特定于提供商的错误细节，用于调试。"
    )


class LLMResponse(BaseModel):
    """
    一个标准化的响应对象，用于封装来自任何提供商的成功、过滤或错误结果。
    """
    status: LLMResponseStatus = Field(
        ...,
        description="响应的总体状态。"
    )
    content: Optional[str] = Field(
        default=None,
        description="LLM 生成的文本内容。仅在 status 为 'success' 时保证存在。"
    )
    model_name: Optional[str] = Field(
        default=None,
        description="实际用于生成此响应的模型名称。"
    )
    usage: Optional[Dict[str, int]] = Field(
        default=None,
        description="Token 使用情况统计，例如 {'prompt_tokens': 10, 'completion_tokens': 200}。"
    )
    error_details: Optional[LLMError] = Field(
        default=None,
        description="如果 status 为 'error'，则包含此字段以提供详细的错误信息。"
    )
    
    # 可以在这里添加一个验证器，确保在status为error时，error_details不为空
    # 但为了保持模型的简单性，我们暂时将此逻辑留给上层服务处理。


# --- Custom Exception ---

class LLMRequestFailedError(Exception):
    """
    在所有重试和故障转移策略都用尽后，由 LLMService 抛出的最终异常。
    """
    def __init__(self, message: str, last_error: Optional[LLMError] = None):
        """
        :param message: 对失败的总体描述。
        :param last_error: 导致最终失败的最后一个标准化错误对象。
        """
        super().__init__(message)
        self.last_error = last_error

    def __str__(self):
        if self.last_error:
            return (
                f"{super().__str__()}\n"  # <--- super().__str__() 会返回我们传入的 message
                f"Last known error ({self.last_error.error_type.value}): {self.last_error.message}"
            )
        return super().__str__()