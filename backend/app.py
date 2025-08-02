# backend/app.py

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.loader import PluginLoader

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动阶段 ---
    container = Container()
    hook_manager = HookManager()

    # 1. 注册平台核心服务
    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)

    # 2. 加载插件（插件此时仅注册工厂和同步钩子）
    loader = PluginLoader(container, hook_manager)
    loader.load_plugins()
    
    logger = logging.getLogger(__name__)
    logger.info("--- FastAPI Application Assembly ---")

    # 3. 将核心服务附加到 app.state，以便依赖注入函数可以访问
    app.state.container = container
    # hook_manager 不再需要直接附加，因为可以通过容器获取

    # 4. 【关键】触发异步服务初始化钩子
    #    这会填充 Auditor, RuntimeRegistry 等
    logger.info("Triggering 'services_post_register' for async initializations...")
    await hook_manager.trigger('services_post_register', container=container)
    logger.info("Async service initialization complete.")

    # 5. 【关键】平台核心负责收集并装配 API 路由
    logger.info("Collecting API routers from all plugins...")
    # 通过钩子收集所有由插件提供的 APIRouter 实例
    routers_to_add: list[APIRouter] = await hook_manager.filter("collect_api_routers", [])
    
    if routers_to_add:
        logger.info(f"Collected {len(routers_to_add)} router(s). Adding to application...")
        for router in routers_to_add:
            app.include_router(router)
            logger.debug(f"Added router: prefix='{router.prefix}', tags={router.tags}")
    else:
        logger.warning("No API routers were collected from plugins.")
    
    # 6. 触发最终启动完成钩子
    await hook_manager.trigger('app_startup_complete', app=app, container=container)
    
    logger.info("--- Hevno Engine Ready ---")
    yield
    # --- 关闭阶段 ---
    logger.info("--- Hevno Engine Shutting Down ---")
    await hook_manager.trigger('app_shutdown', app=app)


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