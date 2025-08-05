# plugins/core_remote_hooks/emitter.py

import json
import logging
from typing import Dict, Any

from plugins.core_websocket.connection_manager import ConnectionManager
from .contracts import RemoteHookEmitterInterface

logger = logging.getLogger(__name__)

class RemoteHookEmitter(RemoteHookEmitterInterface):
    """
    将后端钩子事件打包并通过 WebSocket 广播到所有前端客户端。
    """
    def __init__(self, connection_manager: ConnectionManager):
        self._manager = connection_manager

    async def emit(self, hook_name: str, data: Dict[str, Any]) -> None:
        """
        构建 payload 并通过 WebSocket 连接管理器广播。
        """
        try:
            # 注意：kwargs 可能包含不可序列化为 JSON 的对象。
            # 这是一个简化的实现，一个更健壮的系统可能需要一个序列化层。
            payload = {
                "hook_name": hook_name,
                "data": data
            }
            message = json.dumps(payload)
            logger.debug(f"Emitting remote hook to frontend: '{hook_name}'")
            await self._manager.broadcast(message)
        except TypeError as e:
            logger.error(
                f"Could not serialize payload for remote hook '{hook_name}'. "
                f"Data may contain non-JSON-serializable objects. Error: {e}"
            )
        except Exception:
            logger.exception(f"Unexpected error while emitting remote hook '{hook_name}'.")