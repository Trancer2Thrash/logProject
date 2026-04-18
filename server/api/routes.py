"""REST API路由"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Optional
import aiofiles

from ..models import ClientInfo, CommandRequest, CommandResponse, FileInfo
from ..websocket.handler import ConnectionManager

router = APIRouter()

# 全局连接管理器实例
manager: Optional[ConnectionManager] = None


def get_manager() -> ConnectionManager:
    if manager is None:
        raise HTTPException(status_code=500, detail="Connection manager not initialized")
    return manager


def set_manager(m: ConnectionManager):
    global manager
    manager = m


@router.get("/token")
async def get_auth_token():
    """获取认证Token"""
    m = get_manager()
    token = m.generate_token()
    return {"token": token, "created_at": datetime.now().isoformat()}


@router.get("/clients")
async def list_clients():
    """获取在线客户端列表"""
    m = get_manager()
    return {"clients": m.get_online_clients(), "count": len(m.active_connections)}


@router.get("/clients/{client_id}")
async def get_client_info(client_id: str):
    """获取指定客户端信息"""
    m = get_manager()
    if client_id not in m.client_info:
        raise HTTPException(status_code=404, detail="Client not found")
    return m.client_info[client_id]


@router.delete("/clients/{client_id}")
async def disconnect_client(client_id: str):
    """断开指定客户端连接"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        # 发送断开连接消息给客户端
        await m.send_message(client_id, {
            "type": "disconnect",
            "data": {"reason": "Server disconnect"}
        })
        # 关闭连接
        m.disconnect(client_id)
        return {"success": True, "message": f"Client {client_id} disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/execute")
async def execute_command(client_id: str, request: CommandRequest):
    """在客户端执行命令"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {
            "type": "execute_cmd",
            "id": str(uuid.uuid4()),
            "data": {
                "command": request.command,
                "args": request.args,
                "timeout": request.timeout
            },
            "timestamp": datetime.now().isoformat()
        }, timeout=request.timeout + 10)
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Command execution timeout")
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/clients/{client_id}/files")
async def list_directory(client_id: str, path: str = "."):
    """列出客户端目录内容"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {
            "type": "list_dir",
            "data": {"path": path}
        })
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")


@router.get("/clients/{client_id}/files/read")
async def read_file(client_id: str, path: str):
    """读取客户端文件内容"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {
            "type": "read_file",
            "data": {"path": path}
        })
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")


@router.get("/clients/{client_id}/files/download")
async def download_file(client_id: str, path: str):
    """从客户端下载文件"""
    from fastapi.responses import Response
    import base64

    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {
            "type": "download_file",
            "data": {"path": path}
        }, timeout=300)

        if not response.get("success"):
            error_msg = response.get("error", "Download failed")
            raise HTTPException(status_code=500, detail=error_msg)

        content = response.get("content")
        if not content:
            raise HTTPException(status_code=500, detail="No file content received")

        filename = response.get("filename", os.path.basename(path))
        file_data = base64.b64decode(content)

        return Response(
            content=file_data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Download timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/files/upload")
async def upload_file(client_id: str, file: UploadFile = File(...), dest_path: str = Form(...)):
    """上传文件到客户端"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        content = await file.read()
        import base64
        response = await m.send_and_wait(client_id, {
            "type": "upload_file",
            "data": {
                "path": dest_path,
                "filename": file.filename,
                "content": base64.b64encode(content).decode()
            }
        }, timeout=300)
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Upload timeout")


@router.get("/clients/{client_id}/system")
async def get_system_info(client_id: str):
    """获取客户端系统信息"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {"type": "system_info", "data": {}})
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")


@router.get("/clients/{client_id}/network")
async def get_network_info(client_id: str):
    """获取客户端网络信息"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {"type": "network_info", "data": {}})
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")


@router.get("/clients/{client_id}/processes")
async def get_process_list(client_id: str):
    """获取客户端进程列表"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {"type": "process_list", "data": {}})
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")


@router.get("/clients/{client_id}/services")
async def get_service_list(client_id: str):
    """获取客户端服务列表"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {"type": "service_list", "data": {}})
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")


@router.get("/clients/{client_id}/tasks")
async def get_scheduled_tasks(client_id: str):
    """获取客户端计划任务"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {"type": "scheduled_tasks", "data": {}})
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")


@router.get("/clients/{client_id}/software")
async def get_installed_software(client_id: str):
    """获取客户端已安装软件"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {"type": "installed_software", "data": {}})
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")


@router.get("/clients/{client_id}/firewall")
async def get_firewall_status(client_id: str):
    """获取客户端防火墙状态"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {"type": "firewall_status", "data": {}})
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request timeout")


@router.get("/clients/{client_id}/logs/search")
async def search_logs(client_id: str, keyword: str, path: str = "", max_results: int = 100):
    """搜索客户端日志"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {
            "type": "search_logs",
            "data": {
                "keyword": keyword,
                "path": path,
                "max_results": max_results
            }
        }, timeout=120)
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Search timeout")


@router.get("/clients/{client_id}/edr/collect")
async def collect_edr_info(client_id: str):
    """一键收集所有EDR信息"""
    m = get_manager()
    if client_id not in m.active_connections:
        raise HTTPException(status_code=404, detail="Client not connected")

    try:
        response = await m.send_and_wait(client_id, {
            "type": "edr_collect",
            "data": {}
        }, timeout=180)  # 3分钟超时
        return response
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Collection timeout")
