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
async def provide_router(routers: list, container: Container, hook_manager: HookManager) -> list:
    ws_router = APIRouter()
    manager: ConnectionManager = container.resolve("connection_manager")

    @ws_router.websocket("/ws/hooks")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        logger.info("New WebSocket client connected.")
        try:
            while True:
                data = await websocket.receive_text()
                # 触发钩子时，传递 websocket 和 data 作为临时上下文
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
    logger.info("--> 正在注册 [core_websocket] 插件...")
    
    container.register("connection_manager", _create_connection_manager, singleton=True)
    hook_manager.add_implementation("collect_api_routers", provide_router, plugin_name="core_websocket")
    
    logger.info("插件 [core_websocket] 注册成功。")