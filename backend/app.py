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

    # 将核心服务实例注册到容器中，以便插件可以解析它们
    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)

    # 阶段一 & 二：发现、排序、注册
    # 此时日志系统应该由 core-logging 插件配置完毕
    loader = PluginLoader(container, hook_manager)
    loader.load_plugins()
    
    logger = logging.getLogger(__name__) # 此时日志已由插件配置
    logger.info("--- FastAPI Application Assembly ---")

    # 将核心服务附加到 app.state，以便 API 依赖注入函数可以访问
    app.state.container = container
    app.state.hook_manager = hook_manager
    logger.info("Core services (Container, HookManager) attached to app.state.")

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
    
    # 可以在此触发其他装配钩子，如 'initialize_services'
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

    # CORS 中间件可以保留
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # 生产中应使用具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app