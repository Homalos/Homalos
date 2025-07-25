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
import datetime
import inspect
import json
import time
from dataclasses import is_dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, cast

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config.config_manager import ConfigManager
from src.core.event import Event, create_trading_event
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.strategy.base_strategy import BaseStrategy
from src.trade.trading_engine import TradingEngine

logger = get_logger("WebServer")


# Pydantic模型定义
class StrategyRequest(BaseModel):
    """策略加载请求"""
    strategy_path: str = Field(..., description="策略文件路径")
    strategy_name: Optional[str] = Field(None, description="策略名称（可选）")
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
    
    async def broadcast_kline_update(self, symbol: str, interval: str, kline_data: Dict[str, Any]):
        """广播K线数据更新"""
        message = {
            "type": "kline_update",
            "symbol": symbol,
            "interval": interval,
            "data": kline_data,
            "timestamp": time.time()
        }
        await self.broadcast(message)
    
    async def broadcast_trading_signal(self, signal_data: Dict[str, Any]):
        """广播交易信号"""
        message = {
            "type": "trading_signal",
            "data": signal_data,
            "timestamp": time.time()
        }
        await self.broadcast(message)
    
    async def broadcast_order_update(self, order_data: Dict[str, Any]):
        """广播订单更新"""
        message = {
            "type": "order_update",
            "data": order_data,
            "timestamp": time.time()
        }
        await self.broadcast(message)
    
    async def broadcast_strategy_performance(self, strategy_name: str, performance_data: Dict[str, Any]):
        """广播策略绩效更新"""
        message = {
            "type": "strategy_performance",
            "strategy_name": strategy_name,
            "data": performance_data,
            "timestamp": time.time()
        }
        await self.broadcast(message)


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
            version="0.0.1",
            docs_url="/docs" if self.config.get("web.api.enable_swagger", True) else None
        )
        
        # CORS中间件
        app.add_middleware(
            cast(Any, CORSMiddleware),
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
            """加载策略 - UUID自动生成"""
            try:
                success, strategy_uuid = await self.trading_engine.strategy_manager.load_strategy(
                    request.strategy_path,
                    request.strategy_name,
                    request.params
                )
                
                if success:
                    return SystemResponse(
                        success=True,
                        message="策略加载成功",
                        data={
                            "strategy_uuid": strategy_uuid,
                            "strategy_path": request.strategy_path,
                            "strategy_name": request.strategy_name
                        }
                    )
                else:
                    raise HTTPException(status_code=400, detail="策略加载失败")
                    
            except Exception as e:
                logger.error(f"加载策略失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/v1/strategies/{strategy_uuid}/start")
        async def start_strategy(strategy_uuid: str):
            """启动策略 - 使用UUID"""
            try:
                success = await self.trading_engine.strategy_manager.start_strategy(strategy_uuid)
                
                if success:
                    return SystemResponse(
                        success=True,
                        message="策略启动成功",
                        data={"strategy_uuid": strategy_uuid}
                    )
                else:
                    raise HTTPException(status_code=400, detail="策略启动失败")
                    
            except Exception as e:
                logger.error(f"启动策略失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/v1/strategies/{strategy_uuid}/stop")
        async def stop_strategy(strategy_uuid: str):
            """停止策略 - 使用UUID"""
            try:
                success = await self.trading_engine.strategy_manager.stop_strategy(strategy_uuid)
                
                if success:
                    return SystemResponse(
                        success=True,
                        message="策略停止成功",
                        data={"strategy_uuid": strategy_uuid}
                    )
                else:
                    raise HTTPException(status_code=400, detail="策略停止失败")
                    
            except Exception as e:
                logger.error(f"停止策略失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/v1/strategies/{strategy_uuid}")
        async def get_strategy_status(strategy_uuid: str):
            """获取策略状态 - 使用UUID"""
            try:
                status = self.trading_engine.strategy_manager.get_strategy_status(strategy_uuid)
                
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
        
        @app.get("/api/v1/strategies/{strategy_uuid}/orders")
        async def get_strategy_orders(strategy_uuid: str):
            """获取策略订单"""
            try:
                orders = self.trading_engine.order_manager.get_strategy_orders(strategy_uuid)
                return SystemResponse(
                    success=True,
                    message="策略订单获取成功",
                    data={"orders": orders}
                )
            except Exception as e:
                logger.error(f"获取策略订单失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/v1/market/subscribe")
        async def subscribe_market_data(request: SubscriptionRequest):
            """订阅行情"""
            try:
                # 通过事件总线发布订阅请求
                self.event_bus.publish(create_trading_event(
                    "data.subscribe",
                    { "symbols": request.symbols, "strategy_id": request.strategy_id },
                    "WebServer"
                ))
                
                return SystemResponse(
                    success=True,
                    message=f"行情订阅成功: {request.symbols}",
                    data={"symbols": request.symbols}
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
        
        # 交易图表相关API
        @app.get("/api/v1/chart/kline")
        async def get_kline_data(
            symbol: str,
            interval: str = "1m",
            limit: int = 200,
            start_time: Optional[int] = None,
            end_time: Optional[int] = None
        ):
            """获取K线数据"""
            try:
                # 从数据中心获取K线数据
                data_center = getattr(self.trading_engine, 'data_center', None)
                if not data_center:
                    raise HTTPException(status_code=500, detail="数据中心未初始化")
                
                # 构造K线数据请求参数
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                }
                
                if start_time:
                    params["start_time"] = start_time
                if end_time:
                    params["end_time"] = end_time
                
                # 获取K线数据（这里需要根据实际的数据中心接口调整）
                kline_data = []
                # TODO: 实现从Redis/SQLite获取K线数据的逻辑
                # kline_data = data_center.get_kline_data(**params)
                
                return SystemResponse(
                    success=True,
                    message="K线数据获取成功",
                    data={
                        "symbol": symbol,
                        "interval": interval,
                        "data": kline_data
                    }
                )
                
            except Exception as e:
                logger.error(f"获取K线数据失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/v1/chart/signals")
        async def get_trading_signals(
            symbol: str,
            strategy_name: Optional[str] = None,
            start_time: Optional[int] = None,
            end_time: Optional[int] = None,
            limit: int = 100
        ):
            """获取交易信号"""
            try:
                # 从交易引擎获取交易信号
                signals = []
                # TODO: 实现从数据库或缓存获取交易信号的逻辑
                # signals = self.trading_engine.get_trading_signals(
                #     symbol=symbol,
                #     strategy_name=strategy_name,
                #     start_time=start_time,
                #     end_time=end_time,
                #     limit=limit
                # )
                
                return SystemResponse(
                    success=True,
                    message="交易信号获取成功",
                    data={
                        "symbol": symbol,
                        "strategy_name": strategy_name,
                        "signals": signals
                    }
                )
                
            except Exception as e:
                logger.error(f"获取交易信号失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/v1/chart/orders")
        async def get_order_history(
            symbol: Optional[str] = None,
            strategy_name: Optional[str] = None,
            start_time: Optional[int] = None,
            end_time: Optional[int] = None,
            limit: int = 100
        ):
            """获取订单历史"""
            try:
                # 从交易引擎获取订单历史
                orders = []
                # TODO: 实现从数据库获取订单历史的逻辑
                # orders = self.trading_engine.get_order_history(
                #     symbol=symbol,
                #     strategy_name=strategy_name,
                #     start_time=start_time,
                #     end_time=end_time,
                #     limit=limit
                # )
                
                return SystemResponse(
                    success=True,
                    message="订单历史获取成功",
                    data={
                        "symbol": symbol,
                        "strategy_name": strategy_name,
                        "orders": orders
                    }
                )
                
            except Exception as e:
                logger.error(f"获取订单历史失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/v1/chart/performance")
        async def get_strategy_performance(
            strategy_name: str,
            start_time: Optional[int] = None,
            end_time: Optional[int] = None
        ):
            """获取策略绩效"""
            try:
                # 从交易引擎获取策略绩效
                performance = {}
                # TODO: 实现策略绩效计算逻辑
                # performance = self.trading_engine.get_strategy_performance(
                #     strategy_name=strategy_name,
                #     start_time=start_time,
                #     end_time=end_time
                # )
                
                return SystemResponse(
                    success=True,
                    message="策略绩效获取成功",
                    data={
                        "strategy_name": strategy_name,
                        "performance": performance
                    }
                )
                
            except Exception as e:
                logger.error(f"获取策略绩效失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/v1/chart/performance/all")
        async def get_all_strategy_performance(
            start_time: Optional[int] = None,
            end_time: Optional[int] = None
        ):
            """获取所有策略绩效"""
            try:
                # 获取所有活跃策略的绩效
                all_performance = {}
                # TODO: 实现获取所有策略的逻辑
                # active_strategies = self.trading_engine.get_active_strategies()
                
                # for strategy_name in active_strategies:
                #     performance = self.trading_engine.get_strategy_performance(
                #         strategy_name=strategy_name,
                #         start_time=start_time,
                #         end_time=end_time
                #     )
                #     all_performance[strategy_name] = performance
                
                return SystemResponse(
                    success=True,
                    message="所有策略绩效获取成功",
                    data={
                        "strategies": all_performance
                    }
                )
                
            except Exception as e:
                logger.error(f"获取所有策略绩效失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/v1/chart/symbols")
        async def get_available_symbols():
            """获取可用交易品种"""
            try:
                # 从交易引擎或数据中心获取可用交易品种
                symbols = []
                # TODO: 实现获取可用交易品种的逻辑
                # symbols = self.trading_engine.get_available_symbols()
                
                return SystemResponse(
                    success=True,
                    message="可用交易品种获取成功",
                    data={
                        "symbols": symbols
                    }
                )
                
            except Exception as e:
                logger.error(f"获取可用交易品种失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
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
                    "risk.rejected", "system.error", "engine.started", "engine.stopped",
                    "kline.update", "bar.generated", "tick.received", "signal.generated",
                    "order.update", "strategy.performance"
                ]
                
                # 处理不同格式的事件数据
                if isinstance(event, dict):
                    # EnhancedEventBus格式的事件数据
                    event_type = event.get('type', 'unknown')
                    event_data = event.get('data', {})
                    event_source = event.get('source', 'unknown')
                    event_timestamp = event.get('timestamp', time.time())
                else:
                    # Event对象格式
                    event_type = getattr(event, 'type', getattr(event, 'event_type', 'unknown'))
                    event_data = getattr(event, 'data', {})
                    event_source = getattr(event, 'source', 'unknown')
                    event_timestamp = getattr(event, 'timestamp', time.time() * 1_000_000_000)
                
                # 调试日志：记录所有接收到的事件
                logger.debug(f"WebSocket事件监控器收到事件: {event_type} from {event_source}")
                
                # 使用更宽松的匹配条件，确保策略事件能被捕获
                should_push = (any(event_type.startswith(prefix) for prefix in push_events) or 
                              "strategy." in event_type or 
                              event_type in push_events)
                
                if should_push:
                    logger.info(f"WebSocket推送事件: {event_type} -> {len(self.ws_manager.active_connections)} 个连接")
                    
                    # 处理时间戳格式
                    if isinstance(event_timestamp, (int, float)) and event_timestamp > 1e12:
                        # 纳秒时间戳，转换为秒
                        timestamp_seconds = event_timestamp / 1_000_000_000
                    else:
                        # 已经是秒时间戳
                        timestamp_seconds = event_timestamp
                    
                    message = {
                        "type": "event",
                        "event_type": event_type,
                        "data": self._serialize_event_data(event_data),
                        "source": event_source,
                        "timestamp": timestamp_seconds
                    }
                    
                    # 根据事件类型使用特殊的广播方法
                    if event_type in ["kline.update", "bar.generated"]:
                        # K线数据更新
                        symbol = event_data.get('symbol', '')
                        interval = event_data.get('interval', '1m')
                        kline_data = event_data.get('bar', event_data.get('kline', {}))
                        asyncio.create_task(self.ws_manager.broadcast_kline_update(symbol, interval, kline_data))
                    elif event_type in ["strategy.signal", "signal.generated"]:
                        # 交易信号
                        asyncio.create_task(self.ws_manager.broadcast_trading_signal(event_data))
                    elif event_type in ["order.submitted", "order.filled", "order.cancelled", "order.update"]:
                        # 订单更新
                        asyncio.create_task(self.ws_manager.broadcast_order_update(event_data))
                    elif event_type == "strategy.performance":
                        # 策略绩效更新
                        strategy_name = event_data.get('strategy_name', '')
                        performance_data = event_data.get('performance', {})
                        asyncio.create_task(self.ws_manager.broadcast_strategy_performance(strategy_name, performance_data))
                    else:
                        # 其他事件使用通用广播
                        # 调试日志：记录推送的消息内容
                        logger.debug(f"WebSocket推送消息: {message}")
                        asyncio.create_task(self.ws_manager.broadcast(message))
                    
            except Exception as e:
                logger.error(f"事件推送失败: {e}")
                import traceback
                logger.error(f"错误详情: {traceback.format_exc()}")
        
        # 注册事件监控器 - 兼容不同类型的事件总线
        if hasattr(self.event_bus, 'add_monitor'):
            # 普通EventBus
            self.event_bus.add_monitor(event_monitor)
        elif hasattr(self.event_bus, 'subscribe_global'):
            # EnhancedEventBus
            self.event_bus.subscribe_global(event_monitor)
        else:
            logger.warning("Event bus does not support monitoring")
        logger.info("WebSocket事件监控器已注册")
    
    def _serialize_event_data(self, data: Any) -> Any:
        """序列化事件数据"""
        try:
            # 处理None值
            if data is None:
                return None
            
            # 处理基本类型
            if isinstance(data, (str, int, float, bool)):
                return data
            
            # 处理枚举类型
            if isinstance(data, Enum):
                return data.value
            
            # 处理datetime对象
            if isinstance(data, datetime.datetime):
                return data.isoformat()
            
            # 处理列表和元组
            if isinstance(data, (list, tuple)):
                return [self._serialize_event_data(item) for item in data]
            
            # 处理字典
            if isinstance(data, dict):
                return {k: self._serialize_event_data(v) for k, v in data.items()}
            
            # 处理dataclass对象
            if is_dataclass(data):
                # 使用asdict转换dataclass，然后递归序列化
                data_dict = asdict(data)
                return self._serialize_event_data(data_dict)
            
            # 处理其他有__dict__属性的对象
            if hasattr(data, '__dict__'):
                obj_dict = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
                return self._serialize_event_data(obj_dict)
            
            # 其他情况转换为字符串
            return str(data)
            
        except Exception as e:
            logger.error(f"序列化事件数据失败: {e}, 数据类型: {type(data)}")
            return str(data)

    @staticmethod
    async def _discover_available_strategies() -> List[Dict[str, Any]]:
        """发现可用策略文件"""
        try:
            import importlib.util

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

    @staticmethod
    def _get_static_html() -> str:
        """获取静态HTML页面"""
        try:
            static_index_path = Path(__file__).parent / "static" / "index.html"
            if static_index_path.exists():
                return static_index_path.read_text(encoding='utf-8')
            else:
                return WebServer._load_error_template("error_404.html")
        except Exception as e:
            logger.error(f"读取静态HTML文件失败: {e}")
            return WebServer._load_error_template("error_500.html", str(e))
    
    @staticmethod
    def _load_error_template(template_name: str, error_message: Optional[str] = None) -> str:
        """加载错误页面模板"""
        template_path = Path(__file__).parent / "static" / template_name
        try:
            template_content = template_path.read_text(encoding='utf-8')
            if error_message and "{{ERROR_MESSAGE}}" in template_content:
                template_content = template_content.replace("{{ERROR_MESSAGE}}", error_message)
            return template_content
        except Exception:
            # 如果模板文件也无法加载，返回最基本的错误页面
            if error_message:
                return f"<html><body><h1>页面加载错误</h1><p>{error_message}</p></body></html>"
            else:
                return "<html><body><h1>页面加载错误</h1><p>静态HTML文件不存在</p></body></html>"
    
    async def start(self, host: Optional[str] = None, port: Optional[int] = None):
        """启动Web服务器"""
        actual_host: str = host or self.config.get("web.host", "0.0.0.0")
        actual_port: int = port or self.config.get("web.port", 8000)
        debug = self.config.get("web.debug", False)
        
        logger.info(f"Web服务器启动: http://{actual_host}:{actual_port}")
        
        # 使用uvicorn启动服务器
        config = uvicorn.Config(
            self.app, 
            host=actual_host, 
            port=actual_port, 
            log_level="info" if not debug else "debug"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def run_sync(self, host: Optional[str] = None, port: Optional[int] = None):
        """同步启动Web服务器"""
        actual_host: str = host or self.config.get("web.host", "0.0.0.0")
        actual_port: int = port or self.config.get("web.port", 8000)
        debug = self.config.get("web.debug", False)
        
        logger.info(f"Web服务器启动: http://{actual_host}:{actual_port}")
        
        uvicorn.run(
            self.app,
            host=actual_host,
            port=actual_port,
            log_level="info" if not debug else "debug"
        )

# Web页面由start_homalos.py启动
# if __name__ == "__main__":
#     # 创建简单的配置管理器用于演示
#     from src.config.config_manager import ConfigManager
#     from src.core.event_bus import EventBus
#     from src.trade.trading_engine import TradingEngine
#
#     # 初始化组件
#     config = ConfigManager("config/system.yaml")
#     event_bus = EventBus()
#     trading_engine = TradingEngine(event_bus, config)
#
#     # 创建并启动Web服务器
#     web_server = WebServer(trading_engine, event_bus, config)
#     web_server.run_sync()