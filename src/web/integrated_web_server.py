#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成Web服务器
将事件监控仪表板集成到主Web服务中

作者: Homalos Team
创建时间: 2024-01-20
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from src.core.event_monitor import EventMonitor
from src.web.web_server import WebServer

logger = logging.getLogger(__name__)


class IntegratedWebServer(WebServer):
    """
    集成Web服务器
    
    继承原有Web服务器功能，并集成事件监控仪表板
    """
    
    def __init__(self, trading_engine, event_bus, config, event_monitor: Optional[EventMonitor] = None):
        super().__init__(trading_engine, event_bus, config)
        self.event_monitor = event_monitor
        
        # 添加事件监控相关路由
        self._setup_dashboard_routes()
    
    def _setup_dashboard_routes(self):
        """设置事件监控仪表板路由"""
        
        @self.app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard():
            """事件监控仪表板页面"""
            return self._get_dashboard_html()
        
        @self.app.get("/api/dashboard/stats")
        async def dashboard_stats():
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
        async def dashboard_timeseries(minutes: int = 60):
            """获取时间序列数据"""
            if not self.event_monitor:
                raise HTTPException(status_code=503, detail="事件监控器未启用")
            
            try:
                timeseries = self.event_monitor.get_timeseries_data(minutes)
                return self._serialize_dashboard_data(timeseries)
            except Exception as e:
                logger.error(f"获取时间序列数据失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/dashboard/alerts")
        async def dashboard_alerts(limit: int = 50):
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
        async def test_publish_event(event_type: str, data: dict = None):
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
        async def test_publish_batch_events(request: Request):
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
                
                test_events = [
                    ("test.success", {"message": "成功测试事件", "value": 100}),
                    ("test.warning", {"message": "警告测试事件", "level": "warning"}),
                    ("test.error", {"message": "错误测试事件", "error_code": 500}),
                    ("strategy.update", {"strategy_id": "test_strategy", "status": "running"}),
                    ("trading.order", {"order_id": "test_order_001", "symbol": "BTCUSDT", "side": "buy"}),
                    ("market.tick", {"symbol": "BTCUSDT", "price": 45000.0, "volume": 1.5}),
                    ("risk.alert", {"message": "风险警告", "level": "high"}),
                    ("system.info", {"message": "系统信息", "component": "web_server"})
                ]
                
                published_events = []
                for i in range(count):
                    event_type, event_data = test_events[i % len(test_events)]
                    # 为每个事件添加唯一标识
                    event_data_copy = event_data.copy()
                    event_data_copy['batch_id'] = i + 1
                    event_data_copy['timestamp'] = time.time()
                    
                    # 直接发布事件（EnhancedEventBus接受event_type和data）
                    try:
                        event_id = self.event_bus.publish(event_type, event_data_copy)
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
        
        @self.app.websocket("/ws/dashboard")
        async def dashboard_websocket(websocket: WebSocket):
            """事件监控仪表板WebSocket连接"""
            await websocket.accept()
            
            try:
                # 发送初始数据
                if self.event_monitor:
                    try:
                        stats = self.event_monitor.get_statistics()
                        serialized_data = self._serialize_dashboard_data(stats)
                        await websocket.send_json({
                            "type": "stats",
                            "data": serialized_data
                        })
                    except Exception as serialize_error:
                        import traceback
                        logger.error(f"序列化初始统计数据失败: {serialize_error}")
                        logger.error(f"完整堆栈跟踪:\n{traceback.format_exc()}")
                        await websocket.send_json({
                            "type": "error",
                            "message": "获取统计数据失败"
                        })
                
                # 保持连接并定期发送更新
                while True:
                    await asyncio.sleep(5)  # 每5秒更新一次
                    
                    if self.event_monitor:
                        try:
                            stats = self.event_monitor.get_statistics()
                            serialized_data = self._serialize_dashboard_data(stats)
                            await websocket.send_json({
                                "type": "stats_update",
                                "data": serialized_data,
                                "timestamp": time.time()
                            })
                        except Exception as serialize_error:
                            import traceback
                            logger.error(f"序列化更新统计数据失败: {serialize_error}")
                            logger.error(f"完整堆栈跟踪:\n{traceback.format_exc()}")
                            await websocket.send_json({
                                "type": "error",
                                "message": "获取统计数据失败"
                            })
                        
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
    
    def _get_fallback_dashboard_html(self) -> str:
        """获取备用仪表板HTML页面"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Homalos 事件监控仪表板</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 2rem; }
        .error { color: #e74c3c; background: #fdf2f2; padding: 1rem; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="error">
        <h2>仪表板加载失败</h2>
        <p>无法加载仪表板页面，请检查静态文件是否存在。</p>
        <a href="/">返回主页</a>
    </div>
</body>
</html>
        """


async def main():
    """主函数"""
    from src.config.config_manager import ConfigManager
    from src.core.enhanced_event_bus import EnhancedEventBus, EventBusConfig
    from src.core.event_monitor import EventMonitor, EventMonitorIntegration
    from src.trade.trading_engine import TradingEngine
    
    try:
        # 初始化组件 - 使用增强版事件总线以获得更好的监控效果
        config = ConfigManager("config/system.yaml")
        
        # 创建增强版事件总线配置
        bus_config = EventBusConfig(
            name="IntegratedWebServer",
            enable_metrics=True,
            enable_detailed_logging=True,
            enable_health_monitoring=True
        )
        
        # 创建并启动增强版事件总线
        event_bus = EnhancedEventBus(bus_config)
        event_bus.start()
        
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