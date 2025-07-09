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
    
    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
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
            return self._get_home_html()
        
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
                    return SystemResponse(
                        success=True,
                        message=f"策略 {request.strategy_id} 加载成功"
                    )
                else:
                    raise HTTPException(status_code=400, detail="策略加载失败")
                    
            except Exception as e:
                logger.error(f"加载策略失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/v1/strategies/{strategy_id}/start")
        async def start_strategy(strategy_id: str):
            """启动策略"""
            try:
                success = await self.trading_engine.strategy_manager.start_strategy(strategy_id)
                
                if success:
                    return SystemResponse(
                        success=True,
                        message=f"策略 {strategy_id} 启动成功"
                    )
                else:
                    raise HTTPException(status_code=400, detail="策略启动失败")
                    
            except Exception as e:
                logger.error(f"启动策略失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/v1/strategies/{strategy_id}/stop")
        async def stop_strategy(strategy_id: str):
            """停止策略"""
            try:
                success = await self.trading_engine.strategy_manager.stop_strategy(strategy_id)
                
                if success:
                    return SystemResponse(
                        success=True,
                        message=f"策略 {strategy_id} 停止成功"
                    )
                else:
                    raise HTTPException(status_code=400, detail="策略停止失败")
                    
            except Exception as e:
                logger.error(f"停止策略失败: {e}")
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
                # 过滤需要推送的事件
                push_events = [
                    "strategy.signal", "order.submitted", "order.filled", 
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
    
    def _get_home_html(self) -> str:
        """获取主页HTML"""
        return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Homalos量化交易系统</title>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://unpkg.com/element-plus/dist/index.full.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/element-plus/dist/index.css">
    <style>
        body { margin: 0; font-family: 'Helvetica Neue', Arial, sans-serif; }
        .header { background: #409EFF; color: white; padding: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .container { padding: 1rem; max-width: 1200px; margin: 0 auto; }
        .stats-card { margin-bottom: 1rem; }
        .real-time-log { height: 300px; overflow-y: auto; background: #f5f5f5; padding: 1rem; border-radius: 4px; }
        .log-item { margin-bottom: 0.5rem; font-size: 0.9rem; }
        .log-time { color: #999; }
        .log-type { font-weight: bold; margin: 0 0.5rem; }
        .log-message { color: #333; }
        .strategy-table { margin-top: 1rem; }
    </style>
</head>
<body>
    <div id="app">
        <div class="header">
            <h1>🚀 Homalos量化交易系统</h1>
            <p>基于Python的期货量化交易系统 v2.0</p>
        </div>
        
        <div class="container">
            <!-- 系统状态卡片 -->
            <el-row :gutter="20" class="stats-card">
                <el-col :span="6">
                    <el-card>
                        <div slot="header">系统状态</div>
                        <div>
                            <el-tag :type="systemStatus.is_running ? 'success' : 'danger'">
                                {{ systemStatus.is_running ? '运行中' : '已停止' }}
                            </el-tag>
                        </div>
                    </el-card>
                </el-col>
                <el-col :span="6">
                    <el-card>
                        <div slot="header">策略数量</div>
                        <div style="font-size: 2rem; color: #409EFF;">{{ Object.keys(strategies).length }}</div>
                    </el-card>
                </el-col>
                <el-col :span="6">
                    <el-card>
                        <div slot="header">账户余额</div>
                        <div style="font-size: 1.5rem; color: #67C23A;">¥{{ accountInfo.total_balance?.toFixed(2) || '0.00' }}</div>
                    </el-card>
                </el-col>
                <el-col :span="6">
                    <el-card>
                        <div slot="header">连接状态</div>
                        <div>
                            <el-tag :type="wsConnected ? 'success' : 'danger'">
                                {{ wsConnected ? '已连接' : '断开' }}
                            </el-tag>
                        </div>
                    </el-card>
                </el-col>
            </el-row>
            
            <!-- 策略管理 -->
            <el-card class="strategy-table">
                <div slot="header">
                    <span>策略管理</span>
                    <el-button style="float: right;" @click="loadStrategy" type="primary" size="small">加载策略</el-button>
                </div>
                
                <el-table :data="strategyList" style="width: 100%">
                    <el-table-column prop="strategy_id" label="策略ID" width="200"></el-table-column>
                    <el-table-column prop="strategy_name" label="策略名称" width="200"></el-table-column>
                    <el-table-column prop="status" label="状态" width="120">
                        <template #default="scope">
                            <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="start_time" label="启动时间" width="180">
                        <template #default="scope">
                            {{ scope.row.start_time ? new Date(scope.row.start_time * 1000).toLocaleString() : '-' }}
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" width="200">
                        <template #default="scope">
                            <el-button 
                                @click="startStrategy(scope.row.strategy_id)"
                                :disabled="scope.row.status === 'running'"
                                type="success" 
                                size="small">
                                启动
                            </el-button>
                            <el-button 
                                @click="stopStrategy(scope.row.strategy_id)"
                                :disabled="scope.row.status !== 'running'"
                                type="danger" 
                                size="small">
                                停止
                            </el-button>
                        </template>
                    </el-table-column>
                </el-table>
            </el-card>
            
            <!-- 实时日志 -->
            <el-card style="margin-top: 1rem;">
                <div slot="header">
                    <span>实时日志</span>
                    <el-button style="float: right;" @click="clearLogs" size="small">清空</el-button>
                </div>
                
                <div class="real-time-log">
                    <div v-for="log in realtimeLogs" :key="log.id" class="log-item">
                        <span class="log-time">{{ log.timestamp }}</span>
                        <span class="log-type" :style="{color: getLogColor(log.type)}">{{ log.type }}</span>
                        <span class="log-message">{{ log.message }}</span>
                    </div>
                </div>
            </el-card>
        </div>
    </div>

    <script>
        const { createApp } = Vue;
        
        createApp({
            data() {
                return {
                    systemStatus: { is_running: false },
                    strategies: {},
                    accountInfo: {},
                    realtimeLogs: [],
                    wsConnected: false,
                    ws: null
                }
            },
            computed: {
                strategyList() {
                    return Object.values(this.strategies);
                }
            },
            mounted() {
                this.initData();
                this.connectWebSocket();
                
                // 定时刷新数据
                setInterval(() => {
                    this.loadSystemStatus();
                    this.loadStrategies();
                    this.loadAccountInfo();
                }, 5000);
            },
            methods: {
                async initData() {
                    await this.loadSystemStatus();
                    await this.loadStrategies();
                    await this.loadAccountInfo();
                },
                
                async loadSystemStatus() {
                    try {
                        const response = await fetch('/api/v1/system/status');
                        const result = await response.json();
                        if (result.success) {
                            this.systemStatus = result.data;
                        }
                    } catch (error) {
                        console.error('加载系统状态失败:', error);
                    }
                },
                
                async loadStrategies() {
                    try {
                        const response = await fetch('/api/v1/strategies');
                        const result = await response.json();
                        if (result.success) {
                            this.strategies = result.data.strategies;
                        }
                    } catch (error) {
                        console.error('加载策略列表失败:', error);
                    }
                },
                
                async loadAccountInfo() {
                    try {
                        const response = await fetch('/api/v1/account');
                        const result = await response.json();
                        if (result.success) {
                            this.accountInfo = result.data;
                        }
                    } catch (error) {
                        console.error('加载账户信息失败:', error);
                    }
                },
                
                async startStrategy(strategyId) {
                    try {
                        const response = await fetch(`/api/v1/strategies/${strategyId}/start`, {
                            method: 'POST'
                        });
                        const result = await response.json();
                        
                        if (result.success) {
                            this.$message.success(result.message);
                            await this.loadStrategies();
                        } else {
                            this.$message.error(result.message);
                        }
                    } catch (error) {
                        this.$message.error('启动策略失败');
                        console.error('启动策略失败:', error);
                    }
                },
                
                async stopStrategy(strategyId) {
                    try {
                        const response = await fetch(`/api/v1/strategies/${strategyId}/stop`, {
                            method: 'POST'
                        });
                        const result = await response.json();
                        
                        if (result.success) {
                            this.$message.success(result.message);
                            await this.loadStrategies();
                        } else {
                            this.$message.error(result.message);
                        }
                    } catch (error) {
                        this.$message.error('停止策略失败');
                        console.error('停止策略失败:', error);
                    }
                },
                
                loadStrategy() {
                    this.$prompt('请输入策略文件路径', '加载策略', {
                        confirmButtonText: '确定',
                        cancelButtonText: '取消'
                    }).then(({ value }) => {
                        // 这里可以实现策略加载逻辑
                        this.$message.info('策略加载功能需要进一步完善');
                    });
                },
                
                connectWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/ws/realtime`;
                    
                    this.ws = new WebSocket(wsUrl);
                    
                    this.ws.onopen = () => {
                        this.wsConnected = true;
                        this.addLog('info', 'WebSocket连接成功');
                        
                        // 发送心跳
                        setInterval(() => {
                            if (this.ws?.readyState === WebSocket.OPEN) {
                                this.ws.send(JSON.stringify({ type: 'ping' }));
                            }
                        }, 30000);
                    };
                    
                    this.ws.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            this.handleWebSocketMessage(data);
                        } catch (error) {
                            console.error('WebSocket消息解析失败:', error);
                        }
                    };
                    
                    this.ws.onclose = () => {
                        this.wsConnected = false;
                        this.addLog('warning', 'WebSocket连接断开');
                        
                        // 重连
                        setTimeout(() => {
                            this.connectWebSocket();
                        }, 5000);
                    };
                    
                    this.ws.onerror = (error) => {
                        this.addLog('error', 'WebSocket连接错误');
                        console.error('WebSocket错误:', error);
                    };
                },
                
                handleWebSocketMessage(data) {
                    if (data.type === 'event') {
                        this.addLog(data.event_type, JSON.stringify(data.data));
                    } else if (data.type === 'pong') {
                        // 心跳响应
                    }
                },
                
                addLog(type, message) {
                    const log = {
                        id: Date.now() + Math.random(),
                        timestamp: new Date().toLocaleTimeString(),
                        type: type,
                        message: message
                    };
                    
                    this.realtimeLogs.unshift(log);
                    
                    // 限制日志数量
                    if (this.realtimeLogs.length > 100) {
                        this.realtimeLogs = this.realtimeLogs.slice(0, 100);
                    }
                },
                
                clearLogs() {
                    this.realtimeLogs = [];
                },
                
                getStatusType(status) {
                    const types = {
                        'running': 'success',
                        'stopped': 'info',
                        'error': 'danger',
                        'loading': 'warning',
                        'loaded': 'info'
                    };
                    return types[status] || 'info';
                },
                
                getLogColor(type) {
                    const colors = {
                        'error': '#F56C6C',
                        'warning': '#E6A23C',
                        'success': '#67C23A',
                        'info': '#409EFF'
                    };
                    return colors[type] || '#909399';
                }
            }
        }).use(ElementPlus).mount('#app');
    </script>
</body>
</html>
        '''
    
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