# plugins/core_engine/__init__.py
import logging
from typing import Dict, Any

from backend.core.contracts import Container, HookManager

# 导入本插件提供的服务和组件
from .engine import ExecutionEngine
from .registry import RuntimeRegistry
from .state import SnapshotStore
from .runtimes.base_runtimes import InputRuntime, SetWorldVariableRuntime
from .runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_runtime_registry(container: Container, hook_manager: HookManager) -> RuntimeRegistry:
    """工厂：创建并填充运行时注册表。"""
    registry = RuntimeRegistry()
    
    # 1. 注册本插件内置的运行时
    base_runtimes = {
        "system.input": InputRuntime,
        "system.set_world_var": SetWorldVariableRuntime,
        "system.execute": ExecuteRuntime,
        "system.call": CallRuntime,
        "system.map": MapRuntime,
    }
    for name, runtime_class in base_runtimes.items():
        registry.register(name)(runtime_class) # 使用装饰器模式注册

    # 2. 【关键】通过钩子，从其他插件收集运行时
    # 注意：这是一个同步的包装器，用于在异步钩子之上
    async def collect_runtimes_task():
        # 初始字典为空，让钩子实现去填充
        other_runtimes = await hook_manager.filter("collect_runtimes", {})
        for name, runtime_class in other_runtimes.items():
             registry.register(name)(runtime_class)
    
    # 在工厂方法中运行这个一次性的异步任务
    import asyncio
    asyncio.run(collect_runtimes_task())
    
    return registry

def _create_execution_engine(container: Container) -> ExecutionEngine:
    """工厂：创建执行引擎，并注入其依赖。"""
    # 从容器中解析它需要的服务
    runtime_registry = container.resolve("runtime_registry")
    llm_service = container.resolve("llm_service") # 从 core-llm 插件获取
    hook_manager = container.resolve("hook_manager") # 从平台核心获取

    # 组装 services 字典
    services = {
        "llm": llm_service
    }
    
    return ExecutionEngine(
        registry=runtime_registry,
        services=services,
        hook_manager=hook_manager
    )

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-engine] 插件...")

    # 注册核心服务到 DI 容器
    # 注意它们的依赖关系，容器会自动处理
    container.register("snapshot_store", lambda: SnapshotStore())
    container.register("sandbox_store", lambda: {}) # 简单的字典存储
    
    # 将 hook_manager 也注册到容器，方便工厂函数访问
    container.register("hook_manager", lambda: hook_manager)
    
    container.register("runtime_registry", 
        lambda c: _create_runtime_registry(c, hook_manager))
        
    container.register("execution_engine", _create_execution_engine)
    
    logger.info("插件 [core-engine] 注册成功。")