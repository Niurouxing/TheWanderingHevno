# plugins/core_engine/runtimes/io_runtimes.py
import logging
from typing import Dict, Any

from ..contracts import ExecutionContext, RuntimeInterface

logger = logging.getLogger(__name__)

class InputRuntime(RuntimeInterface):
    """
    system.io.input: 将一个静态或动态生成的值注入到节点管道中。
    作为节点内部数据处理流程最基础的“数据源”。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        return {"output": config.get("value")}

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

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        message = config.get("message")
        if message is None:
            raise ValueError("LogRuntime requires a 'message' field in its config.")

        level_str = config.get("level", "info").lower()
        level = self.LOG_LEVELS.get(level_str, logging.INFO)
        
        # 使用一个专用的 logger，可以方便地在日志配置中控制其输出
        runtime_logger = logging.getLogger("hevno.runtime.log")
        runtime_logger.log(level, str(message))
        
        return {}