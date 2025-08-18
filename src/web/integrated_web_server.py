#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : web_server
@Date       : 2025/7/6 21:35
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 集成Web服务器，将事件监控仪表板集成到主Web服务中
"""
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict, Tuple, Any as AnyType

from fastapi import HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from websockets.exceptions import ConnectionClosedOK

from src.core.event_monitor import EventMonitor
from src.web.web_server import WebServer, SystemResponse

logger = logging.getLogger(__name__)


class IntegratedWebServer(WebServer):
    """
    集成Web服务器
    
    继承原有Web服务器功能，并集成事件监控仪表板
    """
    
    def __init__(self, trading_engine: Any, event_bus: Any, config: Any, event_monitor: Optional[EventMonitor] = None) -> None:
        super().__init__(trading_engine, event_bus, config)
        self.event_monitor = event_monitor
        
        # 添加事件监控相关路由
        self._setup_dashboard_routes()
    
    async def start(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        """启动集成Web服务器"""
        # 保存当前事件循环引用（确保IntegratedWebServer也能正确保存）
        try:
            self._main_loop = asyncio.get_running_loop()
            logger.debug("集成Web服务器已保存事件循环引用")
        except RuntimeError:
            logger.warning("集成Web服务器无法获取运行中的事件循环")
        
        # 调用父类的启动方法
        await super().start(host, port)
    
    def shutdown(self) -> None:
        """关闭集成Web服务器"""
        logger.info("正在关闭集成Web服务器...")
        # 调用父类的shutdown方法停止事件处理
        super().shutdown()
        logger.info("集成Web服务器已关闭")
    
    def _setup_dashboard_routes(self) -> None:
        """设置事件监控仪表板路由"""
        
        @self.app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard() -> Any:
            """事件监控仪表板页面"""
            return self._get_dashboard_html()
        
        @self.app.get("/chart.html", response_class=HTMLResponse)
        async def chart_page() -> Any:
            """交易图表页面"""
            return self._get_chart_html()
        
        @self.app.get("/api/dashboard/stats")
        async def dashboard_stats() -> Any:
            """获取事件统计数据"""
            if not self.event_monitor:
                raise HTTPException(status_code=503, detail="事件监控器未启用")
            
            try:
                stats = self.event_monitor.get_statistics()
                return self._serialize_dashboard_data(stats)
            except Exception as e:
                logger.error(f"获取仪表板统计数据失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/dashboard/timeseries")
        async def dashboard_timeseries(minutes: int = 60) -> Any:
            """获取时间序列数据"""
            if not self.event_monitor:
                raise HTTPException(status_code=503, detail="事件监控器未启用")
            
            try:
                # 使用基础监控接口聚合多种时间序列
                series_metrics: List[str] = [
                    "event_count", "processing_time", "queue_wait_time", "error_rate", "throughput"
                ]
                timeseries: Dict[str, List[Tuple[float, float]]] = {}
                for metric in series_metrics:
                    timeseries[metric] = self.event_monitor.get_time_series_data(metric, minutes)
                return self._serialize_dashboard_data(timeseries)
            except Exception as e:
                logger.error(f"获取时间序列数据失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/dashboard/alerts")
        async def dashboard_alerts(limit: int = 50) -> Any:
            """获取告警信息"""
            if not self.event_monitor:
                raise HTTPException(status_code=503, detail="事件监控器未启用")
            
            try:
                alerts = self.event_monitor.get_recent_alerts(limit)
                return self._serialize_dashboard_data(alerts)
            except Exception as e:
                logger.error(f"获取告警信息失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/test/publish_event")
        async def test_publish_event(event_type: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """测试事件发布API"""
            try:
                from src.core.event import Event
                event = Event(event_type, data or {})
                self.event_bus.publish(event)
                return {
                    "success": True,
                    "message": f"事件已发布: {event_type}",
                    "event_id": event.trace_id
                }
            except Exception as e:
                logger.error(f"发布测试事件失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/test/publish_batch_events")
        async def test_publish_batch_events(request: Request) -> Dict[str, Any]:
            """批量发布测试事件"""
            try:
                # 获取事件数量，默认为5
                count = 5
                try:
                    body = await request.json()
                    if isinstance(body, dict) and 'count' in body:
                        count = min(max(int(body['count']), 1), 20)  # 限制在1-20之间
                except Exception:
                    pass  # 使用默认值
                
                test_events: List[Tuple[str, Dict[str, Any]]] = [
                    ("test.success", {"message": "成功测试事件", "value": 100}),
                    ("test.warning", {"message": "警告测试事件", "level": "warning"}),
                    ("test.error", {"message": "错误测试事件", "error_code": 500}),
                    ("strategy.update", {"strategy_id": "test_strategy", "status": "running"}),
                    ("trading.order", {"order_id": "test_order_001", "symbol": "BTCUSDT", "side": "buy"}),
                    ("market.tick", {"symbol": "FG509", "price": 2400.0, "volume": 1.5}),
                    ("risk.alert", {"message": "风险警告", "level": "high"}),
                    ("system.info", {"message": "系统信息", "component": "web_server"})
                ]
                
                published_events: List[Dict[str, Any]] = []
                for i in range(count):
                    event_type, event_data = test_events[i % len(test_events)]
                    # 为每个事件添加唯一标识
                    event_data_copy = event_data.copy()
                    event_data_copy['batch_id'] = i + 1
                    event_data_copy['timestamp'] = time.time()
                    
                    # 使用基础事件总线：构造 Event 对象再发布
                    try:
                        from src.core.event import Event
                        event = Event(event_type, event_data_copy)
                        self.event_bus.publish(event)
                        event_id = event.trace_id
                        logger.debug(f"成功发布事件: {event_type}, event_id: {event_id}")
                    except Exception as event_error:
                        import traceback
                        logger.error(f"发布事件失败: {event_error}")
                        logger.error(f"事件类型: {event_type}")
                        logger.error(f"事件数据: {event_data_copy}")
                        logger.error(f"完整堆栈跟踪:\n{traceback.format_exc()}")
                        raise
                    published_events.append({
                        "event_type": event_type,
                        "event_id": event_id,
                        "data": event_data_copy
                    })
                
                return {
                    "success": True,
                    "message": f"已发布 {len(published_events)} 个测试事件",
                    "events": published_events
                }
            except Exception as e:
                logger.error(f"批量发布测试事件失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # 交易图表相关API - 只有在策略运行时才返回数据
        @self.app.get("/api/v1/trading/signals")
        async def get_trading_signals(
            strategy_uuid: Optional[str] = None,
            symbol: Optional[str] = None,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None
        ) -> Any:
            """获取交易信号 - 只有在策略运行时才返回数据"""
            try:
                # 检查是否有运行中的策略
                running_strategies = []
                if hasattr(self.trading_engine, 'strategy_manager'):
                    all_strategies = self.trading_engine.strategy_manager.get_all_strategies()
                    running_strategies = [s for s in all_strategies.values() if s.get('status') == 'running']
                
                # 如果没有运行中的策略，返回空数据
                if not running_strategies:
                    return SystemResponse(
                        success=True,
                        message="当前没有运行中的策略",
                        data={
                            "signals": [],
                            "running_strategies": []
                        }
                    )
                
                # 如果有运行中的策略，返回交易信号（这里暂时返回空数据，实际应从数据库获取）
                signals: List[Dict[str, Any]] = []
                # TODO: 实现从数据库或缓存获取交易信号的逻辑
                # signals = self.trading_engine.get_trading_signals(...)
                
                return SystemResponse(
                    success=True,
                    message="交易信号获取成功",
                    data={
                        "signals": signals,
                        "running_strategies": [s.get('strategy_uuid') for s in running_strategies]
                    }
                )
            except Exception as e:
                logger.error(f"获取交易信号失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/trading/orders")
        async def get_trading_orders(
            strategy_uuid: Optional[str] = None,
            symbol: Optional[str] = None,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None
        ) -> Any:
            """获取交易订单 - 只有在策略运行时才返回数据"""
            try:
                # 检查是否有运行中的策略
                running_strategies = []
                if hasattr(self.trading_engine, 'strategy_manager'):
                    all_strategies = self.trading_engine.strategy_manager.get_all_strategies()
                    running_strategies = [s for s in all_strategies.values() if s.get('status') == 'running']
                
                # 如果没有运行中的策略，返回空数据
                if not running_strategies:
                    return SystemResponse(
                        success=True,
                        message="当前没有运行中的策略",
                        data={
                            "orders": [],
                            "running_strategies": []
                        }
                    )
                
                # 如果有运行中的策略，获取订单数据
                orders: List[Dict[str, Any]] = []
                if strategy_uuid and hasattr(self.trading_engine, 'order_manager'):
                    orders = self.trading_engine.order_manager.get_strategy_orders(strategy_uuid)
                
                return SystemResponse(
                    success=True,
                    message="交易订单获取成功",
                    data={
                        "orders": orders,
                        "running_strategies": [s.get('strategy_uuid') for s in running_strategies]
                    }
                )
            except Exception as e:
                logger.error(f"获取交易订单失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/trading/performance")
        async def get_trading_performance(
            strategy_uuid: Optional[str] = None,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None
        ) -> Any:
            """获取策略绩效 - 只有在策略运行时才返回数据"""
            try:
                # 检查是否有运行中的策略
                running_strategies = []
                if hasattr(self.trading_engine, 'strategy_manager'):
                    all_strategies = self.trading_engine.strategy_manager.get_all_strategies()
                    running_strategies = [s for s in all_strategies.values() if s.get('status') == 'running']
                
                # 如果没有运行中的策略，返回空数据
                if not running_strategies:
                    return SystemResponse(
                        success=True,
                        message="当前没有运行中的策略",
                        data={
                            "performance": {},
                            "running_strategies": []
                        }
                    )
                
                # 如果有运行中的策略，返回绩效数据（这里暂时返回空数据，实际应计算绩效）
                performance: Dict[str, Any] = {}
                # TODO: 实现策略绩效计算逻辑
                # performance = self.trading_engine.get_strategy_performance(...)
                
                return SystemResponse(
                    success=True,
                    message="策略绩效获取成功",
                    data={
                        "performance": performance,
                        "running_strategies": [s.get('strategy_uuid') for s in running_strategies]
                    }
                )
            except Exception as e:
                logger.error(f"获取策略绩效失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/market/kline")
        async def get_market_kline(
            symbol: str,
            interval: str = "1m",
            limit: int = 200
        ) -> Any:
            """获取K线数据"""
            try:
                # 生成模拟K线数据用于演示
                kline_data = self._generate_mock_kline_data(symbol, interval, limit)
                
                return SystemResponse(
                    success=True,
                    message="K线数据获取成功",
                    data={
                        "symbol": symbol,
                        "interval": interval,
                        "klines": kline_data
                    }
                )
            except Exception as e:
                logger.error(f"获取K线数据失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws/dashboard")
        async def dashboard_websocket(websocket: WebSocket) -> None:
            """事件监控仪表板WebSocket连接"""
            await websocket.accept()
            
            async def safe_send_json(data: Dict[str, Any]) -> bool:
                """安全发送JSON数据，检查连接状态"""
                try:
                    # 检查WebSocket连接状态
                    if websocket.client_state.name != 'CONNECTED':
                        return False
                    await websocket.send_json(data)
                    return True
                except (WebSocketDisconnect, RuntimeError, ConnectionClosedOK) as e:
                    logger.debug(f"WebSocket连接已断开，停止发送数据: {e}")
                    return False
                except Exception as e:
                    logger.error(f"发送WebSocket数据失败: {e}")
                    return False
            
            try:
                # 发送初始数据
                if self.event_monitor:
                    try:
                        stats = self.event_monitor.get_statistics()
                        serialized_data = self._serialize_dashboard_data(stats)
                        success = await safe_send_json({
                            "type": "stats",
                            "data": serialized_data
                        })
                        if not success:
                            return
                    except Exception as serialize_error:
                        import traceback
                        logger.error(f"序列化初始统计数据失败: {serialize_error}")
                        logger.error(f"完整堆栈跟踪:\n{traceback.format_exc()}")
                        success = await safe_send_json({
                            "type": "error",
                            "message": "获取统计数据失败"
                        })
                        if not success:
                            return
                
                # 保持连接并定期发送更新
                while True:
                    await asyncio.sleep(5)  # 每5秒更新一次
                    
                    # 检查连接状态
                    if websocket.client_state.name != 'CONNECTED':
                        logger.debug("WebSocket连接已断开，退出循环")
                        break
                    
                    if self.event_monitor:
                        try:
                            stats = self.event_monitor.get_statistics()
                            serialized_data = self._serialize_dashboard_data(stats)
                            success = await safe_send_json({
                                "type": "stats_update",
                                "data": serialized_data,
                                "timestamp": time.time()
                            })
                            if not success:
                                break
                        except Exception as serialize_error:
                            import traceback
                            logger.error(f"序列化更新统计数据失败: {serialize_error}")
                            logger.error(f"完整堆栈跟踪:\n{traceback.format_exc()}")
                            success = await safe_send_json({
                                "type": "error",
                                "message": "获取统计数据失败"
                            })
                            if not success:
                                break
                        
            except WebSocketDisconnect:
                logger.info("仪表板WebSocket连接断开")
            except Exception as e:
                import traceback
                logger.error(f"仪表板WebSocket错误: {e}")
                logger.error(f"完整堆栈跟踪:\n{traceback.format_exc()}")
    
    def _serialize_dashboard_data(self, data: Any) -> Any:
        """序列化仪表板数据"""
        try:
            # 处理None值
            if data is None:
                return None
            
            # 处理基本类型
            if isinstance(data, (str, int, float, bool)):
                return data
            
            # 处理datetime对象
            if isinstance(data, datetime):
                return data.isoformat()
            
            # 处理Event对象（使用__slots__）
            from src.core.event import Event
            if isinstance(data, Event):
                return {
                    'type': data.type,
                    'data': self._serialize_dashboard_data(data.data),
                    'source': data.source,
                    'trace_id': data.trace_id,
                    'timestamp': data.timestamp,
                    'priority': data.priority.name if hasattr(data.priority, 'name') else str(data.priority)
                }
            
            # 处理列表和元组
            if isinstance(data, (list, tuple)):
                return [self._serialize_dashboard_data(item) for item in data]
            
            # 处理字典
            if isinstance(data, dict):
                return {str(k): self._serialize_dashboard_data(v) for k, v in data.items()}
            
            # 处理其他有__dict__属性的对象
            if hasattr(data, '__dict__'):
                obj_dict = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
                return self._serialize_dashboard_data(obj_dict)
            
            # 处理有__slots__的对象
            if hasattr(data, '__slots__') and not isinstance(data, str):
                obj_dict = {}
                for slot in data.__slots__:
                    if hasattr(data, slot):
                        obj_dict[slot] = getattr(data, slot)
                return self._serialize_dashboard_data(obj_dict)
            
            # 处理枚举类型
            if hasattr(data, 'name') and hasattr(data, 'value'):
                return data.value
            
            # 其他情况转换为字符串
            return str(data)
            
        except Exception as e:
            logger.error(f"序列化仪表板数据失败: {e}, 数据类型: {type(data)}, 数据内容: {repr(data)}")
            return str(data)
    
    def _generate_mock_kline_data(self, symbol: str, interval: str, limit: int) -> list:
        """生成模拟K线数据用于演示"""
        import random
        from datetime import datetime, timedelta
        
        # 基础价格（根据不同品种设置不同的基础价格）
        base_prices = {
            'rb2501': 3500,  # 螺纹钢
            'hc2501': 3200,  # 热卷
            'i2501': 800,    # 铁矿石
            'j2501': 2000,   # 焦炭
            'jm2501': 1400,  # 焦煤
            'fg2501': 1200,  # 玻璃
            'fg509': 1361,   # 玻璃509合约（当前策略使用）
            'sa2501': 1800,  # 纯碱
        }
        
        base_price = base_prices.get(symbol.lower(), 3000)
        
        # 时间间隔映射（分钟）
        interval_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30, 
            '1h': 60, '4h': 240, '1d': 1440
        }
        
        minutes = interval_minutes.get(interval, 1)
        
        # 生成K线数据
        klines = []
        current_time = datetime.now()
        current_price = float(base_price)
        
        for i in range(limit):
            # 计算时间戳
            bar_time = current_time - timedelta(minutes=minutes * (limit - i - 1))
            timestamp = int(bar_time.timestamp() * 1000)  # 毫秒时间戳
            
            # 生成价格波动（模拟真实市场波动）
            price_change = random.uniform(-0.02, 0.02)  # ±2%的价格波动
            current_price = current_price * (1 + price_change)
            
            # 生成OHLC数据
            open_price = current_price
            high_price = open_price * (1 + random.uniform(0, 0.01))  # 最高价
            low_price = open_price * (1 - random.uniform(0, 0.01))   # 最低价
            close_price = open_price + random.uniform(-20, 20)       # 收盘价
            
            # 确保价格逻辑正确
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            # 生成成交量
            volume = random.randint(100, 1000)
            
            # K线数据格式：[timestamp, open, high, low, close, volume]
            kline = [
                timestamp,
                round(open_price, 2),
                round(high_price, 2),
                round(low_price, 2),
                round(close_price, 2),
                volume
            ]
            
            klines.append(kline)
            current_price = close_price
        
        return klines
    
    def _get_dashboard_html(self) -> str:
        """获取事件监控仪表板HTML页面"""
        # 返回静态文件路径，实现前后端分离
        static_path = Path(__file__).parent / "static" / "dashboard.html"
        
        try:
            with open(static_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"仪表板HTML文件未找到: {static_path}")
            return self._get_fallback_dashboard_html()
        except Exception as e:
            logger.error(f"读取仪表板HTML文件失败: {e}")
            return self._get_fallback_dashboard_html()
    
    def _get_chart_html(self) -> str:
        """获取交易图表HTML页面"""
        # 返回静态文件路径，实现前后端分离
        static_path = Path(__file__).parent / "static" / "chart.html"
        
        try:
            with open(static_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"图表HTML文件未找到: {static_path}")
            return self._get_fallback_chart_html()
        except Exception as e:
            logger.error(f"读取图表HTML文件失败: {e}")
            return self._get_fallback_chart_html()
    
    def _get_fallback_chart_html(self) -> str:
        """获取备用图表HTML页面"""
        fallback_path = Path(__file__).parent / "static" / "fallback_chart.html"
        
        try:
            with open(fallback_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"备用图表HTML文件未找到: {fallback_path}")
            # 如果备用文件也不存在，返回最简单的错误页面
            return self._get_minimal_error_html("图表页面加载失败", "无法加载图表页面，请检查静态文件是否存在。")
        except Exception as e:
            logger.error(f"读取备用图表HTML文件失败: {e}")
            return self._get_minimal_error_html("图表页面加载失败", "无法加载图表页面，请检查静态文件是否存在。")
    
    def _get_fallback_dashboard_html(self) -> str:
        """获取备用仪表板HTML页面"""
        fallback_path = Path(__file__).parent / "static" / "fallback_dashboard.html"
        
        try:
            with open(fallback_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"备用仪表板HTML文件未找到: {fallback_path}")
            # 如果备用文件也不存在，返回最简单的错误页面
            return self._get_minimal_error_html("仪表板加载失败", "无法加载仪表板页面，请检查静态文件是否存在。")
        except Exception as e:
            logger.error(f"读取备用仪表板HTML文件失败: {e}")
            return self._get_minimal_error_html("仪表板加载失败", "无法加载仪表板页面，请检查静态文件是否存在。")
    
    def _get_minimal_error_html(self, title: str, message: str) -> str:
        """获取最简单的错误页面HTML（最后的备用方案）"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Homalos量化交易系统</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            text-align: center; 
            padding: 2rem; 
            background: #f8f9fa;
            margin: 0;
        }}
        .error {{ 
            color: #e74c3c; 
            background: #fdf2f2; 
            padding: 2rem; 
            border-radius: 8px; 
            border: 1px solid #f5c6cb;
            max-width: 500px;
            margin: 2rem auto;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .error h2 {{
            margin-top: 0;
            color: #721c24;
        }}
        .error a {{
            color: #409EFF;
            text-decoration: none;
            font-weight: 500;
        }}
        .error a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="error">
        <h2>{title}</h2>
        <p>{message}</p>
        <a href="/">返回主页</a>
    </div>
</body>
</html>
        """


async def main() -> None:
    """主函数"""
    from src.config.config_manager import ConfigManager
    from src.core.event_bus import BasicEventBus as EventBus
    from src.core.event_monitor import EventMonitor, EventMonitorIntegration
    from src.trade.trading_engine import TradingEngine
    
    try:
        # 初始化组件 - 使用基础事件总线
        config = ConfigManager("config/system.yaml")
        
        # 创建基础事件总线（构造函数内已启动）
        from src.core.event_bus import BasicEventBus
        event_bus = BasicEventBus(name="IntegratedWebServer")
        
        event_monitor = EventMonitor(name="IntegratedWebServer")
        
        # 将事件监控器与事件总线集成
        monitor_integration = EventMonitorIntegration(event_bus, event_monitor)
        
        # 在异步环境中初始化交易引擎
        trading_engine = TradingEngine(event_bus, config)
        
        # 创建并启动集成Web服务器
        web_server = IntegratedWebServer(trading_engine, event_bus, config, event_monitor)
        await web_server.start()
        
    except Exception as e:
        logger.error(f"启动集成Web服务器失败: {e}")
        raise


if __name__ == "__main__":
    # 测试集成Web服务器
    asyncio.run(main())