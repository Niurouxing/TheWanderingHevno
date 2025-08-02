# plugins/example_logger/__init__.py
import logging
from backend.core.hooks import HookManager
from . import hooks

# 设置插件自己的日志记录器
logger = logging.getLogger(__name__)

def register_plugin(hook_manager: HookManager):
    """
    插件注册入口。
    引擎会在启动时调用此函数。
    """
    logger.info("Registering 'Example Logger' plugin...")
    
    # 注册一个通知型钩子
    hook_manager.add_implementation(
        "engine_step_start", 
        hooks.on_engine_step_start,
        priority=10,
        plugin_name="example_logger"
    )
    
    # 注册一个过滤型钩子
    hook_manager.add_implementation(
        "before_snapshot_create",
        hooks.on_before_snapshot_create,
        priority=10,
        plugin_name="example_logger"
    )

    logger.info("'Example Logger' plugin registered successfully.")