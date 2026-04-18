"""EDR日志调查工具 - 服务端入口"""
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from server.api.routes import router as api_router, set_manager
from server.websocket.handler import ConnectionManager, WebSocketHandler


# 全局连接管理器
connection_manager = ConnectionManager()
ws_handler = WebSocketHandler(connection_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    set_manager(connection_manager)
    os.makedirs("temp_downloads", exist_ok=True)
    print(f"[{datetime.now()}] EDR Server started")
    yield
    # 关闭时
    print(f"[{datetime.now()}] EDR Server stopped")


app = FastAPI(
    title="EDR日志调查工具",
    description="远程日志调查与系统信息收集工具",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix="/api")


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    client_id: str = Query(...)
):
    """WebSocket连接端点"""
    # Token验证
    if not connection_manager.validate_token(token):
        await websocket.close(code=4001, reason="Invalid token")
        return

    # 连接
    await connection_manager.connect(websocket, client_id)
    print(f"[{datetime.now()}] Client connected: {client_id}")

    try:
        while True:
            data = await websocket.receive_text()
            await ws_handler.handle(client_id, data)
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
        print(f"[{datetime.now()}] Client disconnected: {client_id}")
    except Exception as e:
        print(f"[{datetime.now()}] WebSocket error: {e}")
        connection_manager.disconnect(client_id)


# 静态文件服务（前端）
WEB_DIR = Path(__file__).parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR / "src"), name="static")

    @app.get("/")
    async def serve_index():
        """服务前端页面"""
        index_path = WEB_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "Frontend not built. Access /docs for API documentation."}
else:
    @app.get("/")
    async def index():
        return {
            "message": "EDR日志调查工具 API",
            "docs": "/docs",
            "endpoints": {
                "websocket": "/ws?token=xxx&client_id=xxx",
                "api": "/api/..."
            }
        }


if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
