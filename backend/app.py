# backend/app.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from backend.container import Container
from backend.core.hooks import HookManager # <-- 确认导入
from backend.core.loader import PluginLoader
from backend.core.tasks import BackgroundTaskManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动阶段 ---
    container = Container()
    # 核心变更：在创建时就注入 container
    hook_manager = HookManager(container)

    # 1. 注册平台核心服务
    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)
    
    task_manager = BackgroundTaskManager(container)
    container.register("task_manager", lambda: task_manager, singleton=True)
    # 【新】将 task_manager 也加入钩子系统的共享上下文
    hook_manager.add_shared_context("task_manager", task_manager)


    # 2. 加载插件
    loader = PluginLoader(container, hook_manager)
    loader.load_plugins()
    
    logger = logging.getLogger(__name__)
    logger.info("--- FastAPI 应用组装 ---")

    # 3. 将核心服务附加到 app.state
    app.state.container = container
    # 将 app 实例也加入钩子系统的共享上下文
    hook_manager.add_shared_context("app", app)

    # 4. 触发异步服务初始化钩子
    # 调用方式保持不变，但现在它会自动注入 container
    logger.info("正在为异步初始化触发 'services_post_register' 钩子...")
    await hook_manager.trigger('services_post_register')
    logger.info("异步服务初始化完成。")

    # 启动后台工作者
    task_manager.start()

    # 5. 平台核心负责收集并装配 API 路由
    logger.info("正在从所有插件收集 API 路由...")
    # 调用方式保持不变，但现在它会自动注入 container
    routers_to_add: list[APIRouter] = await hook_manager.filter("collect_api_routers", [])
    
    if routers_to_add:
        logger.info(f"已收集到 {len(routers_to_add)} 个路由。正在添加到应用中...")
        for router in routers_to_add:
            app.include_router(router)
            logger.debug(f"已添加路由: prefix='{router.prefix}', tags={router.tags}")
    else:
        logger.warning("未从插件中收集到任何 API 路由。")
    
    # 6. 触发最终启动完成钩子
    # 调用方式保持不变，但现在它会自动注入 app 和 container
    await hook_manager.trigger('app_startup_complete')
    
    logger.info("--- Hevno 引擎已就绪 ---")
    yield
    # --- 关闭阶段 ---
    logger.info("--- Hevno 引擎正在关闭 ---")
    
    await task_manager.stop()
    # 调用方式保持不变，但现在它会自动注入 app
    await hook_manager.trigger('app_shutdown')


def create_app() -> FastAPI:
    """应用工厂函数"""
    app = FastAPI(
        title="Hevno Engine (Plugin Architecture)",
        version="1.2.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app