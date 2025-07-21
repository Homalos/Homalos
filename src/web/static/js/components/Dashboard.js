// 仪表板组件
// 使用全局变量替代ES6 import

const DashboardComponent = {
    name: 'DashboardComponent',
    template: `
        <el-row :gutter="20" class="stats-card">
            <el-col :span="6">
                <el-card>
                    <template #header>
                        <span>{{ t('dashboard.systemStatus') }}</span>
                    </template>
                    <div>
                        <el-tag :type="systemStatusType">
                            {{ systemStatusText }}
                        </el-tag>
                    </div>
                </el-card>
            </el-col>
            
            <el-col :span="6">
                <el-card>
                    <template #header>
                        <span>{{ t('dashboard.strategyCount') }}</span>
                    </template>
                    <div style="font-size: 2rem; color: #409EFF;">
                        {{ strategyCount }}
                    </div>
                </el-card>
            </el-col>
            
            <el-col :span="6">
                <el-card>
                    <template #header>
                        <span>{{ t('dashboard.accountBalance') }}</span>
                    </template>
                    <div style="font-size: 1.5rem; color: #67C23A;">
                        {{ formattedBalance }}
                    </div>
                </el-card>
            </el-col>
            
            <el-col :span="6">
                <el-card>
                    <template #header>
                        <span>{{ t('dashboard.connectionStatus') }}</span>
                    </template>
                    <div>
                        <el-tag :type="connectionStatusType">
                            {{ connectionStatusText }}
                        </el-tag>
                    </div>
                </el-card>
            </el-col>
        </el-row>
    `,
    
    setup() {
        const { state, getters } = window.useGlobalState()
        const { t } = window.useI18n()
        
        // 计算系统状态类型
        const systemStatusType = Vue.computed(() => {
            return state.system.isRunning ? 'success' : 'danger'
        })
        
        // 计算系统状态文本
        const systemStatusText = Vue.computed(() => {
            return state.system.isRunning ? t('dashboard.running') : t('dashboard.stopped')
        })
        
        // 计算策略数量
        const strategyCount = Vue.computed(() => {
            return Object.keys(state.strategies).length
        })
        
        // 计算格式化的余额
        const formattedBalance = Vue.computed(() => {
            const balance = state.accountInfo.totalBalance || 0
            return `¥${balance.toFixed(2)}`
        })
        
        // 计算连接状态类型
        const connectionStatusType = Vue.computed(() => {
            return state.wsConnection.connected ? 'success' : 'danger'
        })
        
        // 计算连接状态文本
        const connectionStatusText = Vue.computed(() => {
            return state.wsConnection.connected ? t('dashboard.connected') : t('dashboard.disconnected')
        })
        
        return {
            state,
            t,
            systemStatusType,
            systemStatusText,
            strategyCount,
            formattedBalance,
            connectionStatusType,
            connectionStatusText
        }
    }
}

// 导出到全局
window.DashboardComponent = DashboardComponent