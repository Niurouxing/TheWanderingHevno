# backend/app.py

import os
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.loader import load_modules, load_plugins
from backend.container import container

# 导入所有 API 路由
from backend.api import base_router, sandbox_router
from backend.api import persistence as persistence_router_module


PLUGGABLE_MODULES = [
    "backend.runtimes",
    "backend.llm.providers",
]

def create_app() -> FastAPI:
    """
    应用工厂函数：构建、配置并返回 FastAPI 应用实例。
    【重构后】此函数不再负责创建服务，而是从容器中获取它们。
    """
    # 0. 加载环境变量 (可以保留，或者依赖容器已加载)
    load_dotenv()

    # 1. 动态加载所有可插拔模块 (这需要在服务创建前完成)
    print("--- Loading Pluggable Modules ---")
    load_modules(PLUGGABLE_MODULES)
    print("--- Modules Loaded ---")

    # 【新增】加载所有插件
    hook_manager = container.hook_manager
    load_plugins(hook_manager)

    # 2. 创建 FastAPI 实例
    app = FastAPI(
        title="Hevno Backend Engine",
        description="A dynamically loaded, modular execution engine for Hevno.",
        version="0.8.0-container-refactor"
    )

    # 3. 从容器中获取核心服务并附加到 app.state
    #    现在 app.py 不再需要知道如何构建这些服务
    print("--- Attaching Core Services from Container ---")
    app.state.engine = container.execution_engine
    app.state.persistence_service = container.persistence_service
    app.state.snapshot_store = container.snapshot_store
    app.state.sandbox_store = container.sandbox_store
    app.state.auditor = container.auditor
    app.state.hook_manager = container.hook_manager
    print("--- Core Services Attached ---")

    # 4. 配置中间件
    origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 5. 包含所有 API 路由
    app.include_router(base_router.router)
    app.include_router(sandbox_router.router)
    app.include_router(persistence_router_module.router) 

    print("\n--- Hevno Engine Ready ---")
    return app