# plugins/core_remote_hooks/__init__.py
import json
import logging

from fastapi import WebSocket

from backend.core.contracts import Container, HookManager
# 依赖 core_websocket 提供的服务
from plugins.core_websocket.connection_manager import ConnectionManager

# 从本插件导入组件
from .contracts import GlobalHookRegistryInterface
from .registry import GlobalHookRegistry
from .emitter import RemoteHookEmitter

logger = logging.getLogger(__name__)

# --- 服务工厂 ---

def _create_global_hook_registry() -> GlobalHookRegistry:
    return GlobalHookRegistry()

def _create_remote_hook_emitter(container: Container) -> RemoteHookEmitter:
    # 这个工厂依赖于另一个插件的服务
    connection_manager = container.resolve("connection_manager")
    return RemoteHookEmitter(connection_manager)


# --- 钩子实现 ---


async def handle_incoming_message(
    data: str,
    container: Container,
    hook_manager: HookManager
):
    """
    钩子实现: 监听 'websocket.message_received'。
    解析来自前端的消息，并根据类型进行分发。
    """
    try:
        payload = json.loads(data)
        message_type = payload.get("type")

        # Case 1: 这是前端发来的钩子清单同步消息
        if message_type == 'sync_hooks':
            registry: GlobalHookRegistryInterface = container.resolve("global_hook_registry")
            frontend_hooks = payload.get("hooks", [])
            registry.register_frontend_hooks(frontend_hooks)
            logger.info(f"Received and registered {len(frontend_hooks)} hooks from frontend.")
            return

        # Case 2: 这是普通的远程钩子调用
        hook_name = payload.get("hook_name")
        hook_data = payload.get("data", {})

        if not hook_name:
            logger.warning("Received a remote message without 'hook_name' or 'type'.")
            return

        logger.debug(f"Relaying remote hook from frontend: '{hook_name}'")
        # 在后端触发该钩子
        await hook_manager.trigger(hook_name, **hook_data)

    except json.JSONDecodeError:
        logger.warning(f"Failed to decode incoming WebSocket message: {data}")
    except Exception:
        logger.exception("Error handling incoming remote hook.")


# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_remote_hooks] 插件...")

    # 1. 注册本插件提供的核心服务
    container.register("global_hook_registry", _create_global_hook_registry, singleton=True)
    container.register("remote_hook_emitter", _create_remote_hook_emitter, singleton=True)

    # 2. 注册钩子实现
    # 【移除】不再注册 services_post_register 钩子
    
    # 这个钩子处理所有来自前端的 WS 消息
    hook_manager.add_implementation(
        "websocket.message_received",
        handle_incoming_message,
        plugin_name="core_remote_hooks"
    )

    logger.info("插件 [core_remote_hooks] 注册成功。")