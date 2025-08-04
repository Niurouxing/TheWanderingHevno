# plugins/core_websocket/__init__.py
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.contracts import Container, HookManager
from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_connection_manager() -> ConnectionManager:
    return ConnectionManager()

# --- 钩子实现 (提供API路由) ---
async def provide_router(routers: list, *, container: Container) -> list:
    # 这个 router 是插件私有的，只在钩子中暴露
    ws_router = APIRouter()
    manager: ConnectionManager = container.resolve("connection_manager")

    @ws_router.websocket("/ws/hooks")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        logger.info("New WebSocket client connected.")
        try:
            # 在这里，我们准备好接收来自前端的钩子事件
            while True:
                data = await websocket.receive_text()
                # 关键：将收到的数据交给一个钩子去处理
                # 我们不在这里直接处理逻辑，而是广播一个内部事件
                hook_manager: HookManager = container.resolve("hook_manager")
                await hook_manager.trigger(
                    "websocket.message_received",
                    websocket=websocket, 
                    data=data
                )
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logger.info("WebSocket client disconnected.")

    routers.append(ws_router)
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-websocket] 插件...")
    
    # 1. 注册核心服务
    container.register("connection_manager", _create_connection_manager, singleton=True)
    
    # 2. 注册钩子，将自己的API路由提供给系统
    hook_manager.add_implementation("collect_api_routers", provide_router, plugin_name="core-websocket")
    
    logger.info("插件 [core-websocket] 注册成功。")