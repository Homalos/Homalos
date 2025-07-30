#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : event_dashboard
@Date       : 2025/1/16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件监控可视化仪表板 - 第一阶段基础Web界面
"""
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from src.core.event_monitor import EventMonitor
from src.core.logger import get_logger

logger = get_logger("EventDashboard")


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def __init__(self, monitor: EventMonitor, *args, **kwargs):
        self.monitor = monitor
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            query_params = parse_qs(parsed_path.query)
            
            if path == '/' or path == '/dashboard':
                self._serve_dashboard()
            elif path == '/api/stats':
                self._serve_stats_api()
            elif path == '/api/dashboard':
                self._serve_dashboard_api()
            elif path == '/api/timeseries':
                self._serve_timeseries_api(query_params)
            elif path == '/api/alerts':
                self._serve_alerts_api()
            elif path.startswith('/static/'):
                self._serve_static_file(path)
            else:
                self._send_404()
                
        except Exception as e:
            logger.error(f"Request handling error: {e}", exc_info=True)
            self._send_500(str(e))
    
    def _serve_dashboard(self):
        """提供仪表板HTML页面"""
        html_content = self._get_dashboard_html()
        self._send_response(200, html_content, 'text/html')
    
    def _serve_stats_api(self):
        """提供统计数据API"""
        stats = self.monitor.get_event_stats()
        self._send_json_response(stats)
    
    def _serve_dashboard_api(self):
        """提供仪表板数据API"""
        dashboard_data = self.monitor.get_dashboard_data()
        self._send_json_response(dashboard_data)
    
    def _serve_timeseries_api(self, query_params):
        """提供时间序列数据API"""
        metric = query_params.get('metric', ['throughput'])[0]
        duration = int(query_params.get('duration', ['5'])[0])
        
        data = self.monitor.get_time_series_data(metric, duration)
        self._send_json_response({
            'metric': metric,
            'duration_minutes': duration,
            'data': data
        })
    
    def _serve_alerts_api(self):
        """提供告警数据API"""
        alerts = self.monitor.get_recent_alerts()
        self._send_json_response(alerts)
    
    def _serve_static_file(self, path):
        """提供静态文件（暂时返回404）"""
        self._send_404()
    
    def _send_response(self, status_code, content, content_type='text/plain'):
        """发送HTTP响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def _send_json_response(self, data):
        """发送JSON响应"""
        json_content = json.dumps(data, ensure_ascii=False, indent=2)
        self._send_response(200, json_content, 'application/json')
    
    def _send_404(self):
        """发送404响应"""
        self._send_response(404, 'Not Found')
    
    def _send_500(self, error_message):
        """发送500响应"""
        self._send_response(500, f'Internal Server Error: {error_message}')
    
    def log_message(self, format, *args):
        """重写日志方法以使用我们的logger"""
        logger.debug(f"HTTP: {format % args}")
    
    def _get_dashboard_html(self) -> str:
        """生成仪表板HTML页面"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Homalos 事件监控仪表板</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.8rem;
            font-weight: 300;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .card:hover {
            transform: translateY(-2px);
        }
        
        .card-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2c3e50;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 0.5rem;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.8rem;
            padding: 0.5rem;
            background: #f8f9fa;
            border-radius: 4px;
        }
        
        .metric-label {
            font-weight: 500;
            color: #555;
        }
        
        .metric-value {
            font-weight: 700;
            font-size: 1.1rem;
        }
        
        .metric-value.success {
            color: #27ae60;
        }
        
        .metric-value.warning {
            color: #f39c12;
        }
        
        .metric-value.error {
            color: #e74c3c;
        }
        
        .chart-container {
            height: 300px;
            margin-top: 1rem;
            background: #f8f9fa;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-style: italic;
        }
        
        .alert-item {
            padding: 0.8rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
            border-left: 4px solid;
        }
        
        .alert-item.info {
            background: #e8f4fd;
            border-color: #3498db;
        }
        
        .alert-item.warning {
            background: #fef9e7;
            border-color: #f39c12;
        }
        
        .alert-item.error {
            background: #fdf2f2;
            border-color: #e74c3c;
        }
        
        .alert-item.critical {
            background: #f8d7da;
            border-color: #dc3545;
        }
        
        .alert-time {
            font-size: 0.8rem;
            color: #666;
            margin-top: 0.3rem;
        }
        
        .refresh-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 0.8rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s ease;
            margin-bottom: 1rem;
        }
        
        .refresh-btn:hover {
            background: #2980b9;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }
        
        .status-indicator.online {
            background: #27ae60;
            animation: pulse 2s infinite;
        }
        
        .status-indicator.offline {
            background: #e74c3c;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .loading {
            text-align: center;
            color: #666;
            font-style: italic;
        }
        
        .error-message {
            background: #fdf2f2;
            color: #e74c3c;
            padding: 1rem;
            border-radius: 4px;
            margin: 1rem 0;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            <span class="status-indicator online"></span>
            Homalos 事件监控仪表板
        </h1>
    </div>
    
    <div class="container">
        <button class="refresh-btn" onclick="refreshDashboard()">🔄 刷新数据</button>
        
        <div class="dashboard-grid">
            <!-- 系统概览 -->
            <div class="card">
                <div class="card-title">📊 系统概览</div>
                <div id="system-overview" class="loading">加载中...</div>
            </div>
            
            <!-- 性能指标 -->
            <div class="card">
                <div class="card-title">⚡ 性能指标</div>
                <div id="performance-metrics" class="loading">加载中...</div>
            </div>
            
            <!-- 事件类型分布 -->
            <div class="card">
                <div class="card-title">📈 事件类型分布</div>
                <div id="event-distribution" class="loading">加载中...</div>
            </div>
            
            <!-- 最近告警 -->
            <div class="card">
                <div class="card-title">🚨 最近告警</div>
                <div id="recent-alerts" class="loading">加载中...</div>
            </div>
        </div>
        
        <!-- 时间序列图表 -->
        <div class="card">
            <div class="card-title">📉 实时监控图表</div>
            <div class="chart-container">
                图表功能需要集成 Chart.js 或其他图表库<br>
                当前显示最近5分钟的吞吐量数据
            </div>
        </div>
    </div>
    
    <script>
        let refreshInterval;
        
        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            refreshDashboard();
            // 每30秒自动刷新
            refreshInterval = setInterval(refreshDashboard, 30000);
        });
        
        // 刷新仪表板数据
        async function refreshDashboard() {
            try {
                const response = await fetch('/api/dashboard');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                updateDashboard(data);
                
            } catch (error) {
                console.error('Failed to refresh dashboard:', error);
                showError('无法获取监控数据: ' + error.message);
            }
        }
        
        // 更新仪表板显示
        function updateDashboard(data) {
            updateSystemOverview(data.summary);
            updatePerformanceMetrics(data.summary);
            updateEventDistribution(data.event_type_distribution);
            updateRecentAlerts(data.recent_alerts);
        }
        
        // 更新系统概览
        function updateSystemOverview(summary) {
            const container = document.getElementById('system-overview');
            const errorRateClass = summary.overall_error_rate > 0.05 ? 'error' : 
                                  summary.overall_error_rate > 0.01 ? 'warning' : 'success';
            
            container.innerHTML = `
                <div class="metric">
                    <span class="metric-label">总事件数</span>
                    <span class="metric-value">${summary.total_events.toLocaleString()}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">总错误数</span>
                    <span class="metric-value ${summary.total_errors > 0 ? 'error' : 'success'}">${summary.total_errors.toLocaleString()}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">整体错误率</span>
                    <span class="metric-value ${errorRateClass}">${(summary.overall_error_rate * 100).toFixed(2)}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">吞吐量</span>
                    <span class="metric-value">${summary.throughput_per_min.toFixed(1)} 事件/分钟</span>
                </div>
            `;
        }
        
        // 更新性能指标
        function updatePerformanceMetrics(summary) {
            const container = document.getElementById('performance-metrics');
            const processingTimeClass = summary.recent_avg_processing_time_ms > 100 ? 'error' :
                                       summary.recent_avg_processing_time_ms > 50 ? 'warning' : 'success';
            const queueTimeClass = summary.recent_avg_queue_wait_time_ms > 50 ? 'error' :
                                  summary.recent_avg_queue_wait_time_ms > 20 ? 'warning' : 'success';
            
            container.innerHTML = `
                <div class="metric">
                    <span class="metric-label">最近5分钟事件数</span>
                    <span class="metric-value">${summary.recent_events_5min.toLocaleString()}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">平均处理时间</span>
                    <span class="metric-value ${processingTimeClass}">${summary.recent_avg_processing_time_ms.toFixed(2)} ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">平均队列等待时间</span>
                    <span class="metric-value ${queueTimeClass}">${summary.recent_avg_queue_wait_time_ms.toFixed(2)} ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">最近错误率</span>
                    <span class="metric-value ${summary.recent_error_rate_5min > 0.05 ? 'error' : 'success'}">${(summary.recent_error_rate_5min * 100).toFixed(2)}%</span>
                </div>
            `;
        }
        
        // 更新事件类型分布
        function updateEventDistribution(distribution) {
            const container = document.getElementById('event-distribution');
            
            if (Object.keys(distribution).length === 0) {
                container.innerHTML = '<div class="loading">暂无事件数据</div>';
                return;
            }
            
            // 按事件数量排序，只显示前5个
            const sortedEvents = Object.entries(distribution)
                .sort((a, b) => b[1].count - a[1].count)
                .slice(0, 5);
            
            const html = sortedEvents.map(([eventType, data]) => `
                <div class="metric">
                    <span class="metric-label">${eventType}</span>
                    <span class="metric-value">${data.count} (${data.percentage.toFixed(1)}%)</span>
                </div>
            `).join('');
            
            container.innerHTML = html;
        }
        
        // 更新最近告警
        function updateRecentAlerts(alerts) {
            const container = document.getElementById('recent-alerts');
            
            if (alerts.length === 0) {
                container.innerHTML = '<div class="loading">暂无告警</div>';
                return;
            }
            
            const html = alerts.map(alert => {
                const time = new Date(alert.timestamp * 1000).toLocaleString('zh-CN');
                return `
                    <div class="alert-item ${alert.level}">
                        <div>${alert.message}</div>
                        <div class="alert-time">${time}</div>
                    </div>
                `;
            }).join('');
            
            container.innerHTML = html;
        }
        
        // 显示错误信息
        function showError(message) {
            const containers = ['system-overview', 'performance-metrics', 'event-distribution', 'recent-alerts'];
            containers.forEach(id => {
                const container = document.getElementById(id);
                container.innerHTML = `<div class="error-message">${message}</div>`;
            });
        }
        
        // 页面卸载时清理定时器
        window.addEventListener('beforeunload', function() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        });
    </script>
</body>
</html>
        """


class EventDashboard:
    """
    事件监控仪表板服务器
    
    提供Web界面来展示事件监控数据
    """
    
    def __init__(self, monitor: EventMonitor, host: str = 'localhost', port: int = 8080):
        self.monitor = monitor
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self) -> None:
        """启动仪表板服务器"""
        if self._running:
            logger.warning("Dashboard server is already running")
            return
        
        try:
            # 创建处理器工厂函数
            def handler_factory(*args, **kwargs):
                return DashboardHandler(self.monitor, *args, **kwargs)
            
            # 创建HTTP服务器
            self.server = HTTPServer((self.host, self.port), handler_factory)
            
            # 在单独线程中运行服务器
            self.server_thread = threading.Thread(
                target=self._run_server,
                name="EventDashboard-Server",
                daemon=True
            )
            
            self._running = True
            self.server_thread.start()
            
            logger.info(f"Event dashboard started at http://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start dashboard server: {e}", exc_info=True)
            self._running = False
            raise
    
    def stop(self) -> None:
        """停止仪表板服务器"""
        if not self._running:
            return
        
        self._running = False
        
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5.0)
        
        logger.info("Event dashboard stopped")
    
    def _run_server(self) -> None:
        """运行HTTP服务器"""
        try:
            self.server.serve_forever()
        except Exception as e:
            if self._running:  # 只有在非正常停止时才记录错误
                logger.error(f"Dashboard server error: {e}", exc_info=True)
    
    @property
    def url(self) -> str:
        """获取仪表板URL"""
        return f"http://{self.host}:{self.port}"
    
    @property
    def is_running(self) -> bool:
        """检查服务器是否运行中"""
        return self._running and self.server_thread and self.server_thread.is_alive()
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


if __name__ == '__main__':
    from src.core.event_monitor import EventMonitor
    from src.core.event import Event, EventType, EventPriority
    
    print("=" * 50)
    print("启动事件监控仪表板测试...")
    
    # 创建监控器
    monitor = EventMonitor(name="DashboardTest")
    
    # 创建仪表板
    dashboard = EventDashboard(monitor, host='localhost', port=8080)
    
    try:
        # 启动仪表板
        dashboard.start()
        print(f"\n🌐 仪表板已启动: {dashboard.url}")
        print("请在浏览器中打开上述地址查看监控界面")
        
        # 模拟一些事件数据
        print("\n正在生成模拟事件数据...")
        
        import random
        
        def generate_test_events():
            """生成测试事件"""
            event_types = [EventType.MARKET_TICK, EventType.ORDER, EventType.TRADE, 
                          EventType.STRATEGY_SIGNAL, EventType.RISK_CHECK]
            
            while dashboard.is_running:
                try:
                    # 随机选择事件类型
                    event_type = random.choice(event_types)
                    priority = random.choice(list(EventPriority))
                    
                    event = Event(event_type, priority=priority)
                    
                    # 模拟处理时间和成功率
                    processing_time = random.randint(1_000_000, 50_000_000)  # 1-50ms
                    queue_wait_time = random.randint(100_000, 10_000_000)    # 0.1-10ms
                    success = random.random() > 0.05  # 95%成功率
                    
                    monitor.record_event(
                        event=event,
                        processing_time_ns=processing_time,
                        queue_wait_time_ns=queue_wait_time,
                        success=success,
                        error_message="模拟错误" if not success else None
                    )
                    
                    time.sleep(random.uniform(0.1, 2.0))  # 随机间隔
                    
                except Exception as e:
                    logger.error(f"Test event generation error: {e}")
                    time.sleep(1.0)
        
        # 在后台生成测试事件
        test_thread = threading.Thread(target=generate_test_events, daemon=True)
        test_thread.start()
        
        print("\n按 Ctrl+C 停止服务器...")
        
        # 保持主线程运行
        while dashboard.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止服务器...")
    except Exception as e:
        logger.error(f"Dashboard test error: {e}", exc_info=True)
    finally:
        dashboard.stop()
        monitor.stop_monitoring()
        print("\n测试完成！")