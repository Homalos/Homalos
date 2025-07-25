// 策略表格组件
// 使用全局变量替代ES6 import

const StrategyTableComponent = {
    name: 'StrategyTableComponent',
    template: `
        <el-card class="strategy-table">
            <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>{{ t('strategy.management') }}</span>
                    <el-button 
                        type="primary" 
                        size="small" 
                        @click="openStrategyDialog"
                        :loading="state.ui.loading">
                        {{ t('strategy.loadStrategy') }}
                    </el-button>
                </div>
            </template>
            
            <el-table 
                :data="strategyList" 
                style="width: 100%"
                v-loading="state.ui.loading"
                :loading-text="state.ui.loadingText">
                
                <el-table-column 
                    prop="strategy_name" 
                    :label="t('strategy.strategyName')" 
                    width="200">
                </el-table-column>
                
                <el-table-column 
                    prop="strategy_uuid" 
                    :label="t('strategy.strategyUuid')" 
                    width="280">
                    <template #default="scope">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-family: monospace; font-size: 12px; color: #666;">
                                {{ scope.row.strategy_uuid || '-' }}
                            </span>
                            <el-button 
                                v-if="scope.row.strategy_uuid"
                                type="text" 
                                size="small"
                                @click="copyUuid(scope.row.strategy_uuid)"
                                :title="t('strategy.copyUuid')">
                            </el-button>
                        </div>
                    </template>
                </el-table-column>
                
                <el-table-column 
                    prop="status" 
                    :label="t('strategy.status')" 
                    width="120">
                    <template #default="scope">
                        <el-tag 
                            :type="getStatusType(scope.row.status)"
                            class="strategy-status-tag">
                            {{ scope.row.status }}
                        </el-tag>
                    </template>
                </el-table-column>
                
                <el-table-column 
                    prop="start_time" 
                    :label="t('strategy.startTime')" 
                    width="180">
                    <template #default="scope">
                        {{ formatTime(scope.row.start_time) }}
                    </template>
                </el-table-column>
                
                <el-table-column 
                    :label="t('strategy.actions')" 
                    width="200">
                    <template #default="scope">
                        <div class="strategy-actions">
                            <el-button 
                                @click="startStrategy(scope.row.strategy_uuid)"
                                :disabled="scope.row.status === 'running'"
                                type="success" 
                                size="small"
                                :loading="startingStrategies.has(scope.row.strategy_uuid)">
                                {{ t('strategy.start') }}
                            </el-button>
                            
                            <el-button 
                                @click="stopStrategy(scope.row.strategy_uuid)"
                                :disabled="scope.row.status !== 'running'"
                                type="danger" 
                                size="small"
                                :loading="stoppingStrategies.has(scope.row.strategy_uuid)">
                                {{ t('strategy.stop') }}
                            </el-button>
                        </div>
                    </template>
                </el-table-column>
            </el-table>
            
            <!-- 空状态 -->
            <div v-if="strategyList.length === 0" class="text-center mt-2">
                <el-empty :description="t('strategy.noStrategies')">
                    <el-button type="primary" @click="openStrategyDialog">
                        {{ t('strategy.loadFirstStrategy') }}
                    </el-button>
                </el-empty>
            </div>
        </el-card>
    `,
    
    setup() {
        const { state, actions } = window.useGlobalState()
        const { t } = window.useI18n()
        
        // 正在启动的策略集合
        const startingStrategies = Vue.ref(new Set())
        
        // 正在停止的策略集合  
        const stoppingStrategies = Vue.ref(new Set())
        
        // 计算策略列表
        const strategyList = Vue.computed(() => {
            return Object.values(state.strategies)
        })
        
        // 获取状态类型
        const getStatusType = (status) => {
            const types = {
                'running': 'success',
                'stopped': 'info',
                'error': 'danger',
                'loading': 'warning',
                'loaded': 'info'
            }
            return types[status] || 'info'
        }
        
        // 格式化时间
        const formatTime = (timestamp) => {
            if (!timestamp) return '-'
            return new Date(timestamp * 1000).toLocaleString()
        }
        
        // 打开策略对话框
        const openStrategyDialog = () => {
            actions.toggleStrategyDialog(true)
        }
        
        // 启动策略 - 使用UUID
        const startStrategy = async (strategyUuid) => {
            try {
                startingStrategies.value.add(strategyUuid)
                
                const response = await window.ApiService.startStrategy(strategyUuid)
                
                if (window.ApiResponse.isSuccess(response)) {
                    window.ElMessage.success(t('strategy.startSuccess'))
                    // 刷新策略列表
                    await refreshStrategies()
                } else {
                    window.ElMessage.error(window.ApiResponse.getMessage(response))
                }
                
            } catch (error) {
                console.error(t('strategy.startFailed'), error)
                window.ElMessage.error(t('strategy.startFailed'))
            } finally {
                startingStrategies.value.delete(strategyUuid)
            }
        }
        
        // 停止策略 - 使用UUID
        const stopStrategy = async (strategyUuid) => {
            try {
                stoppingStrategies.value.add(strategyUuid)
                
                const response = await window.ApiService.stopStrategy(strategyUuid)
                
                if (window.ApiResponse.isSuccess(response)) {
                    window.ElMessage.success(t('strategy.stopSuccess'))
                    // 刷新策略列表
                    await refreshStrategies()
                } else {
                    window.ElMessage.error(window.ApiResponse.getMessage(response))
                }
                
            } catch (error) {
                console.error(t('strategy.stopFailed'), error)
                window.ElMessage.error(t('strategy.stopFailed'))
            } finally {
                stoppingStrategies.value.delete(strategyUuid)
            }
        }
        
        // 刷新策略列表
        const refreshStrategies = async () => {
            try {
                const response = await window.ApiService.getStrategies()
                
                if (window.ApiResponse.isSuccess(response)) {
                    actions.updateStrategies(window.ApiResponse.getData(response).strategies)
                }
                
            } catch (error) {
                console.error('刷新策略列表失败:', error)
            }
        }
        
        // 复制UUID到剪贴板
        const copyUuid = async (uuid) => {
            try {
                await navigator.clipboard.writeText(uuid)
                window.ElMessage.success(t('strategy.uuidCopied'))
            } catch (error) {
                console.error('复制UUID失败:', error)
                // 降级方案：使用传统方法
                const textArea = document.createElement('textarea')
                textArea.value = uuid
                document.body.appendChild(textArea)
                textArea.select()
                document.execCommand('copy')
                document.body.removeChild(textArea)
                window.ElMessage.success(t('strategy.uuidCopied'))
            }
        }
        
        return {
            state,
            t,
            strategyList,
            startingStrategies,
            stoppingStrategies,
            copyUuid,
            getStatusType,
            formatTime,
            openStrategyDialog,
            startStrategy,
            stopStrategy
        }
    }
}

// 导出到全局
window.StrategyTableComponent = StrategyTableComponent