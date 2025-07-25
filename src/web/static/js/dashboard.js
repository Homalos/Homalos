/**
 * 事件监控仪表板应用
 * 负责仪表板页面的Vue应用逻辑
 */

const { createApp, ref, onMounted, onUnmounted } = Vue;
const { ElMessage } = ElementPlus;

// 仪表板Vue应用
const DashboardApp = {
    template: `
        <div class="header">
            <div class="header-content">
                <div class="header-title">
                    <h1>
                        <span :class="statusIndicatorClass" id="status-indicator"></span>
                        Homalos 集成监控中心
                    </h1>
                    <p>实时事件监控与性能分析</p>
                </div>
                <div class="nav-links">
                    <a href="/" class="nav-link">
                        <i class="el-icon-house"></i>
                        主页
                    </a>
                    <a href="/dashboard" class="nav-link active">
                        <i class="el-icon-data-analysis"></i>
                        事件监控
                    </a>
                    <a href="/api/docs" class="nav-link">
                        <i class="el-icon-document"></i>
                        API文档
                    </a>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="dashboard-grid">
                <!-- 系统概览 -->
                <div class="card">
                    <h3>系统概览</h3>
                    <div v-if="loading.overview" class="loading">正在加载...</div>
                    <div v-else-if="error.overview" class="error-message">{{ error.overview }}</div>
                    <div v-else v-html="systemOverviewHtml"></div>
                </div>
                
                <!-- 性能指标 -->
                <div class="card">
                    <h3>性能指标</h3>
                    <div v-if="loading.performance" class="loading">正在加载...</div>
                    <div v-else-if="error.performance" class="error-message">{{ error.performance }}</div>
                    <div v-else v-html="performanceMetricsHtml"></div>
                </div>
                
                <!-- 事件类型分布 -->
                <div class="card">
                    <h3>事件类型分布</h3>
                    <div v-if="loading.distribution" class="loading">正在加载...</div>
                    <div v-else-if="error.distribution" class="error-message">{{ error.distribution }}</div>
                    <div v-else v-html="eventDistributionHtml"></div>
                </div>
                
                <!-- 最近告警 -->
                <div class="card">
                    <h3>最近告警</h3>
                    <div v-if="loading.alerts" class="loading">正在加载...</div>
                    <div v-else-if="error.alerts" class="error-message">{{ error.alerts }}</div>
                    <div v-else v-html="recentAlertsHtml"></div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 2rem;">
                <button class="refresh-btn" @click="refreshDashboard" :disabled="isRefreshing">
                    {{ isRefreshing ? '刷新中...' : '刷新数据' }}
                </button>
            </div>
        </div>
        
        <!-- 版权声明 -->
        <footer class="footer">
            <div class="footer-content">
                <p class="copyright">© 2025 Homalos量化交易系统 版权所有</p>
            </div>
        </footer>
    `,
    
    setup() {
        // 响应式数据
        const isOnline = ref(false);
        const isRefreshing = ref(false);
        const loading = ref({
            overview: true,
            performance: true,
            distribution: true,
            alerts: true
        });
        const error = ref({
            overview: null,
            performance: null,
            distribution: null,
            alerts: null
        });
        
        const systemOverviewHtml = ref('');
        const performanceMetricsHtml = ref('');
        const eventDistributionHtml = ref('');
        const recentAlertsHtml = ref('');
        
        let refreshInterval = null;
        let websocket = null;
        
        // 计算属性
        const statusIndicatorClass = Vue.computed(() => {
            return `status-indicator ${isOnline.value ? 'status-online' : 'status-offline'}`;
        });
        
        // WebSocket连接管理
        const initWebSocket = () => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
            
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = () => {
                console.log('WebSocket连接已建立');
                isOnline.value = true;
            };
            
            websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                if (message.type === 'stats' || message.type === 'stats_update') {
                    updateDashboard(message.data);
                }
            };
            
            websocket.onclose = () => {
                console.log('WebSocket连接已关闭');
                isOnline.value = false;
                
                // 尝试重连
                setTimeout(initWebSocket, 5000);
            };
            
            websocket.onerror = (error) => {
                console.error('WebSocket错误:', error);
                isOnline.value = false;
            };
        };
        
        // 刷新仪表板数据
        const refreshDashboard = async () => {
            if (isRefreshing.value) return;
            
            isRefreshing.value = true;
            
            try {
                const [statsResponse, alertsResponse] = await Promise.all([
                    fetch('/api/dashboard/stats'),
                    fetch('/api/dashboard/alerts')
                ]);
                
                if (statsResponse.ok && alertsResponse.ok) {
                    const stats = await statsResponse.json();
                    const alerts = await alertsResponse.json();
                    
                    updateDashboard(stats);
                    updateRecentAlerts(alerts);
                    
                    // 清除错误状态
                    Object.keys(error.value).forEach(key => {
                        error.value[key] = null;
                    });
                } else {
                    throw new Error('API请求失败');
                }
            } catch (err) {
                console.error('刷新仪表板失败:', err);
                const errorMessage = '数据加载失败: ' + err.message;
                
                Object.keys(error.value).forEach(key => {
                    error.value[key] = errorMessage;
                });
                
                ElMessage.error(errorMessage);
            } finally {
                isRefreshing.value = false;
                Object.keys(loading.value).forEach(key => {
                    loading.value[key] = false;
                });
            }
        };
        
        // 更新仪表板数据
        const updateDashboard = (data) => {
            updateSystemOverview(data);
            updatePerformanceMetrics(data);
            updateEventDistribution(data);
        };
        
        // 更新系统概览
        const updateSystemOverview = (data) => {
            console.log('updateSystemOverview called with data:', data);
            
            if (!data || !data.summary) {
                console.error('No data or summary found:', data);
                error.value.overview = '无数据';
                return;
            }
            
            const summary = data.summary;
            console.log('Summary data:', summary);
            
            systemOverviewHtml.value = `
                <div class="metric">
                    <span class="metric-label">总事件数</span>
                    <span class="metric-value">${summary.total_events || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">总错误数</span>
                    <span class="metric-value">${summary.total_errors || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">错误率</span>
                    <span class="metric-value">${((summary.overall_error_rate || 0) * 100).toFixed(1)}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">最近5分钟事件</span>
                    <span class="metric-value">${summary.recent_events_5min || 0}</span>
                </div>
            `;
            
            console.log('Updated systemOverviewHtml:', systemOverviewHtml.value);
            
            loading.value.overview = false;
            error.value.overview = null;
        };
        
        // 更新性能指标
        const updatePerformanceMetrics = (data) => {
            if (!data || !data.summary) {
                error.value.performance = '无数据';
                return;
            }
            
            const summary = data.summary;
            performanceMetricsHtml.value = `
                <div class="metric">
                    <span class="metric-label">平均处理时间</span>
                    <span class="metric-value">${(summary.recent_avg_processing_time_ms || 0).toFixed(2)}ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">平均队列等待</span>
                    <span class="metric-value">${(summary.recent_avg_queue_wait_time_ms || 0).toFixed(2)}ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">吞吐量/分钟</span>
                    <span class="metric-value">${(summary.throughput_per_min || 0).toFixed(1)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">最近5分钟错误率</span>
                    <span class="metric-value">${((summary.recent_error_rate_5min || 0) * 100).toFixed(1)}%</span>
                </div>
            `;
            
            loading.value.performance = false;
            error.value.performance = null;
        };
        
        // 更新事件类型分布
        const updateEventDistribution = (data) => {
            if (!data || !data.event_type_distribution) {
                error.value.distribution = '无数据';
                return;
            }
            
            const distribution = data.event_type_distribution;
            eventDistributionHtml.value = Object.entries(distribution).map(([type, stats]) => `
                <div class="metric">
                    <span class="metric-label">${type}</span>
                    <span class="metric-value">${stats.count} (${stats.percentage.toFixed(1)}%)</span>
                </div>
            `).join('');
            
            loading.value.distribution = false;
            error.value.distribution = null;
        };
        
        // 更新最近告警
        const updateRecentAlerts = (alerts) => {
            if (!alerts || alerts.length === 0) {
                recentAlertsHtml.value = '<div class="loading">暂无告警</div>';
                loading.value.alerts = false;
                error.value.alerts = null;
                return;
            }
            
            recentAlertsHtml.value = alerts.slice(0, 10).map(alert => {
                const time = new Date(alert.timestamp * 1000).toLocaleString('zh-CN');
                return `
                    <div class="alert-item ${alert.level}">
                        <div>${alert.message}</div>
                        <div class="alert-time">${time}</div>
                    </div>
                `;
            }).join('');
            
            loading.value.alerts = false;
            error.value.alerts = null;
        };
        
        // 格式化持续时间
        const formatDuration = (seconds) => {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            
            if (hours > 0) {
                return `${hours}h ${minutes}m ${secs}s`;
            } else if (minutes > 0) {
                return `${minutes}m ${secs}s`;
            } else {
                return `${secs}s`;
            }
        };
        
        // 生命周期钩子
        onMounted(() => {
            initWebSocket();
            refreshDashboard();
            
            // 设置自动刷新
            refreshInterval = setInterval(refreshDashboard, 30000); // 30秒刷新一次
        });
        
        onUnmounted(() => {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
            if (websocket) {
                websocket.close();
            }
        });
        
        return {
            isOnline,
            isRefreshing,
            loading,
            error,
            systemOverviewHtml,
            performanceMetricsHtml,
            eventDistributionHtml,
            recentAlertsHtml,
            statusIndicatorClass,
            refreshDashboard
        };
    }
};

// 创建并挂载应用
const app = createApp(DashboardApp);
app.use(ElementPlus);
app.mount('#dashboard-app');

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (window.websocket) {
        window.websocket.close();
    }
});