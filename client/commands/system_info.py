"""系统信息收集模块 - EDR核心功能"""
import os
import platform
import socket
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import psutil


class SystemInfoCollector:
    """Windows系统信息收集器"""

    @staticmethod
    def get_basic_info() -> Dict[str, Any]:
        """获取基础系统信息"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time

        return {
            "hostname": socket.gethostname(),
            "os_type": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_physical_count": psutil.cpu_count(logical=False),
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime": str(uptime).split('.')[0],
            "boot_time": boot_time.isoformat(),
            "current_user": os.getlogin(),
            "system_time": datetime.now().isoformat()
        }

    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        """获取CPU信息"""
        cpu_freq = psutil.cpu_freq()
        return {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "cpu_per_core": psutil.cpu_percent(interval=1, percpu=True),
            "cpu_freq_current": cpu_freq.current if cpu_freq else 0,
            "cpu_freq_min": cpu_freq.min if cpu_freq else 0,
            "cpu_freq_max": cpu_freq.max if cpu_freq else 0,
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False)
        }

    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """获取内存信息"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "memory_total": mem.total,
            "memory_used": mem.used,
            "memory_available": mem.available,
            "memory_percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent
        }

    @staticmethod
    def get_disk_info() -> List[Dict[str, Any]]:
        """获取磁盘信息"""
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "opts": partition.opts,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
            except PermissionError:
                continue
        return disks

    @staticmethod
    def get_network_interfaces() -> List[Dict[str, Any]]:
        """获取网络接口信息"""
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            interface = {"name": name, "addresses": []}
            for addr in addrs:
                interface["addresses"].append({
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast
                })
            interfaces.append(interface)
        return interfaces

    @staticmethod
    def get_network_connections() -> List[Dict[str, Any]]:
        """获取网络连接"""
        connections = []
        for conn in psutil.net_connections(kind='inet'):
            try:
                connections.append({
                    "fd": conn.fd,
                    "family": str(conn.family),
                    "type": str(conn.type),
                    "local_addr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                    "remote_addr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
                    "status": conn.status,
                    "pid": conn.pid
                })
            except:
                continue
        return connections

    @staticmethod
    def get_process_list() -> List[Dict[str, Any]]:
        """获取进程列表"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'cmdline', 'create_time']):
            try:
                pinfo = proc.info
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "username": pinfo['username'] or "N/A",
                    "cpu_percent": round(pinfo['cpu_percent'] or 0, 2),
                    "memory_percent": round(pinfo['memory_percent'] or 0, 2),
                    "cmdline": ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else "",
                    "create_time": datetime.fromtimestamp(pinfo['create_time']).isoformat() if pinfo['create_time'] else ""
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 按CPU占用排序
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return processes[:100]  # 返回前100个进程

    @staticmethod
    async def get_services() -> List[Dict[str, Any]]:
        """获取Windows服务列表"""
        from .executor import CommandExecutor

        result = await CommandExecutor.execute_powershell(
            "Get-Service | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json -Depth 3",
            timeout=60
        )

        if result["success"] and result["output"]:
            import json
            try:
                services = json.loads(result["output"])
                if isinstance(services, dict):
                    services = [services]
                return [{
                    "name": s.get("Name", ""),
                    "display_name": s.get("DisplayName", ""),
                    "status": s.get("Status", ""),
                    "start_type": s.get("StartType", "")
                } for s in services]
            except:
                pass

        return []

    @staticmethod
    async def get_scheduled_tasks() -> List[Dict[str, Any]]:
        """获取计划任务"""
        from .executor import CommandExecutor

        result = await CommandExecutor.execute_powershell(
            "Get-ScheduledTask | Select-Object TaskName, TaskPath, State, LastRunTime, NextRunTime | ConvertTo-Json -Depth 3",
            timeout=60
        )

        if result["success"] and result["output"]:
            import json
            try:
                tasks = json.loads(result["output"])
                if isinstance(tasks, dict):
                    tasks = [tasks]
                return [{
                    "name": t.get("TaskName", ""),
                    "path": t.get("TaskPath", ""),
                    "state": t.get("State", ""),
                    "last_run": str(t.get("LastRunTime", "")),
                    "next_run": str(t.get("NextRunTime", ""))
                } for t in tasks]
            except:
                pass

        return []

    @staticmethod
    async def get_installed_software() -> List[Dict[str, Any]]:
        """获取已安装软件"""
        from .executor import CommandExecutor

        # 从注册表读取
        result = await CommandExecutor.execute_powershell(
            """
            $software = @()
            $paths = @(
                "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*"
            )
            foreach ($path in $paths) {
                if (Test-Path $path) {
                    Get-ItemProperty $path -ErrorAction SilentlyContinue | ForEach-Object {
                        if ($_.DisplayName) {
                            $software += @{
                                Name = $_.DisplayName
                                Version = $_.DisplayVersion
                                Publisher = $_.Publisher
                                InstallDate = $_.InstallDate
                                Location = $_.InstallLocation
                            }
                        }
                    }
                }
            }
            $software | ConvertTo-Json -Depth 3
            """,
            timeout=60
        )

        if result["success"] and result["output"]:
            import json
            try:
                software = json.loads(result["output"])
                if isinstance(software, dict):
                    software = [software]
                return software
            except:
                pass

        return []

    @staticmethod
    async def get_firewall_status() -> Dict[str, Any]:
        """获取防火墙状态"""
        from .executor import CommandExecutor

        result = await CommandExecutor.execute_powershell(
            """
            $profiles = Get-NetFirewallProfile
            $result = @{}
            foreach ($profile in $profiles) {
                $result[$profile.Name] = @{
                    Enabled = $profile.Enabled
                    DefaultInboundAction = $profile.DefaultInboundAction
                    DefaultOutboundAction = $profile.DefaultOutboundAction
                }
            }
            $result | ConvertTo-Json
            """,
            timeout=30
        )

        firewall_status = {"profiles": {}}
        if result["success"] and result["output"]:
            import json
            try:
                firewall_status["profiles"] = json.loads(result["output"])
            except:
                pass

        # 获取防火墙规则数量
        rule_result = await CommandExecutor.execute_powershell(
            "(Get-NetFirewallRule | Measure-Object).Count",
            timeout=30
        )
        if rule_result["success"]:
            try:
                firewall_status["total_rules"] = int(rule_result["output"].strip())
            except:
                pass

        return firewall_status

    @staticmethod
    async def get_users_info() -> List[Dict[str, Any]]:
        """获取用户信息"""
        from .executor import CommandExecutor

        result = await CommandExecutor.execute_powershell(
            """
            Get-LocalUser | Select-Object Name, Enabled, Description, LastLogon, PasswordLastSet | ConvertTo-Json -Depth 3
            """,
            timeout=30
        )

        if result["success"] and result["output"]:
            import json
            try:
                users = json.loads(result["output"])
                if isinstance(users, dict):
                    users = [users]
                return [{
                    "name": u.get("Name", ""),
                    "enabled": u.get("Enabled", False),
                    "description": u.get("Description", ""),
                    "last_logon": str(u.get("LastLogon", "")),
                    "password_last_set": str(u.get("PasswordLastSet", ""))
                } for u in users]
            except:
                pass

        return []

    @staticmethod
    async def get_login_history() -> List[Dict[str, Any]]:
        """获取登录历史"""
        from .executor import CommandExecutor

        result = await CommandExecutor.execute_powershell(
            """
            Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4624} -MaxEvents 50 -ErrorAction SilentlyContinue |
            Select-Object TimeCreated, Message |
            ForEach-Object {
                @{
                    time = $_.TimeCreated
                    message = $_.Message
                }
            } | ConvertTo-Json -Depth 3
            """,
            timeout=60
        )

        if result["success"] and result["output"]:
            import json
            try:
                return json.loads(result["output"])
            except:
                pass

        return []

    @staticmethod
    async def get_dns_cache() -> List[Dict[str, Any]]:
        """获取DNS缓存"""
        from .executor import CommandExecutor

        result = await CommandExecutor.execute_cmd("ipconfig /displaydns", timeout=30)

        # 解析DNS缓存输出
        entries = []
        if result["success"]:
            lines = result["output"].split('\n')
            current_entry = {}
            for line in lines:
                line = line.strip()
                if 'Record Name' in line:
                    if current_entry:
                        entries.append(current_entry)
                    current_entry = {"name": line.split(':')[-1].strip()}
                elif 'A (Host) Record' in line:
                    current_entry["type"] = "A"
                    current_entry["address"] = line.split(':')[-1].strip()
                elif line.startswith('Record Type'):
                    current_entry["type"] = line.split(':')[-1].strip()

            if current_entry:
                entries.append(current_entry)

        return entries[:100]  # 限制数量

    @staticmethod
    async def get_startup_programs() -> List[Dict[str, Any]]:
        """获取启动项"""
        from .executor import CommandExecutor

        result = await CommandExecutor.execute_powershell(
            """
            $startup = @()

            # 当前用户启动项
            $userStartup = [Environment]::GetFolderPath('Startup')
            if (Test-Path $userStartup) {
                Get-ChildItem $userStartup | ForEach-Object {
                    $startup += @{
                        Name = $_.Name
                        Location = $_.FullName
                        User = $env:USERNAME
                    }
                }
            }

            # 所有用户启动项
            $allUsersStartup = "$env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
            if (Test-Path $allUsersStartup) {
                Get-ChildItem $allUsersStartup | ForEach-Object {
                    $startup += @{
                        Name = $_.Name
                        Location = $_.FullName
                        User = 'All Users'
                    }
                }
            }

            # 注册表启动项
            $regPaths = @(
                "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
            )
            foreach ($path in $regPaths) {
                if (Test-Path $path) {
                    Get-ItemProperty $path | Get-Member -MemberType NoteProperty | ForEach-Object {
                        $startup += @{
                            Name = $_.Name
                            Location = (Get-ItemProperty $path).($_.Name)
                            User = if ($path -like "*HKCU*") { $env:USERNAME } else { 'All Users' }
                        }
                    }
                }
            }

            $startup | ConvertTo-Json -Depth 3
            """,
            timeout=30
        )

        if result["success"] and result["output"]:
            import json
            try:
                startup = json.loads(result["output"])
                return startup if isinstance(startup, list) else [startup]
            except:
                pass

        return []

    @staticmethod
    async def search_logs(keyword: str, path: str = "", max_results: int = 100) -> Dict[str, Any]:
        """搜索日志文件"""
        from .executor import CommandExecutor
        from .file_ops import FileOperations

        # 默认搜索Windows日志目录
        if not path:
            path = r"C:\Windows\Logs"

        results = []

        # 先找到所有日志文件
        files_result = await FileOperations.search_files(path, ".log", recursive=True)
        if not files_result.get("success"):
            # 尝试其他常见日志路径
            alt_paths = [
                os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Logs'),
                os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'Logs'),
                os.path.join(os.environ.get('APPDATA', ''), '..', 'Local', 'Logs')
            ]
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    files_result = await FileOperations.search_files(alt_path, ".log", recursive=True)
                    if files_result.get("success"):
                        break

        log_files = files_result.get("results", [])

        # 在每个日志文件中搜索关键字
        for log_file in log_files[:20]:  # 限制搜索文件数量
            try:
                read_result = await FileOperations.read_file(log_file["path"], max_size=5*1024*1024)
                if read_result.get("success") and not read_result.get("is_binary"):
                    content = read_result["content"]
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if keyword.lower() in line.lower():
                            results.append({
                                "file": log_file["path"],
                                "line_number": i + 1,
                                "line": line.strip()[:500]  # 限制每行长度
                            })
                            if len(results) >= max_results:
                                break
                if len(results) >= max_results:
                    break
            except:
                continue

        return {
            "success": True,
            "keyword": keyword,
            "search_path": path,
            "results": results,
            "count": len(results)
        }

    @staticmethod
    async def collect_all() -> Dict[str, Any]:
        """一键收集所有EDR信息"""
        import time
        start_time = time.time()

        # 并行收集信息
        basic_task = asyncio.create_task(asyncio.to_thread(SystemInfoCollector.get_basic_info))
        cpu_task = asyncio.create_task(asyncio.to_thread(SystemInfoCollector.get_cpu_info))
        memory_task = asyncio.create_task(asyncio.to_thread(SystemInfoCollector.get_memory_info))
        disk_task = asyncio.create_task(asyncio.to_thread(SystemInfoCollector.get_disk_info))
        network_task = asyncio.create_task(asyncio.to_thread(SystemInfoCollector.get_network_interfaces))
        connections_task = asyncio.create_task(asyncio.to_thread(SystemInfoCollector.get_network_connections))
        processes_task = asyncio.create_task(asyncio.to_thread(SystemInfoCollector.get_process_list))
        services_task = asyncio.create_task(SystemInfoCollector.get_services())
        tasks_task = asyncio.create_task(SystemInfoCollector.get_scheduled_tasks())
        software_task = asyncio.create_task(SystemInfoCollector.get_installed_software())
        firewall_task = asyncio.create_task(SystemInfoCollector.get_firewall_status())
        users_task = asyncio.create_task(SystemInfoCollector.get_users_info())
        startup_task = asyncio.create_task(SystemInfoCollector.get_startup_programs())

        # 等待所有任务完成
        await asyncio.gather(
            basic_task, cpu_task, memory_task, disk_task,
            network_task, connections_task, processes_task,
            services_task, tasks_task, software_task,
            firewall_task, users_task, startup_task
        )

        return {
            "success": True,
            "collection_time": datetime.now().isoformat(),
            "elapsed_seconds": round(time.time() - start_time, 2),
            "data": {
                "basic": basic_task.result(),
                "cpu": cpu_task.result(),
                "memory": memory_task.result(),
                "disk": disk_task.result(),
                "network": {
                    "interfaces": network_task.result(),
                    "connections": connections_task.result()
                },
                "processes": processes_task.result(),
                "services": services_task.result(),
                "scheduled_tasks": tasks_task.result(),
                "installed_software": software_task.result(),
                "firewall": firewall_task.result(),
                "users": users_task.result(),
                "startup_programs": startup_task.result()
            }
        }
