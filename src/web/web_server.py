#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : web_server
@Date       : 2025/7/6 21:30
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: Web管理界面服务器
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config.config_manager import ConfigManager
from src.core.event_bus import EventBus
from src.core.event import Event, create_trading_event
from src.core.logger import get_logger
from src.services.trading_engine import TradingEngine

logger = get_logger("WebServer")


# Pydantic模型定义
class StrategyRequest(BaseModel):
    """策略加载请求"""
    strategy_id: str = Field(..., description="策略ID")
    strategy_path: str = Field(..., description="策略文件路径")
    params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")


class StrategyActionRequest(BaseModel):
    """策略操作请求"""
    strategy_id: str = Field(..., description="策略ID")


class SubscriptionRequest(BaseModel):
    """行情订阅请求"""
    symbols: List[str] = Field(..., description="合约列表")
    strategy_id: str = Field(..., description="策略ID")


class OrderRequest(BaseModel):
    """下单请求"""
    strategy_id: str = Field(..., description="策略ID")
    symbol: str = Field(..., description="合约代码")
    exchange: str = Field(..., description="交易所")
    direction: str = Field(..., description="方向")
    offset: str = Field(..., description="开平")
    price: float = Field(..., description="价格")
    volume: float = Field(..., description="数量")


class SystemResponse(BaseModel):
    """系统响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    timestamp: float = Field(default_factory=time.time, description="时间戳")


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_info: Optional[Dict[str, Any]] = None):
        """建立连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = client_info or {}
        logger.info(f"WebSocket连接建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_info.pop(websocket, None)
            logger.info(f"WebSocket连接断开，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送WebSocket消息失败: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)


class WebServer:
    """Web服务器"""
    
    def __init__(self, trading_engine: TradingEngine, event_bus: EventBus, config: ConfigManager):
        self.trading_engine = trading_engine
        self.event_bus = event_bus
        self.config = config
        
        # WebSocket管理器
        self.ws_manager = WebSocketManager()
        
        # 创建FastAPI应用
        self.app = self._create_app()
        
        # 设置事件监听
        self._setup_event_listeners()
        
        logger.info("Web服务器初始化完成")
    
    def _create_app(self) -> FastAPI:
        """创建FastAPI应用"""
        app = FastAPI(
            title="Homalos量化交易系统",
            description="基于Python的期货量化交易系统Web管理界面",
            version="2.0.0",
            docs_url="/docs" if self.config.get("web.api.enable_swagger", True) else None
        )
        
        # CORS中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("web.cors_origins", ["*"]),
            allow_credentials=True,
            allow_methods=self.config.get("web.cors_methods", ["GET", "POST", "PUT", "DELETE"]),
            allow_headers=self.config.get("web.cors_headers", ["*"]),
        )
        
        # 静态文件
        static_path = Path(__file__).parent / "static"
        if static_path.exists():
            app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
        
        # 路由注册
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI):
        """注册路由"""
        
        # 主页
        @app.get("/", response_class=HTMLResponse)
        async def home():
            """主页"""
            return self._get_static_html()
        
        # 系统状态API
        @app.get("/api/v1/system/status")
        async def get_system_status():
            """获取系统状态"""
            try:
                status = self.trading_engine.get_engine_status()
                return SystemResponse(
                    success=True,
                    message="系统状态获取成功",
                    data=status
                )
            except Exception as e:
                logger.error(f"获取系统状态失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # 策略管理API
        @app.get("/api/v1/strategies/discover")
        async def discover_strategies():
            """发现可用策略"""
            try:
                strategies = await self._discover_available_strategies()
                return SystemResponse(
                    success=True,
                    message="策略发现成功",
                    data={"available_strategies": strategies}
                )
            except Exception as e:
                logger.error(f"策略发现失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/v1/strategies")
        async def list_strategies():
            """获取策略列表"""
            try:
                strategies = self.trading_engine.strategy_manager.get_all_strategies()
                return SystemResponse(
                    success=True,
                    message="策略列表获取成功",
                    data={"strategies": strategies}
                )
            except Exception as e:
                logger.error(f"获取策略列表失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/v1/strategies")
        async def load_strategy(request: StrategyRequest):
            """加载策略"""
            try:
                success = await self.trading_engine.strategy_manager.load_strategy(
                    request.strategy_path,
                    request.strategy_id,
                    request.params
                )
                
                if success:
                    # 发布策略加载成功事件
                    self.event_bus.publish(create_trading_event(
                        "strategy.loaded",
                        {
                            "strategy_id": request.strategy_id,
                            "strategy_path": request.strategy_path,
                            "message": f"策略 {request.strategy_id} 加载成功"
                        },
                        "WebServer"
                    ))
                    
                    return SystemResponse(
                        success=True,
                        message=f"策略 {request.strategy_id} 加载成功"
                    )
                else:
                    # 发布策略加载失败事件
                    self.event_bus.publish(create_trading_event(
                        "strategy.load_failed",
                        {
                            "strategy_id": request.strategy_id,
                            "message": f"策略 {request.strategy_id} 加载失败"
                        },
                        "WebServer"
                    ))
                    raise HTTPException(status_code=400, detail="策略加载失败")
                    
            except Exception as e:
                logger.error(f"加载策略失败: {e}")
                # 发布策略加载错误事件
                self.event_bus.publish(create_trading_event(
                    "strategy.load_error",
                    {
                        "strategy_id": request.strategy_id,
                        "error": str(e),
                        "message": f"策略 {request.strategy_id} 加载出错: {e}"
                    },
                    "WebServer"
                ))
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/v1/strategies/{strategy_id}/start")
        async def start_strategy(strategy_id: str):
            """启动策略"""
            try:
                success = await self.trading_engine.strategy_manager.start_strategy(strategy_id)
                
                if success:
                    # 发布策略启动成功事件
                    self.event_bus.publish(create_trading_event(
                        "strategy.started",
                        {
                            "strategy_id": strategy_id,
                            "message": f"策略 {strategy_id} 启动成功"
                        },
                        "WebServer"
                    ))
                    
                    return SystemResponse(
                        success=True,
                        message=f"策略 {strategy_id} 启动成功"
                    )
                else:
                    # 发布策略启动失败事件
                    self.event_bus.publish(create_trading_event(
                        "strategy.start_failed",
                        {
                            "strategy_id": strategy_id,
                            "message": f"策略 {strategy_id} 启动失败"
                        },
                        "WebServer"
                    ))
                    raise HTTPException(status_code=400, detail="策略启动失败")
                    
            except Exception as e:
                logger.error(f"启动策略失败: {e}")
                # 发布策略启动错误事件
                self.event_bus.publish(create_trading_event(
                    "strategy.start_error",
                    {
                        "strategy_id": strategy_id,
                        "error": str(e),
                        "message": f"策略 {strategy_id} 启动出错: {e}"
                    },
                    "WebServer"
                ))
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/v1/strategies/{strategy_id}/stop")
        async def stop_strategy(strategy_id: str):
            """停止策略"""
            try:
                success = await self.trading_engine.strategy_manager.stop_strategy(strategy_id)
                
                if success:
                    # 发布策略停止成功事件
                    self.event_bus.publish(create_trading_event(
                        "strategy.stopped",
                        {
                            "strategy_id": strategy_id,
                            "message": f"策略 {strategy_id} 停止成功"
                        },
                        "WebServer"
                    ))
                    
                    return SystemResponse(
                        success=True,
                        message=f"策略 {strategy_id} 停止成功"
                    )
                else:
                    # 发布策略停止失败事件
                    self.event_bus.publish(create_trading_event(
                        "strategy.stop_failed",
                        {
                            "strategy_id": strategy_id,
                            "message": f"策略 {strategy_id} 停止失败"
                        },
                        "WebServer"
                    ))
                    raise HTTPException(status_code=400, detail="策略停止失败")
                    
            except Exception as e:
                logger.error(f"停止策略失败: {e}")
                # 发布策略停止错误事件
                self.event_bus.publish(create_trading_event(
                    "strategy.stop_error",
                    {
                        "strategy_id": strategy_id,
                        "error": str(e),
                        "message": f"策略 {strategy_id} 停止出错: {e}"
                    },
                    "WebServer"
                ))
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/v1/strategies/{strategy_id}")
        async def get_strategy_status(strategy_id: str):
            """获取策略状态"""
            try:
                status = self.trading_engine.strategy_manager.get_strategy_status(strategy_id)
                
                if status:
                    return SystemResponse(
                        success=True,
                        message="策略状态获取成功",
                        data=status
                    )
                else:
                    raise HTTPException(status_code=404, detail="策略不存在")
                    
            except Exception as e:
                logger.error(f"获取策略状态失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/v1/strategies/{strategy_id}/orders")
        async def get_strategy_orders(strategy_id: str):
            """获取策略订单"""
            try:
                orders = self.trading_engine.order_manager.get_strategy_orders(strategy_id)
                return SystemResponse(
                    success=True,
                    message="策略订单获取成功",
                    data={"orders": orders}
                )
            except Exception as e:
                logger.error(f"获取策略订单失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # 行情订阅API
        @app.post("/api/v1/market/subscribe")
        async def subscribe_market_data(request: SubscriptionRequest):
            """订阅行情"""
            try:
                # 通过事件总线发布订阅请求
                self.event_bus.publish(create_trading_event(
                    "data.subscribe",
                    {"symbols": request.symbols, "strategy_id": request.strategy_id},
                    "WebServer"
                ))
                
                return SystemResponse(
                    success=True,
                    message=f"行情订阅成功: {request.symbols}"
                )
            except Exception as e:
                logger.error(f"订阅行情失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # 账户信息API
        @app.get("/api/v1/account")
        async def get_account_info():
            """获取账户信息"""
            try:
                account_info = self.trading_engine.account_manager.get_total_account_info()
                return SystemResponse(
                    success=True,
                    message="账户信息获取成功",
                    data=account_info
                )
            except Exception as e:
                logger.error(f"获取账户信息失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # 性能监控API
        @app.get("/api/v1/monitoring/stats")
        async def get_monitoring_stats():
            """获取监控统计"""
            try:
                # 这里可以添加性能监控数据
                stats = {
                    "system": self.trading_engine.get_engine_status(),
                    "timestamp": time.time()
                }
                
                return SystemResponse(
                    success=True,
                    message="监控统计获取成功",
                    data=stats
                )
            except Exception as e:
                logger.error(f"获取监控统计失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # WebSocket端点
        @app.websocket("/ws/realtime")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket实时数据推送"""
            await self.ws_manager.connect(websocket, {"connect_time": time.time()})
            
            try:
                while True:
                    # 保持连接活跃
                    data = await websocket.receive_text()
                    
                    # 处理客户端消息（心跳等）
                    try:
                        message = json.loads(data)
                        if message.get("type") == "ping":
                            await self.ws_manager.send_personal_message(
                                {"type": "pong", "timestamp": time.time()},
                                websocket
                            )
                    except json.JSONDecodeError:
                        pass
                        
            except WebSocketDisconnect:
                self.ws_manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket异常: {e}")
                self.ws_manager.disconnect(websocket)
    
    def _setup_event_listeners(self):
        """设置事件监听器"""
        def event_monitor(event: Event):
            """事件监控器，推送实时更新"""
            try:
                # 扩展需要推送的事件类型，包含策略相关事件
                push_events = [
                    "strategy.loaded", "strategy.started", "strategy.stopped", "strategy.error",
                    "strategy.load_failed", "strategy.start_failed", "strategy.stop_failed",
                    "strategy.load_error", "strategy.start_error", "strategy.stop_error",
                    "strategy.signal", "order.submitted", "order.filled", "order.cancelled",
                    "risk.rejected", "system.error", "engine.started", "engine.stopped"
                ]
                
                if any(event.type.startswith(prefix) for prefix in push_events):
                    message = {
                        "type": "event",
                        "event_type": event.type,
                        "data": self._serialize_event_data(event.data),
                        "source": event.source,
                        "timestamp": event.timestamp / 1_000_000_000  # 转换为秒
                    }
                    
                    # 异步广播消息
                    asyncio.create_task(self.ws_manager.broadcast(message))
                    
            except Exception as e:
                logger.error(f"事件推送失败: {e}")
        
        # 注册事件监控器
        self.event_bus.add_monitor(event_monitor)
    
    def _serialize_event_data(self, data: Any) -> Any:
        """序列化事件数据"""
        try:
            if hasattr(data, '__dict__'):
                # 对象转换为字典
                return {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
            else:
                return data
        except Exception:
            return str(data)
    
    async def _discover_available_strategies(self) -> List[Dict[str, Any]]:
        """发现可用策略文件"""
        try:
            from pathlib import Path
            import importlib.util
            import inspect
            from src.strategies.base_strategy import BaseStrategy
            
            strategies = []
            strategy_dir = Path("src/strategies")
            
            if not strategy_dir.exists():
                logger.warning("策略目录不存在")
                return strategies
            
            # 扫描策略文件
            for strategy_file in strategy_dir.glob("*.py"):
                if strategy_file.name.startswith("__") or strategy_file.name in ["base_strategy.py", "strategy_factory.py"]:
                    continue
                
                try:
                    # 尝试动态导入模块
                    spec = importlib.util.spec_from_file_location(
                        strategy_file.stem, str(strategy_file)
                    )
                    
                    if spec is None or spec.loader is None:
                        continue
                    
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 查找策略类
                    strategy_classes = []
                    detected_classes = set()  # 添加去重集合
                    
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseStrategy) and 
                            obj != BaseStrategy and
                            obj.__name__ not in detected_classes):  # 避免重复检测
                            
                            try:
                                # 验证策略类必要属性
                                if not (hasattr(obj, 'strategy_name') or hasattr(obj, '__name__')):
                                    logger.warning(f"策略类 {name} 缺少必要属性，跳过")
                                    continue
                                    
                                # 读取策略类的简洁属性而非docstring
                                strategy_info = {
                                    "class_name": obj.__name__,  # 使用类的真实名称
                                    "name": getattr(obj, "strategy_name", obj.__name__),
                                    "authors": getattr(obj, "authors", getattr(obj, "strategy_author", "未知")),
                                    "version": getattr(obj, "version", getattr(obj, "strategy_version", "1.0.0")),
                                    "description": getattr(obj, "description", getattr(obj, "strategy_description", "无描述"))
                                }
                                
                                strategy_classes.append(strategy_info)
                                detected_classes.add(obj.__name__)  # 记录已检测的类
                                
                            except AttributeError as e:
                                logger.debug(f"策略类 {name} 属性访问错误: {e}")
                                continue
                    
                    if strategy_classes:
                        strategies.append({
                            "file_name": strategy_file.name,
                            "file_path": str(strategy_file),
                            "strategy_classes": strategy_classes,
                            "is_template": "template" in strategy_file.name.lower()
                        })
                        
                except Exception as e:
                    logger.debug(f"跳过策略文件 {strategy_file.name}: {e}")
                    continue
            
            logger.info(f"发现 {len(strategies)} 个策略文件")
            return strategies
            
        except Exception as e:
            logger.error(f"策略发现失败: {e}")
            return []

    def _get_static_html(self) -> str:
        """获取静态HTML页面"""
        try:
            static_index_path = Path(__file__).parent / "static" / "index.html"
            if static_index_path.exists():
                return static_index_path.read_text(encoding='utf-8')
            else:
                # 如果静态文件不存在，返回简单的错误页面
                return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Homalos量化交易系统</title>
</head>
<body>
    <div style="text-align: center; padding: 2rem;">
        <h1>🚀 Homalos量化交易系统</h1>
        <p>静态文件正在加载中...</p>
        <p><a href="/docs">查看API文档</a></p>
    </div>
</body>
</html>'''
        except Exception as e:
            logger.error(f"读取静态HTML文件失败: {e}")
            return f"<html><body><h1>页面加载错误</h1><p>{str(e)}</p></body></html>"
    
    async def start(self, host: str = None, port: int = None):
        """启动Web服务器"""
        import uvicorn
        
        host = host or self.config.get("web.host", "0.0.0.0")
        port = port or self.config.get("web.port", 8000)
        debug = self.config.get("web.debug", False)
        
        logger.info(f"Web服务器启动: http://{host}:{port}")
        
        # 使用uvicorn启动服务器
        config = uvicorn.Config(
            self.app, 
            host=host, 
            port=port, 
            log_level="info" if not debug else "debug"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def run_sync(self, host: str = None, port: int = None):
        """同步启动Web服务器"""
        import uvicorn
        
        host = host or self.config.get("web.host", "0.0.0.0")
        port = port or self.config.get("web.port", 8000)
        debug = self.config.get("web.debug", False)
        
        logger.info(f"Web服务器启动: http://{host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info" if not debug else "debug"
        ) 