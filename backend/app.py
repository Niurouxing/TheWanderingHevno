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
    # --- 应用启动 ---
    container = Container()
    hook_manager = HookManager()

    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)

    # 阶段一 & 二：发现、排序、注册
    loader = PluginLoader(container, hook_manager)
    loader.load_plugins()
    
    logger = logging.getLogger(__name__)
    logger.info("--- FastAPI Application Assembly ---")

    app.state.container = container
    app.state.hook_manager = hook_manager
    logger.info("Core services (Container, HookManager) attached to app.state.")

    # 阶段 2.5: 异步服务初始化
    # 触发一个钩子，允许需要异步操作（如数据库连接、异步收集依赖）的插件完成它们的设置。
    logger.info("Triggering 'services_post_register' hook for async initializations...")
    await hook_manager.trigger('services_post_register', container=container)
    logger.info("Async service initialization complete.")

    # 阶段三：装配 API 路由 (通过钩子)
    logger.info("Triggering 'collect_api_routers' filter hook...")
    routers_to_add: list[APIRouter] = await hook_manager.filter("collect_api_routers", [])
    
    if routers_to_add:
        logger.info(f"Collected {len(routers_to_add)} router(s). Adding to application...")
        for router in routers_to_add:
            app.include_router(router)
            logger.debug(f"Added router: prefix='{router.prefix}', tags={router.tags}")
    else:
        logger.warning("No API routers were collected from plugins.")
    
    await hook_manager.trigger('app_startup_complete', app=app, container=container)
    
    logger.info("--- Hevno Engine Ready ---")
    yield
    # --- 应用关闭 ---
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