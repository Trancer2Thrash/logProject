"""Pydantic数据模型定义"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TokenType(str, Enum):
    """Token类型"""
    AUTH = "auth"
    FILE_TRANSFER = "file_transfer"


class ClientInfo(BaseModel):
    """客户端信息"""
    client_id: str
    hostname: str
    ip_address: str
    os_type: str
    os_version: str
    username: str
    connect_time: datetime
    last_heartbeat: datetime
    status: str = "online"


class CommandRequest(BaseModel):
    """命令请求"""
    command: str
    args: Optional[List[str]] = []
    timeout: Optional[int] = 30


class CommandResponse(BaseModel):
    """命令响应"""
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    execution_time: float = 0.0


class FileInfo(BaseModel):
    """文件信息"""
    name: str
    path: str
    is_dir: bool
    size: int
    modified_time: datetime
    permissions: str


class SystemInfo(BaseModel):
    """系统信息"""
    hostname: str
    os_type: str
    os_version: str
    architecture: str
    cpu_info: str
    cpu_usage: float
    memory_total: int
    memory_used: int
    memory_usage: float
    disk_total: int
    disk_used: int
    disk_usage: float
    uptime: str


class NetworkInterface(BaseModel):
    """网络接口信息"""
    name: str
    ip_address: str
    mac_address: str
    netmask: str
    status: str


class NetworkConnection(BaseModel):
    """网络连接信息"""
    protocol: str
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int
    state: str
    pid: int


class NetworkInfo(BaseModel):
    """网络信息"""
    interfaces: List[NetworkInterface]
    connections: List[NetworkConnection]
    dns_servers: List[str]
    routing_table: List[Dict[str, Any]]


class ProcessInfo(BaseModel):
    """进程信息"""
    pid: int
    name: str
    username: str
    cpu_usage: float
    memory_usage: float
    command_line: str
    create_time: datetime


class FileTransferRequest(BaseModel):
    """文件传输请求"""
    file_path: str
    file_size: int
    chunk_size: int = 65536
    transfer_id: str


class Message(BaseModel):
    """WebSocket消息格式"""
    type: str
    id: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.now()
