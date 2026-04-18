"""文件操作模块"""
import os
import aiofiles
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional


class FileOperations:
    """文件系统操作"""

    @staticmethod
    def get_file_info(path: str) -> Dict[str, Any]:
        """获取文件/目录信息"""
        try:
            stat = os.stat(path)
            return {
                "name": os.path.basename(path),
                "path": os.path.abspath(path),
                "is_dir": os.path.isdir(path),
                "size": stat.st_size if os.path.isfile(path) else 0,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "accessed_time": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:],
                "readable": os.access(path, os.R_OK),
                "writable": os.access(path, os.W_OK),
            }
        except Exception as e:
            return {"error": str(e), "path": path}

    @staticmethod
    async def list_directory(path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
        """列出目录内容"""
        try:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                return {"success": False, "error": f"Path not found: {path}"}

            if not os.path.isdir(path):
                return {"success": False, "error": f"Not a directory: {path}"}

            items = []
            for item in os.listdir(path):
                if not show_hidden and item.startswith('.'):
                    continue
                item_path = os.path.join(path, item)
                info = FileOperations.get_file_info(item_path)
                if "error" not in info:
                    items.append(info)

            # 排序：目录优先，然后按名称
            items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

            return {
                "success": True,
                "path": path,
                "items": items,
                "total": len(items)
            }
        except PermissionError:
            return {"success": False, "error": "Permission denied"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def read_file(path: str, encoding: str = "utf-8", max_size: int = 10 * 1024 * 1024) -> Dict[str, Any]:
        """读取文件内容"""
        try:
            path = os.path.abspath(path)

            if not os.path.exists(path):
                return {"success": False, "error": f"File not found: {path}"}

            if os.path.isdir(path):
                return {"success": False, "error": f"Not a file: {path}"}

            file_size = os.path.getsize(path)
            if file_size > max_size:
                return {
                    "success": False,
                    "error": f"File too large ({file_size} bytes). Max allowed: {max_size} bytes"
                }

            async with aiofiles.open(path, 'rb') as f:
                content = await f.read()

            # 尝试多种编码解码
            text_content = None
            for enc in [encoding, 'utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    text_content = content.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue

            return {
                "success": True,
                "path": path,
                "content": text_content if text_content else base64.b64encode(content).decode(),
                "size": file_size,
                "is_binary": text_content is None,
                "encoding": encoding if text_content and encoding == 'utf-8' else 'detected'
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def search_files(path: str, pattern: str, recursive: bool = True) -> Dict[str, Any]:
        """搜索文件"""
        results = []
        try:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                return {"success": False, "error": f"Path not found: {path}"}

            pattern_lower = pattern.lower()

            def search_in_dir(dir_path: str):
                try:
                    for item in os.listdir(dir_path):
                        item_path = os.path.join(dir_path, item)
                        if pattern_lower in item.lower():
                            results.append(FileOperations.get_file_info(item_path))
                        if recursive and os.path.isdir(item_path):
                            search_in_dir(item_path)
                except PermissionError:
                    pass

            search_in_dir(path)
            return {
                "success": True,
                "path": path,
                "pattern": pattern,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_directory_tree(path: str = ".", max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
        """获取目录树结构"""
        try:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                return {"name": os.path.basename(path), "error": "not found"}

            result = {
                "name": os.path.basename(path) or path,
                "path": path,
                "is_dir": os.path.isdir(path)
            }

            if os.path.isdir(path) and current_depth < max_depth:
                children = []
                try:
                    for item in sorted(os.listdir(path)):
                        if item.startswith('.'):
                            continue
                        child_path = os.path.join(path, item)
                        child = FileOperations.get_directory_tree(
                            child_path, max_depth, current_depth + 1
                        )
                        children.append(child)
                    result["children"] = children
                except PermissionError:
                    result["error"] = "Permission denied"

            return result
        except Exception as e:
            return {"name": os.path.basename(path), "error": str(e)}
