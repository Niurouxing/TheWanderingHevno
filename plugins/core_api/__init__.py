# plugins/core_api/__init__.py
import logging

from backend.core.contracts import Container, HookManager
from .auditor import Auditor, AuditorRegistry, Reportable # 从本地导入
from .base_router import router as base_router
from .sandbox_router import router as sandbox_router

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_auditor(container: Container) -> Auditor:
    """工厂：创建并配置 Auditor 服务。"""
    # 1. 创建注册表
    registry = AuditorRegistry()

    # 2. 【关键】从容器中解析所有被标记为“reportable”的服务或组件
    #    这是一个高级 DI 模式，但我们可以先用一个简单的方式实现。
    #    目前，我们手动注册已知的报告器。
    #    TODO: 实现一个自动发现机制
    
    # 手动从其他插件解析并注册报告器
    # (这会隐式地创建对这些服务的依赖)
    # runtime_reporter = container.resolve("runtime_reporter") 
    # llm_reporter = container.resolve("llm_reporter")
    # sandbox_stats_reporter = container.resolve("sandbox_stats_reporter")
    
    # registry.register(runtime_reporter)
    # registry.register(llm_reporter)
    # registry.register(sandbox_stats_reporter)
    
    return Auditor(registry)

# --- 钩子实现 ---
async def add_own_routers(routers: list) -> list:
    """钩子实现：将本插件的路由添加到收集中。"""
    routers.append(base_router)
    routers.append(sandbox_router)
    logger.debug("Provided base_router and sandbox_router to the application.")
    return routers

def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-api] 插件...")

    # 1. 注册服务
    container.register("auditor", _create_auditor)
    logger.debug("服务 'auditor' 已注册。")

    # 2. 注册钩子实现
    # 这个插件既是 API 路由的提供者，也是收集者。
    # 它自己的 add_own_routers 应该在所有其他插件之后运行，
    # 以便它能首先添加自己的基础路由。
    hook_manager.add_implementation(
        "collect_api_routers", 
        add_own_routers, 
        priority=100, # 较高优先级，最后添加
        plugin_name="core-api"
    )
    logger.debug("钩子实现 'collect_api_routers' (for self) 已注册。")

    logger.info("插件 [core-api] 注册成功。")