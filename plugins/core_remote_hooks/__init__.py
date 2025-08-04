# plugins/core_remote_hooks/__init__.py
import json
import logging

from fastapi import WebSocket

from backend.core.contracts import Container, HookManager
# 依赖 core_websocket 提供的服务
from plugins.core_websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# --- 钩子实现 ---

# 1. 处理从前端发来的钩子事件
async def handle_incoming_hook(
    websocket: WebSocket, 
    data: str, 
    container: Container, 
    hook_manager: HookManager
):
    try:
        payload = json.loads(data)
        hook_name = payload.get("hook_name")
        hook_data = payload.get("data", {})
        
        if not hook_name:
            logger.warning("Received a remote hook without 'hook_name'.")
            return

        logger.debug(f"Relaying remote hook from frontend: '{hook_name}'")
        
        # 触发钩子时，将 hook_data 中的内容展开作为临时上下文
        await hook_manager.trigger(hook_name, **hook_data)

    except json.JSONDecodeError:
        logger.warning(f"Failed to decode incoming WebSocket message: {data}")
    except Exception:
        logger.exception("Error handling incoming remote hook.")


# 2. 监听后端事件，并将其转发给前端
#    这是一个范例，比如我们想把 'achievement.unlocked' 事件转发出去
async def forward_achievement_hook(container: Container, **kwargs):
    manager: ConnectionManager = container.resolve("connection_manager")
    
    payload = {
        "hook_name": "achievement.unlocked",
        "data": kwargs
    }
    
    logger.debug(f"Forwarding backend hook 'achievement.unlocked' to frontend.")
    await manager.broadcast(json.dumps(payload))

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_remote-hooks] 插件...")
    
    hook_manager.add_implementation(
        "websocket.message_received",
        handle_incoming_hook,
        plugin_name="core_remote-hooks"
    )

    hook_manager.add_implementation(
        "achievement.unlocked",
        forward_achievement_hook,
        plugin_name="core_remote-hooks"
    )

    logger.info("插件 [core_remote-hooks] 注册成功。")