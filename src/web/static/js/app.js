// Vue主应用入口
// 使用全局变量替代ES6 import

// 主应用组件
const MainApp = {
    name: 'MainApp',
    template: `
        <div>
            <!-- 头部 -->
            <header class="header">
                <h1>🚀 Homalos量化交易系统</h1>
                <p>基于Python的期货量化交易系统 v2.0</p>
            </header>
            
            <!-- 主容器 -->
            <div class="container">
                <!-- 仪表板组件 -->
                <dashboard-component></dashboard-component>
                
                <!-- 策略管理组件 -->
                <strategy-table-component></strategy-table-component>
                
                <!-- 日志面板组件 -->
                <log-panel-component></log-panel-component>
            </div>
            
            <!-- 策略加载对话框 -->
            <strategy-dialog-component></strategy-dialog-component>
        </div>
    `,
    
    setup() {
        const { state, actions } = window.useGlobalState()
        
        // 初始化数据加载
        const initializeApp = async () => {
            actions.setLoading(true, '正在初始化系统...')
            
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
                
                console.log('应用初始化完成')
                
            } catch (error) {
                console.error('应用初始化失败:', error)
                actions.addLog('error', `应用初始化失败: ${error.message}`)
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
        
        return {
            state
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