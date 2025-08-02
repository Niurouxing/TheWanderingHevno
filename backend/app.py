# backend/app.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

# 导入微核心组件
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.loader import PluginLoader

# 注意我们不在这里导入任何插件或具体服务
# 这是一个干净、通用的启动器

# 使用 FastAPI 的新版生命周期管理器 (lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 应用启动时执行 ---
    # 实例化平台核心服务
    container = Container()
    hook_manager = HookManager()

    # 阶段一 & 二：发现、排序与注册 (同步过程)
    loader = PluginLoader(container, hook_manager)
    loader.load_plugins()
    
    # 日志系统此时应该已经由 core_logging 插件配置好了
    logger = logging.getLogger(__name__)
    logger.info("--- FastAPI Application Assembly ---")

    # 将核心服务附加到 app.state，以便 API 路由可以访问它们
    app.state.container = container
    app.state.hook_manager = hook_manager
    logger.info("Core services (Container, HookManager) attached to app.state.")

    # 阶段三：装配 (使用钩子系统)
    logger.info("Triggering 'collect_api_routers' filter hook to collect API routers from plugins...")
    # 我们启动一个空的列表，然后让 filter 钩子去填充它
    routers_to_add: list[APIRouter] = await hook_manager.filter("collect_api_routers", [])
    
    if routers_to_add:
        logger.info(f"Collected {len(routers_to_add)} router(s). Adding to application...")
        for router in routers_to_add:
            app.include_router(router)
            logger.debug(f"Added router with prefix '{router.prefix}' and tags {router.tags}")
    else:
        logger.info("No API routers were collected from plugins.")


    logger.info("--- Hevno Engine Ready ---")

    yield # 在此暂停，应用开始处理请求

    # --- 应用关闭时执行 ---
    logger.info("--- Hevno Engine Shutting Down ---")
    # 可以在这里添加清理逻辑


def create_app() -> FastAPI:
    """
    应用工厂函数：构建、配置并返回 FastAPI 应用实例。
    """
    app = FastAPI(
        title="Hevno Engine (Plugin Architecture)",
        version="1.2.0",
        lifespan=lifespan  # 注册生命周期管理器
    )

    # 中间件的配置移到这里，因为它不依赖于异步启动过程
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app