# EDR日志调查工具

一个基于 Python + FastAPI + Vue 的远程日志调查与系统信息收集工具，专为 EDR (端点检测与响应) 场景设计。

> 使用 AI 编程工具 (Claude Code) 开发
## AI使用
**Write|Review|Test：Claude Code+GLM 5.1**  
**Git Push:Opencode+Oh-My-Openagent+GLM5.1**  
本次项目完全使用**黑暗工厂**模式：
- No Human Write Code
- No Human Test Code
- No Human Review Code
## 功能特性

### 核心功能

| 功能 | 描述 |
|------|------|
| 远程命令执行 | 在客户端执行任意命令，支持中文正确显示 |
| 文件系统浏览 | 远程浏览目录结构、读取文件内容 |
| 文件下载 | 从客户端下载文件到服务端 |
| 文件上传 | 从服务端上传文件到客户端 |

### EDR 信息收集

- **系统基础信息**: 主机名、操作系统、架构、运行时间、当前用户
- **硬件信息**: CPU使用率、内存使用、磁盘使用情况
- **网络信息**: 网络接口、网络连接状态、DNS缓存
- **进程列表**: 进程名、PID、CPU/内存占用、命令行参数
- **服务列表**: Windows 服务状态
- **计划任务**: Windows 计划任务列表
- **已安装软件**: 从注册表读取已安装软件列表
- **防火墙状态**: Windows 防火墙配置
- **用户信息**: 本地用户列表
- **启动项**: 开机启动程序
- **日志搜索**: 关键字搜索系统日志文件

### 安全特性

- Token 认证机制
- WebSocket 实时双向通信
- 心跳保活机制

## 技术架构

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│                 │◄──────────────────►│                 │
│    服务端        │                    │    客户端        │
│  (FastAPI)      │     REST API       │   (Python)      │
│                 │◄──────────────────►│                 │
└─────────────────┘                    └─────────────────┘
        │
        │ HTTP
        ▼
┌─────────────────┐
│    前端界面      │
│  (Vue 3 + EP)   │
└─────────────────┘
```

## 项目结构

```
logProject/
├── server/                    # 服务端
│   ├── main.py               # FastAPI 入口
│   ├── api/
│   │   └── routes.py         # REST API 路由
│   ├── websocket/
│   │   └── handler.py        # WebSocket 连接管理
│   └── models/
│       └── schemas.py        # Pydantic 数据模型
│
├── client/                    # 客户端
│   ├── main.py               # 客户端入口
│   └── commands/
│       ├── executor.py       # 命令执行器
│       ├── file_ops.py       # 文件操作
│       ├── file_transfer.py  # 文件传输
│       └── system_info.py    # 系统信息收集
│
├── web/
│   └── index.html            # 前端单页应用
│
├── setup_env.ps1             # 环境初始化脚本
├── start_server.ps1          # 启动服务端
├── start_client.ps1          # 启动客户端
└── README.md
```

## 快速开始

### 环境要求

- Python 3.10+
- Anaconda / Miniconda

### 安装与运行

```powershell
# 1. 初始化环境 (首次运行)
.\setup_env.ps1

# 2. 启动服务端
.\start_server.ps1

# 3. 在另一个终端启动客户端
.\start_client.ps1
```

### 使用 Web 界面

1. 打开浏览器访问 `http://localhost:8000`
2. 点击 "获取Token" 生成认证 Token
3. 使用 Token 启动客户端
4. 在左侧选择在线客户端
5. 使用各功能标签页进行操作

## API 文档

启动服务端后访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

### 主要 API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/token` | 获取认证 Token |
| GET | `/api/clients` | 获取在线客户端列表 |
| POST | `/api/clients/{id}/execute` | 执行命令 |
| GET | `/api/clients/{id}/files` | 列出目录 |
| GET | `/api/clients/{id}/files/download` | 下载文件 |
| POST | `/api/clients/{id}/files/upload` | 上传文件 |
| GET | `/api/clients/{id}/system` | 获取系统信息 |
| GET | `/api/clients/{id}/network` | 获取网络信息 |
| GET | `/api/clients/{id}/processes` | 获取进程列表 |
| GET | `/api/clients/{id}/services` | 获取服务列表 |
| GET | `/api/clients/{id}/tasks` | 获取计划任务 |
| GET | `/api/clients/{id}/software` | 获取已安装软件 |
| GET | `/api/clients/{id}/firewall` | 获取防火墙状态 |
| GET | `/api/clients/{id}/logs/search` | 搜索日志 |
| GET | `/api/clients/{id}/edr/collect` | 一键收集所有 EDR 信息 |

## 技术栈

- **服务端**: Python 3.10, FastAPI, WebSocket
- **客户端**: Python 3.10, websockets, psutil
- **前端**: Vue 3, Element Plus (CDN)
- **通信协议**: WebSocket + JSON

## 注意事项

1. 本工具仅用于合法的日志调查和安全审计用途
2. 请确保在授权范围内使用
3. 客户端需要管理员权限才能获取完整的系统信息
4. 命令输出已支持中文正确显示 (UTF-8 编码)

## License

MIT
