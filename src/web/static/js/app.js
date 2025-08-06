// Vue主应用入口
// 使用全局变量替代ES6 import

// 主应用组件
const MainApp = {
    name: 'MainApp',
    template: `
        <div>
            <!-- 头部 -->
            <header class="header">
                <div class="header-content">
                    <div class="header-title">
                        <h1>{{ t('header.title') || 'Homalos量化交易系统' }}</h1>
                        <p>{{ t('header.subtitle') || '基于Python的期货量化交易系统 v0.0.1' }}</p>
                    </div>
                    <div class="header-nav">
                        <nav class="nav-menu">
                            <a href="#" @click="currentPage = 'main'" class="nav-item" :class="{ active: currentPage === 'main' }">
                                <i class="el-icon-house"></i>
                                {{ t('navigation.home') || '主页' }}
                            </a>
                            <a href="/dashboard" class="nav-item" target="_blank">
                                <i class="el-icon-data-analysis"></i>
                                {{ t('navigation.eventMonitor') || '事件监控' }}
                            </a>
                        </nav>
                    </div>
                    <div class="header-actions">
                        <language-switcher-component></language-switcher-component>
                    </div>
                </div>
            </header>
            
            <!-- 主容器 -->
            <div class="container">
                <div v-if="currentPage === 'main'">
                    <!-- 仪表板组件 -->
                    <dashboard-component></dashboard-component>
                    
                    <!-- 策略管理组件 -->
                    <strategy-table-component></strategy-table-component>
                    
                    <!-- 交易图表入口 -->
                    <div class="trading-chart-entry">
                        <el-card class="chart-entry-card">
                            <div class="chart-entry-content">
                                <h3>📈 交易图表</h3>
                                <p>查看实时K线图表、交易信号和策略绩效</p>
                                <el-button type="primary" @click="openChartPage" size="large">
                                    <i class="el-icon-data-line"></i>
                                    打开交易图表
                                </el-button>
                            </div>
                        </el-card>
                    </div>
                    
                    <!-- 调试面板 -->
                    <div class="debug-panel" style="margin: 20px 0;">
                        <el-card>
                            <template #header>
                                <span>🔍 WebSocket调试工具</span>
                            </template>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <el-button type="primary" @click="testWebSocketMessages" size="small">
                                    测试WebSocket消息接收
                                </el-button>
                                <el-button type="success" @click="clearDebugLogs" size="small">
                                    清空调试日志
                                </el-button>
                                <span style="margin-left: 10px; color: #666;">检查浏览器控制台查看详细调试信息</span>
                            </div>
                        </el-card>
                    </div>
                    
                    <!-- 日志面板组件 -->
                    <log-panel-component></log-panel-component>
                </div>
                

            </div>
            
            <!-- 策略加载对话框 -->
            <strategy-dialog-component></strategy-dialog-component>
            
            <!-- 版权声明 -->
            <footer class="footer">
                <div class="footer-content">
                    <p class="copyright">{{ t('footer.copyright') }}</p>
                </div>
            </footer>
        </div>
    `,
    
    setup() {
        const { state, actions } = window.useGlobalState()
        const { t } = window.useI18n()
        
        // 当前页面状态
        const currentPage = Vue.ref('main')
        
        // 系统状态数据
        const systemStatus = Vue.ref({})
        const strategies = Vue.ref([])
        const accountInfo = Vue.ref({})
        const refreshTimer = Vue.ref(null)
        
        // 初始化数据加载
        const initializeApp = async () => {
            actions.setLoading(true, t('system.initializingSystem'))
            
            try {
                // 并行加载初始数据
                const [systemStatus, strategies, accountInfo] = await Promise.all([
                    window.ApiService.getSystemStatus(),
                    window.ApiService.getStrategies(),
                    window.ApiService.getAccountInfo()
                ])
                
                // 更新状态
                if (window.ApiResponse.isSuccess(systemStatus)) {
                    actions.updateSystemStatus(window.ApiResponse.getData(systemStatus))
                }
                
                if (window.ApiResponse.isSuccess(strategies)) {
                    actions.updateStrategies(window.ApiResponse.getData(strategies).strategies)
                }
                
                if (window.ApiResponse.isSuccess(accountInfo)) {
                    actions.updateAccountInfo(window.ApiResponse.getData(accountInfo))
                }
                
                // 连接WebSocket
                window.wsService.connect()
                
                console.log(t('system.appInitialized'))
                
            } catch (error) {
                console.error(t('system.appInitFailed'), error)
                actions.addLog('error', `${t('system.appInitFailed')}: ${error.message}`)
            } finally {
                actions.setLoading(false)
            }
        }
        
        // 定期刷新数据
        const startDataRefresh = () => {
            setInterval(async () => {
                try {
                    const [systemStatus, strategies, accountInfo] = await Promise.all([
                        window.ApiService.getSystemStatus(),
                        window.ApiService.getStrategies(),
                        window.ApiService.getAccountInfo()
                    ])
                    
                    if (window.ApiResponse.isSuccess(systemStatus)) {
                        actions.updateSystemStatus(window.ApiResponse.getData(systemStatus))
                    }
                    
                    if (window.ApiResponse.isSuccess(strategies)) {
                        actions.updateStrategies(window.ApiResponse.getData(strategies).strategies)
                    }
                    
                    if (window.ApiResponse.isSuccess(accountInfo)) {
                        actions.updateAccountInfo(window.ApiResponse.getData(accountInfo))
                    }
                    
                } catch (error) {
                    console.warn('数据刷新失败:', error)
                }
            }, 5000) // 每5秒刷新一次
        }
        
        // 组件挂载后初始化
        Vue.onMounted(() => {
            initializeApp()
            startDataRefresh()
        })
        
        // 组件卸载时清理
        Vue.onUnmounted(() => {
            window.wsService.disconnect()
        })
        
        // 打开交易图表页面
        const openChartPage = () => {
            window.open('/chart', '_blank')
        }
        
        // 调试方法：测试WebSocket消息接收
        const testWebSocketMessages = () => {
            console.log('🔍 开始测试WebSocket消息接收...')
            
            // 添加调试日志
            actions.addLog('info', '🔍 [调试] 开始测试WebSocket消息接收')
            
            // 检查WebSocket连接状态
            if (window.wsService && window.wsService.isConnected()) {
                console.log('✅ WebSocket连接正常')
                actions.addLog('success', '✅ WebSocket连接状态正常')
                
                // 模拟发送一个测试事件
                const testEvent = {
                    type: 'event',
                    event_type: 'strategy.started',
                    data: {
                        strategy_id: 'test_strategy',
                        strategy_uuid: 'test-uuid-12345',
                        strategy_name: 'TestStrategy',
                        message: '策略 TestStrategy 启动成功',
                        timestamp: Date.now() / 1000
                    },
                    source: 'DebugTest',
                    timestamp: Date.now() / 1000
                }
                
                console.log('🧪 模拟处理strategy.started事件:', testEvent)
                actions.addLog('info', '🧪 [调试] 模拟处理strategy.started事件')
                
                // 直接调用WebSocket的事件处理方法
                if (window.wsService.handleEventMessage) {
                    window.wsService.handleEventMessage(testEvent)
                } else {
                    console.error('❌ WebSocket事件处理方法不存在')
                    actions.addLog('error', '❌ WebSocket事件处理方法不存在')
                }
            } else {
                console.error('❌ WebSocket连接异常')
                actions.addLog('error', '❌ WebSocket连接异常，请检查连接状态')
            }
        }
        
        // 调试方法：清空调试日志
        const clearDebugLogs = () => {
            console.clear()
            actions.addLog('info', '🧹 [调试] 浏览器控制台已清空')
        }
        
        return {
            state,
            currentPage,
            t,
            openChartPage,
            testWebSocketMessages,
            clearDebugLogs
        }
    }
}

// 🔧 修复时序问题：立即添加事件监听器，不等待DOMContentLoaded
console.log('🚀 正在设置Vue应用启动监听器...')

// 等待所有组件准备就绪
window.addEventListener('componentsReady', () => {
    console.log('📡 接收到componentsReady事件')
    
    // 确保DOM已准备就绪
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createVueApp)
    } else {
        createVueApp()
    }
})

// 创建Vue应用函数
function createVueApp() {
    try {
        console.log('开始创建Vue应用...')
        
        // 检查依赖是否加载
        if (typeof Vue === 'undefined') {
            console.error('Vue未加载')
            return
        }
        
        if (typeof ElementPlus === 'undefined') {
            console.error('ElementPlus未加载')
            return
        }
        
        // 创建Vue应用
        const app = Vue.createApp(MainApp)
        
        // 使用ElementPlus
        app.use(ElementPlus)
        
        // 暴露ElementPlus组件到全局作用域，解决组件内部访问问题
        window.ElMessage = ElementPlus.ElMessage
        window.ElMessageBox = ElementPlus.ElMessageBox
        window.ElNotification = ElementPlus.ElNotification
        window.ElLoading = ElementPlus.ElLoading
        
        console.log('✅ ElementPlus组件已暴露到全局作用域')
        
        // 注册其他组件
        if (window.VueComponentRegistry) {
            const registry = window.VueComponentRegistry
            
            if (registry.DashboardComponent) {
                app.component('dashboard-component', registry.DashboardComponent)
                console.log('✅ dashboard-component 已注册到Vue应用')
            }
            if (registry.StrategyTableComponent) {
                app.component('strategy-table-component', registry.StrategyTableComponent)
                console.log('✅ strategy-table-component 已注册到Vue应用')
            }
            if (registry.StrategyDialogComponent) {
                app.component('strategy-dialog-component', registry.StrategyDialogComponent)
                console.log('✅ strategy-dialog-component 已注册到Vue应用')
            }
            if (registry.LogPanelComponent) {
                app.component('log-panel-component', registry.LogPanelComponent)
                console.log('✅ log-panel-component 已注册到Vue应用')
            }
            if (registry.LanguageSwitcherComponent) {
                app.component('language-switcher-component', registry.LanguageSwitcherComponent)
                console.log('✅ language-switcher-component 已注册到Vue应用')
            }
            if (registry.TradingChartComponent) {
                app.component('trading-chart-component', registry.TradingChartComponent)
                console.log('✅ trading-chart-component 已注册到Vue应用')
            }
        }
        
        // 挂载应用到#app
        const appElement = document.getElementById('app')
        if (appElement) {
            app.mount('#app')
            console.log('🎉 Vue应用已成功挂载到 #app')
        } else {
            console.error('❌ 找不到 #app 挂载点')
        }
        
    } catch (error) {
        console.error('Vue应用启动失败:', error)
    }
}

// 将MainApp导出到全局
window.MainApp = MainApp

// 工具函数
window.HomalosUtils = {
    // 格式化时间
    formatTime(timestamp) {
        return new Date(timestamp * 1000).toLocaleString()
    },
    
    // 格式化金额
    formatCurrency(amount) {
        return `¥${(amount || 0).toFixed(2)}`
    },
    
    // 获取状态类型
    getStatusType(status) {
        const types = {
            'running': 'success',
            'stopped': 'info',
            'error': 'danger',
            'loading': 'warning',
            'loaded': 'info'
        }
        return types[status] || 'info'
    },
    
    // 获取日志颜色
    getLogColor(type) {
        const colors = {
            'error': '#F56C6C',
            'warning': '#E6A23C',
            'success': '#67C23A',
            'info': '#409EFF'
        }
        return colors[type] || '#909399'
    }
}