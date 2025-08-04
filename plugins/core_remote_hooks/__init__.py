# plugins/core_remote_hooks/__init__.py
import json
import logging

from fastapi import WebSocket

from backend.core.contracts import Container, HookManager
# 依赖 core-websocket 提供的服务
from plugins.core_websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# --- 钩子实现 ---

# 1. 处理从前端发来的钩子事件
async def handle_incoming_hook(websocket: WebSocket, data: str, *, container: Container):
    try:
        payload = json.loads(data)
        hook_name = payload.get("hook_name")
        hook_data = payload.get("data", {})
        
        if not hook_name:
            logger.warning("Received a remote hook without 'hook_name'.")
            return

        logger.debug(f"Relaying remote hook from frontend: '{hook_name}'")
        
        hook_manager: HookManager = container.resolve("hook_manager")
        
        # 在后端重新广播这个钩子
        # 注意：我们把 container 也传进去，以便钩子实现者能访问服务
        await hook_manager.trigger(hook_name, container=container, **hook_data)

    except json.JSONDecodeError:
        logger.warning(f"Failed to decode incoming WebSocket message: {data}")
    except Exception:
        logger.exception("Error handling incoming remote hook.")


# 2. 监听后端事件，并将其转发给前端
#    这是一个范例，比如我们想把 'achievement.unlocked' 事件转发出去
async def forward_achievement_hook(container: Container, **kwargs):
    # 从容器中解析 ConnectionManager
    manager: ConnectionManager = container.resolve("connection_manager")
    
    # 构建要发送给前端的 payload
    payload = {
        "hook_name": "achievement.unlocked", # 这是前端要监听的钩子名
        "data": kwargs # 将后端钩子的所有参数都转发出去
    }
    
    logger.debug(f"Forwarding backend hook 'achievement.unlocked' to frontend.")
    await manager.broadcast(json.dumps(payload))

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-remote-hooks] 插件...")
    
    # 订阅由 core-websocket 触发的内部事件
    hook_manager.add_implementation(
        "websocket.message_received",
        handle_incoming_hook,
        plugin_name="core-remote-hooks"
    )

    # 【关键】订阅我们想要“远程化”的后端业务钩子
    # 这里需要明确列出哪些后端的钩子是需要被广播到前端的
    # 这是一个白名单机制，更安全可控
    hook_manager.add_implementation(
        "achievement.unlocked", # 假设这是一个由其他插件定义的业务钩子
        forward_achievement_hook,
        plugin_name="core-remote-hooks"
    )
    # 你可以添加更多需要转发的钩子
    # hook_manager.add_implementation("some.other.event", forward_some_other_event, ...)

    logger.info("插件 [core-remote-hooks] 注册成功。")