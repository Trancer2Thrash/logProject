"""WebSocket连接管理器"""
import asyncio
import uuid
import secrets
from datetime import datetime
from typing import Dict, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
import json


class ConnectionManager:
    """管理所有客户端WebSocket连接"""

    def __init__(self):
        # client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # client_id -> ClientInfo
        self.client_info: Dict[str, dict] = {}
        # 有效的Token集合
        self.valid_tokens: Set[str] = set()
        # 待处理的响应队列 (message_id -> response)
        self.pending_responses: Dict[str, asyncio.Future] = {}
        # 文件传输缓存
        self.file_transfers: Dict[str, dict] = {}

    def generate_token(self) -> str:
        """生成认证Token"""
        token = secrets.token_urlsafe(32)
        self.valid_tokens.add(token)
        return token

    def validate_token(self, token: str) -> bool:
        """验证Token"""
        return token in self.valid_tokens

    async def connect(self, websocket: WebSocket, client_id: str):
        """接受新连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_info[client_id] = {
            "client_id": client_id,
            "connect_time": datetime.now(),
            "last_heartbeat": datetime.now(),
            "status": "online"
        }

    def disconnect(self, client_id: str):
        """断开连接"""
        self.active_connections.pop(client_id, None)
        self.client_info.pop(client_id, None)
        # 清理该客户端的待处理响应
        for msg_id in list(self.pending_responses.keys()):
            if msg_id.startswith(client_id):
                future = self.pending_responses.pop(msg_id, None)
                if future and not future.done():
                    future.cancel()

    async def send_message(self, client_id: str, message: dict) -> bool:
        """发送消息给指定客户端"""
        if client_id not in self.active_connections:
            return False
        try:
            await self.active_connections[client_id].send_json(message)
            return True
        except Exception:
            self.disconnect(client_id)
            return False

    async def send_and_wait(self, client_id: str, message: dict, timeout: float = 60.0) -> dict:
        """发送消息并等待响应"""
        message_id = f"{client_id}_{uuid.uuid4()}"
        message["id"] = message_id

        future = asyncio.get_event_loop().create_future()
        self.pending_responses[message_id] = future

        try:
            success = await self.send_message(client_id, message)
            if not success:
                raise ConnectionError(f"Client {client_id} not connected")

            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.pending_responses.pop(message_id, None)
            raise TimeoutError(f"Request timeout for client {client_id}")
        finally:
            self.pending_responses.pop(message_id, None)

    def handle_response(self, message_id: str, response: dict):
        """处理客户端响应"""
        if message_id in self.pending_responses:
            future = self.pending_responses[message_id]
            if not future.done():
                future.set_result(response)

    def get_online_clients(self) -> list:
        """获取在线客户端列表"""
        return [
            {**info, "last_heartbeat": info["last_heartbeat"].isoformat(),
             "connect_time": info["connect_time"].isoformat()}
            for info in self.client_info.values()
        ]

    def update_heartbeat(self, client_id: str):
        """更新心跳时间"""
        if client_id in self.client_info:
            self.client_info[client_id]["last_heartbeat"] = datetime.now()
            self.client_info[client_id]["status"] = "online"

    def update_client_info(self, client_id: str, info: dict):
        """更新客户端详细信息"""
        if client_id in self.client_info:
            self.client_info[client_id].update(info)


class WebSocketHandler:
    """WebSocket消息处理器"""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager

    async def handle(self, client_id: str, data: str):
        """处理接收到的消息"""
        try:
            message = json.loads(data)
            msg_type = message.get("type")
            msg_id = message.get("id")
            msg_data = message.get("data", {})

            if msg_type == "pong":
                self.manager.update_heartbeat(client_id)

            elif msg_type == "register":
                # 客户端注册信息
                self.manager.update_client_info(client_id, msg_data)

            elif msg_type == "response":
                # 命令响应
                self.manager.handle_response(msg_id, msg_data)

            elif msg_type == "file_chunk":
                # 文件传输块
                await self.handle_file_chunk(msg_data)

            elif msg_type == "error":
                # 错误消息
                self.manager.handle_response(msg_id, {"error": msg_data.get("error"), "success": False})

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Error handling message: {e}")

    async def handle_file_chunk(self, data: dict):
        """处理文件传输块"""
        transfer_id = data.get("transfer_id")
        if transfer_id in self.manager.file_transfers:
            transfer = self.manager.file_transfers[transfer_id]
            transfer["chunks"].append(data.get("chunk_data"))
            transfer["received"] += len(data.get("chunk_data", ""))

            if data.get("is_last"):
                transfer["future"].set_result(transfer["chunks"])
