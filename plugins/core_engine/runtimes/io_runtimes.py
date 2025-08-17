# plugins/core_engine/runtimes/io_runtimes.py
import logging
from typing import Dict, Any, Literal, Type
from pydantic import BaseModel, Field

from ..contracts import ExecutionContext, RuntimeInterface

logger = logging.getLogger(__name__)

class InputRuntime(RuntimeInterface):
    """
    system.io.input: 将一个静态或动态生成的值注入到节点管道中。
    作为节点内部数据处理流程最基础的“数据源”。
    """
    class ConfigModel(BaseModel):
        value: Any = Field(..., description="要注入到管道中的值，可以是任何类型，支持宏。")

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
            return {"output": validated_config.value}
        except Exception as e:
            return {"error": f"Invalid configuration for system.io.input: {e}"}

class LogRuntime(RuntimeInterface):
    """
    system.io.log: 向后端日志系统输出一条消息。
    提供一个标准化的、用于调试图执行流程的工具。
    """
    LOG_LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    class ConfigModel(BaseModel):
        message: str = Field(..., description="要记录的日志消息，支持宏。")
        level: Literal["debug", "info", "warning", "error", "critical"] = Field(
            default="info",
            description="日志的级别。"
        )

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
            
            level = self.LOG_LEVELS.get(validated_config.level, logging.INFO)
            
            runtime_logger = logging.getLogger("hevno.runtime.log")
            runtime_logger.log(level, validated_config.message)
            
            return {}
        except Exception as e:
            # Pydantic validation errors are helpful here
            return {"error": f"Invalid configuration for system.io.log: {e}"}