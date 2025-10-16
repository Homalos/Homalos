#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_api.py
@Date       : 2025/10/16 12:06
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: FastAPI — REST + WebSocket
- `/api/strategies` GET 列出注册策略
- `/api/strategies/{sid}/start` POST 启动
- `/api/strategies/{sid}/stop` POST 停止
- `/api/strategies/{sid}/reload` POST 重载
- `/ws` WebSocket：连接后订阅所有策略回传消息（支持 `?filter=sid` 查询参数可选）

- 在 `startup` 时我们 `set_event_loop(loop)`，并启动 `watchdog`、自动加载 `enabled` 的策略。
- WS 客户端每个都有自己的 `asyncio.Queue`，Manager 的 reader 线程会把消息 `call_soon_threadsafe` 放到这些 queues。
- 你可以通过 `GET /api/strategies` 查看注册中心配置并用 `POST /api/strategies/<sid>/start` 动态启动。
"""
import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path

from src.core.strategy_manager import StrategyManagerIPC

app = FastAPI(title="Strategy Manager API")

# CORS (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate manager (adjust paths as needed)
# strategies_pkg assumed used by child import; registry_path is strategies.json file
ROOT = Path(__file__).parent.parent
REGISTRY_PATH = ROOT / "strategies.json"
MANAGER = StrategyManagerIPC(strategies_pkg="src.strategy", registry_path=str(REGISTRY_PATH))

# on startup register event loop for manager
@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    MANAGER.set_event_loop(loop)
    MANAGER.start_watchdog(str(ROOT / "src" / "strategy"))
    # optionally auto-start enabled strategies
    for sid, cfg in MANAGER.registry.list_enabled().items():
        MANAGER.load_strategy(sid)
    app.state.ws_connections = set()
    print("API started")

@app.on_event("shutdown")
async def shutdown_event():
    # stop watchdog and unload strategies
    MANAGER.stop_watchdog()
    for sid in list(MANAGER._meta.keys()):
        MANAGER.unload_strategy(sid)
    print("API stopped")

# REST endpoints
@app.get("/api/strategies")
def list_strategies():
    return JSONResponse(MANAGER.registry.list_all())

@app.post("/api/strategies/{sid}/start")
def start_strategy(sid: str):
    if sid not in MANAGER.registry.strategies:
        return JSONResponse({"error": "not found"}, status_code=404)
    MANAGER.load_strategy(sid)
    return {"status": "started", "sid": sid}

@app.post("/api/strategies/{sid}/stop")
def stop_strategy(sid: str):
    MANAGER.unload_strategy(sid)
    return {"status": "stopped", "sid": sid}

@app.post("/api/strategies/{sid}/reload")
def reload_strategy(sid: str):
    MANAGER.reload_strategy(sid)
    return {"status": "reloaded", "sid": sid}

@app.post("/api/strategies/{sid}/enable")
def enable_strategy(sid: str):
    MANAGER.registry.strategies.setdefault(sid, {})
    MANAGER.registry.strategies[sid]["enabled"] = True
    MANAGER.registry.save()
    return {"status": "enabled", "sid": sid}

@app.post("/api/strategies/{sid}/disable")
def disable_strategy(sid: str):
    if sid in MANAGER.registry.strategies:
        MANAGER.registry.strategies[sid]["enabled"] = False
        MANAGER.registry.save()
    return {"status": "disabled", "sid": sid}

@app.get("/api/status")
def status():
    meta = {}
    for sid, m in MANAGER._meta.items():
        proc = m.get("proc")
        meta[sid] = {
            "pid": proc.pid if proc else None,
            "alive": proc.is_alive() if proc else False,
            "module": m.get("module"),
            "class": m.get("class")
        }
    return {"running": meta}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, filter: str = None):
    """
    Connect to receive real-time messages from strategies.
    Optional query param filter=<sid> to only receive messages for a specific strategy.
    """
    await websocket.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    MANAGER.register_ws_queue(q)
    try:
        while True:
            msg = await q.get()
            # optional filtering by sid
            if filter and msg.get("sid") != filter:
                continue
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        MANAGER.unregister_ws_queue(q)
    except Exception:
        MANAGER.unregister_ws_queue(q)
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run("api.main_api:app", host="0.0.0.0", port=8000, reload=False)
