"""命令执行器"""
import asyncio
import locale
import time
from typing import List, Optional


class CommandExecutor:
    """Windows命令执行器"""

    # 获取系统默认编码
    SYSTEM_ENCODING = locale.getpreferredencoding() or 'gbk'

    @staticmethod
    async def execute(command: str, args: List[str] = None, timeout: int = 30) -> dict:
        """
        执行命令并返回结果

        Args:
            command: 命令名
            args: 命令参数
            timeout: 超时时间(秒)

        Returns:
            dict: 包含success, output, error, exit_code, execution_time
        """
        start_time = time.time()
        args = args or []

        # 构建完整命令
        full_command = [command] + args

        try:
            # 使用asyncio创建子进程，设置环境变量使用UTF-8
            import os
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "output": "",
                    "error": f"Command timeout after {timeout} seconds",
                    "exit_code": -1,
                    "execution_time": timeout
                }

            execution_time = time.time() - start_time

            # 解码输出 - Windows默认使用GBK编码
            output = CommandExecutor._decode_output(stdout)
            error = CommandExecutor._decode_output(stderr)

            return {
                "success": process.returncode == 0,
                "output": output,
                "error": error if error else None,
                "exit_code": process.returncode,
                "execution_time": round(execution_time, 3)
            }

        except FileNotFoundError:
            return {
                "success": False,
                "output": "",
                "error": f"Command not found: {command}",
                "exit_code": -1,
                "execution_time": 0
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1,
                "execution_time": time.time() - start_time
            }

    @staticmethod
    def _decode_output(data: bytes) -> str:
        """解码命令输出，尝试多种编码"""
        if not data:
            return ""

        # 按优先级尝试不同的编码
        encodings = [
            'utf-8',      # 首先尝试UTF-8
            'gbk',        # Windows简体中文
            'gb2312',     # Windows简体中文备选
            'cp936',      # Windows代码页936
            'latin-1',    # 兜底编码，不会失败
        ]

        for encoding in encodings:
            try:
                return data.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue

        # 最后使用replace模式
        return data.decode('utf-8', errors='replace')

    @staticmethod
    async def execute_powershell(script: str, timeout: int = 30) -> dict:
        """执行PowerShell脚本，输出UTF-8"""
        # PowerShell可以设置输出编码
        full_script = f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; {script}"
        return await CommandExecutor.execute(
            "powershell",
            ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", full_script],
            timeout
        )

    @staticmethod
    async def execute_cmd(command: str, timeout: int = 30) -> dict:
        """执行CMD命令，使用UTF-8代码页"""
        # 先切换到UTF-8代码页，再执行命令
        full_command = f"chcp 65001 >nul && {command}"
        return await CommandExecutor.execute(
            "cmd",
            ["/c", full_command],
            timeout
        )
