"""文件传输模块"""
import os
import aiofiles
import base64
import hashlib
from typing import Dict, Any, Optional


class FileTransfer:
    """文件传输处理"""

    CHUNK_SIZE = 64 * 1024  # 64KB chunks

    @staticmethod
    async def prepare_download(file_path: str) -> Dict[str, Any]:
        """准备文件下载（返回文件信息和Base64内容）"""
        try:
            file_path = os.path.abspath(file_path)

            if not os.path.exists(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}

            if os.path.isdir(file_path):
                return {"success": False, "error": f"Not a file: {file_path}"}

            file_size = os.path.getsize(file_path)

            # 读取文件内容
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()

            # 计算MD5
            md5 = hashlib.md5(content).hexdigest()

            return {
                "success": True,
                "path": file_path,
                "filename": os.path.basename(file_path),
                "size": file_size,
                "md5": md5,
                "content": base64.b64encode(content).decode()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def save_upload(dest_path: str, filename: str, content_b64: str) -> Dict[str, Any]:
        """保存上传的文件"""
        try:
            # 确保目标目录存在
            os.makedirs(dest_path, exist_ok=True)

            file_path = os.path.join(dest_path, filename)

            # 解码Base64内容
            content = base64.b64decode(content_b64)

            # 写入文件
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)

            # 计算MD5
            md5 = hashlib.md5(content).hexdigest()

            return {
                "success": True,
                "path": file_path,
                "size": len(content),
                "md5": md5
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def save_upload_to_path(full_path: str, content_b64: str) -> Dict[str, Any]:
        """保存上传的文件到指定完整路径"""
        try:
            # 确保目录存在
            dir_path = os.path.dirname(full_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # 解码Base64内容
            content = base64.b64decode(content_b64)

            # 写入文件
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(content)

            # 计算MD5
            md5 = hashlib.md5(content).hexdigest()

            return {
                "success": True,
                "path": full_path,
                "size": len(content),
                "md5": md5
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
