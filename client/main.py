"""EDR日志调查工具 - 客户端入口"""
import asyncio
import json
import uuid
import socket
import platform
import os
import sys
import argparse
from datetime import datetime
from typing import Optional
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import websockets

from client.commands import CommandExecutor, FileOperations, FileTransfer, SystemInfoCollector


class EDRClient:
    """EDR客户端"""

    def __init__(self, server_url: str, token: str, client_id: Optional[str] = None):
        self.server_url = server_url
        self.token = token
        self.client_id = client_id or self._generate_client_id()
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.heartbeat_interval = 30  # 心跳间隔(秒)

    def _generate_client_id(self) -> str:
        """生成客户端ID"""
        hostname = socket.gethostname()
        return f"{hostname}-{uuid.uuid4().hex[:8]}"

    async def connect(self):
        """连接到服务端"""
        url = f"{self.server_url}?token={self.token}&client_id={self.client_id}"

        print(f"[{datetime.now()}] Connecting to {self.server_url}...")

        try:
            self.websocket = await websockets.connect(url)
            self.running = True
            print(f"[{datetime.now()}] Connected successfully. Client ID: {self.client_id}")

            # 发送注册信息
            await self.register()

            # 启动心跳任务
            asyncio.create_task(self.heartbeat_loop())

            # 消息处理循环
            await self.message_loop()

        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 4001:
                print(f"[{datetime.now()}] Authentication failed: Invalid token")
            else:
                print(f"[{datetime.now()}] Connection failed: {e}")
        except Exception as e:
            print(f"[{datetime.now()}] Connection error: {e}")

    async def register(self):
        """发送注册信息"""
        register_data = {
            "type": "register",
            "id": str(uuid.uuid4()),
            "data": {
                "client_id": self.client_id,
                "hostname": socket.gethostname(),
                "ip_address": self._get_local_ip(),
                "os_type": platform.system(),
                "os_version": platform.version(),
                "username": os.getlogin()
            },
            "timestamp": datetime.now().isoformat()
        }
        await self.websocket.send(json.dumps(register_data))

    def _get_local_ip(self) -> str:
        """获取本机IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    async def heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.websocket and self.websocket.open:
                    ping_msg = {
                        "type": "ping",
                        "id": str(uuid.uuid4()),
                        "data": {},
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.websocket.send(json.dumps(ping_msg))
            except Exception as e:
                print(f"[{datetime.now()}] Heartbeat error: {e}")

    async def message_loop(self):
        """消息处理循环"""
        try:
            async for message in self.websocket:
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"[{datetime.now()}] Connection closed by server")
        except Exception as e:
            print(f"[{datetime.now()}] Message loop error: {e}")
        finally:
            self.running = False

    async def handle_message(self, message: str):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            msg_id = data.get("id")
            msg_data = data.get("data", {})

            print(f"[{datetime.now()}] Received command: {msg_type}")

            # 处理断开连接命令
            if msg_type == "disconnect":
                print(f"[{datetime.now()}] Server requested disconnect: {msg_data.get('reason', 'No reason')}")
                self.running = False
                if self.websocket:
                    await self.websocket.close()
                return

            # 分发到对应的处理器
            handler_map = {
                "execute_cmd": self.handle_execute_cmd,
                "list_dir": self.handle_list_dir,
                "read_file": self.handle_read_file,
                "download_file": self.handle_download_file,
                "upload_file": self.handle_upload_file,
                "system_info": self.handle_system_info,
                "network_info": self.handle_network_info,
                "process_list": self.handle_process_list,
                "service_list": self.handle_service_list,
                "scheduled_tasks": self.handle_scheduled_tasks,
                "installed_software": self.handle_installed_software,
                "firewall_status": self.handle_firewall_status,
                "search_logs": self.handle_search_logs,
                "edr_collect": self.handle_edr_collect,
            }

            handler = handler_map.get(msg_type)
            if handler:
                result = await handler(msg_data)
                await self.send_response(msg_id, result)
            else:
                await self.send_response(msg_id, {"error": f"Unknown command: {msg_type}"})

        except json.JSONDecodeError:
            print(f"[{datetime.now()}] Invalid JSON message")
        except Exception as e:
            print(f"[{datetime.now()}] Handle message error: {e}")
            await self.send_response(msg_id, {"error": str(e)})

    async def send_response(self, msg_id: str, result: dict):
        """发送响应"""
        if self.websocket and self.websocket.open:
            response = {
                "type": "response",
                "id": msg_id,
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            await self.websocket.send(json.dumps(response))

    # === 命令处理器 ===

    async def handle_execute_cmd(self, data: dict) -> dict:
        """执行命令"""
        command = data.get("command")
        args = data.get("args", [])
        timeout = data.get("timeout", 30)
        use_cmd = data.get("use_cmd", True)  # 默认使用cmd执行，自动处理编码

        if not command:
            return {"success": False, "error": "No command specified"}

        # 如果是cmd命令，使用execute_cmd方法自动处理UTF-8编码
        if use_cmd and command.lower() == "cmd":
            # 提取实际命令
            if args and args[0] == "/c":
                actual_cmd = " ".join(args[1:]) if len(args) > 1 else ""
            else:
                actual_cmd = " ".join(args)
            result = await CommandExecutor.execute_cmd(actual_cmd, timeout)
        else:
            result = await CommandExecutor.execute(command, args, timeout)

        return result

    async def handle_list_dir(self, data: dict) -> dict:
        """列出目录"""
        path = data.get("path", ".")
        result = await FileOperations.list_directory(path)
        return result

    async def handle_read_file(self, data: dict) -> dict:
        """读取文件"""
        path = data.get("path")
        if not path:
            return {"success": False, "error": "No path specified"}
        result = await FileOperations.read_file(path)
        return result

    async def handle_download_file(self, data: dict) -> dict:
        """下载文件"""
        path = data.get("path")
        if not path:
            return {"success": False, "error": "No path specified"}
        result = await FileTransfer.prepare_download(path)
        return result

    async def handle_upload_file(self, data: dict) -> dict:
        """上传文件"""
        path = data.get("path")
        filename = data.get("filename")
        content = data.get("content")

        if not all([path, filename, content]):
            return {"success": False, "error": "Missing required fields"}

        full_path = os.path.join(path, filename)
        result = await FileTransfer.save_upload_to_path(full_path, content)
        return result

    async def handle_system_info(self, data: dict) -> dict:
        """获取系统信息"""
        basic = SystemInfoCollector.get_basic_info()
        cpu = SystemInfoCollector.get_cpu_info()
        memory = SystemInfoCollector.get_memory_info()
        disk = SystemInfoCollector.get_disk_info()

        return {
            "success": True,
            "data": {
                "basic": basic,
                "cpu": cpu,
                "memory": memory,
                "disk": disk
            }
        }

    async def handle_network_info(self, data: dict) -> dict:
        """获取网络信息"""
        interfaces = SystemInfoCollector.get_network_interfaces()
        connections = SystemInfoCollector.get_network_connections()

        return {
            "success": True,
            "data": {
                "interfaces": interfaces,
                "connections": connections
            }
        }

    async def handle_process_list(self, data: dict) -> dict:
        """获取进程列表"""
        processes = SystemInfoCollector.get_process_list()
        return {
            "success": True,
            "data": processes,
            "count": len(processes)
        }

    async def handle_service_list(self, data: dict) -> dict:
        """获取服务列表"""
        services = await SystemInfoCollector.get_services()
        return {
            "success": True,
            "data": services,
            "count": len(services)
        }

    async def handle_scheduled_tasks(self, data: dict) -> dict:
        """获取计划任务"""
        tasks = await SystemInfoCollector.get_scheduled_tasks()
        return {
            "success": True,
            "data": tasks,
            "count": len(tasks)
        }

    async def handle_installed_software(self, data: dict) -> dict:
        """获取已安装软件"""
        software = await SystemInfoCollector.get_installed_software()
        return {
            "success": True,
            "data": software,
            "count": len(software)
        }

    async def handle_firewall_status(self, data: dict) -> dict:
        """获取防火墙状态"""
        status = await SystemInfoCollector.get_firewall_status()
        return {
            "success": True,
            "data": status
        }

    async def handle_search_logs(self, data: dict) -> dict:
        """搜索日志"""
        keyword = data.get("keyword")
        path = data.get("path", "")
        max_results = data.get("max_results", 100)

        if not keyword:
            return {"success": False, "error": "No keyword specified"}

        result = await SystemInfoCollector.search_logs(keyword, path, max_results)
        return result

    async def handle_edr_collect(self, data: dict) -> dict:
        """一键收集所有EDR信息"""
        print(f"[{datetime.now()}] Starting EDR full collection...")
        result = await SystemInfoCollector.collect_all()
        print(f"[{datetime.now()}] EDR collection completed in {result['elapsed_seconds']}s")
        return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="EDR Client")
    parser.add_argument("--server", "-s", default="ws://localhost:8000/ws",
                        help="Server WebSocket URL")
    parser.add_argument("--token", "-t", required=True,
                        help="Authentication token")
    parser.add_argument("--client-id", "-c", default=None,
                        help="Client ID (auto-generated if not specified)")

    args = parser.parse_args()

    client = EDRClient(
        server_url=args.server,
        token=args.token,
        client_id=args.client_id
    )

    # 重连机制
    while True:
        try:
            await client.connect()
        except KeyboardInterrupt:
            print(f"\n[{datetime.now()}] Shutting down...")
            break
        except Exception as e:
            print(f"[{datetime.now()}] Connection error: {e}")

        # 断开后等待重连
        if not client.running:
            print(f"[{datetime.now()}] Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
