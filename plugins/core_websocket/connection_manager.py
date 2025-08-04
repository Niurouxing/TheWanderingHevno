# plugins/core_websocket/connection_manager.py
import asyncio
from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """向所有连接的客户端广播消息"""
        if not self.active_connections:
            return
        
        # 使用 asyncio.gather 并发发送
        tasks = [conn.send_text(message) for conn in self.active_connections]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to(self, websocket: WebSocket, message: str):
        """向单个客户端发送消息"""
        await websocket.send_text(message)