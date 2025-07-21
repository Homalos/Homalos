// 日志面板组件
// 使用全局变量替代ES6 import

const LogPanelComponent = {
    name: 'LogPanelComponent',
    template: `
        <el-card style="margin-top: 1rem;">
            <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>{{ t('log.realtimeLog') }}</span>
                    <div>
                        <el-button-group size="small">
                            <el-button 
                                @click="toggleAutoScroll"
                                :type="autoScroll ? 'primary' : 'default'"
                                :icon="autoScroll ? 'VideoPlay' : 'VideoPause'">
                                {{ autoScroll ? t('log.autoScroll') : t('log.pauseScroll') }}
                            </el-button>
                            <el-button 
                                @click="clearLogs"
                                type="warning"
                                icon="Delete">
                                {{ t('log.clear') }}
                            </el-button>
                        </el-button-group>
                    </div>
                </div>
            </template>
            
            <!-- 日志过滤器 -->
            <div style="margin-bottom: 1rem;">
                <el-row :gutter="10" align="middle">
                    <el-col :span="4">
                        <el-text>{{ t('log.logLevel') }}：</el-text>
                    </el-col>
                    <el-col :span="20">
                        <el-checkbox-group v-model="visibleLogTypes">
                            <el-checkbox 
                                v-for="type in logTypes" 
                                :key="type.value"
                                :label="type.value"
                                :style="{ color: type.color }">
                                {{ type.label }}
                            </el-checkbox>
                        </el-checkbox-group>
                    </el-col>
                </el-row>
            </div>
            
            <!-- 日志显示区域 -->
            <div 
                ref="logContainer"
                class="real-time-log"
                v-loading="state.ui.loading"
                loading-text="加载中...">
                
                <div 
                    v-for="log in filteredLogs" 
                    :key="log.id" 
                    class="log-item"
                    :class="getLogClass(log.type)">
                    
                    <span class="log-time">{{ log.timestamp }}</span>
                    <el-tag 
                        :type="getLogTagType(log.type)" 
                        size="small" 
                        class="log-type">
                        {{ getLogTypeText(log.type) }}
                    </el-tag>
                    <span class="log-message">{{ log.message }}</span>
                </div>
                
                <!-- 空状态 -->
                <div v-if="filteredLogs.length === 0" class="text-center" style="padding: 2rem;">
                    <el-empty :description="t('log.noLogs')">
                        <el-text type="info">
                            {{ state.realtimeLogs.length === 0 ? t('log.systemWillShowLogs') : t('log.noLogsWithFilter') }}
                        </el-text>
                    </el-empty>
                </div>
            </div>
            
            <!-- 日志统计 -->
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e4e7ed;">
                <el-row :gutter="20">
                    <el-col :span="6">
                        <el-statistic :title="t('log.totalLogs')" :value="state.realtimeLogs.length" />
                    </el-col>
                    <el-col :span="6">
                        <el-statistic :title="t('log.displayedLogs')" :value="filteredLogs.length" />
                    </el-col>
                    <el-col :span="6">
                        <el-statistic :title="t('log.errorCount')" :value="getLogCountByType('error')" />
                    </el-col>
                    <el-col :span="6">
                        <el-statistic :title="t('log.warningCount')" :value="getLogCountByType('warning')" />
                    </el-col>
                </el-row>
            </div>
        </el-card>
    `,
    
    setup() {
        const { state, actions } = window.useGlobalState()
        const { t } = window.useI18n()
        
        // 组件引用
        const logContainer = Vue.ref(null)
        
        // 本地状态
        const autoScroll = Vue.ref(true)
        const visibleLogTypes = Vue.ref(['info', 'success', 'warning', 'error'])
        
        // 日志类型定义
        const logTypes = Vue.computed(() => [
            { value: 'info', label: t('log.info'), color: '#409EFF' },
            { value: 'success', label: t('log.success'), color: '#67C23A' },
            { value: 'warning', label: t('log.warning'), color: '#E6A23C' },
            { value: 'error', label: t('log.error'), color: '#F56C6C' }
        ])
        
        // 过滤后的日志
        const filteredLogs = Vue.computed(() => {
            return state.realtimeLogs.filter(log => 
                visibleLogTypes.value.includes(log.type)
            )
        })
        
        // 获取日志类名
        const getLogClass = (type) => {
            return `log-item-${type}`
        }
        
        // 获取日志标签类型
        const getLogTagType = (type) => {
            const typeMap = {
                'info': 'info',
                'success': 'success',
                'warning': 'warning',
                'error': 'danger'
            }
            return typeMap[type] || 'info'
        }
        
        // 获取日志类型文本
        const getLogTypeText = (type) => {
            const textMap = {
                'info': t('log.info'),
                'success': t('log.success'),
                'warning': t('log.warning'),
                'error': t('log.error')
            }
            return textMap[type] || type.toUpperCase()
        }
        
        // 获取特定类型的日志数量
        const getLogCountByType = (type) => {
            return state.realtimeLogs.filter(log => log.type === type).length
        }
        
        // 切换自动滚动
        const toggleAutoScroll = () => {
            autoScroll.value = !autoScroll.value
            
            if (autoScroll.value) {
                Vue.nextTick(() => {
                    scrollToBottom()
                })
            }
        }
        
        // 滚动到底部
        const scrollToBottom = () => {
            if (logContainer.value) {
                logContainer.value.scrollTop = logContainer.value.scrollHeight
            }
        }
        
        // 清空日志
        const clearLogs = () => {
            ElMessageBox.confirm(t('log.confirmClearLogs'), t('log.confirmOperation'), {
                confirmButtonText: t('common.confirm'),
                cancelButtonText: t('common.cancel'),
                type: 'warning'
            }).then(() => {
                actions.clearLogs()
                ElMessage.success(t('log.logsCleared'))
            }).catch(() => {
                // 用户取消
            })
        }
        
        // 监听日志变化，自动滚动
        Vue.watch(
            () => state.realtimeLogs.length,
            () => {
                if (autoScroll.value) {
                    Vue.nextTick(() => {
                        scrollToBottom()
                    })
                }
            }
        )
        
        // 监听过滤条件变化，自动滚动
        Vue.watch(
            () => visibleLogTypes.value,
            () => {
                if (autoScroll.value) {
                    Vue.nextTick(() => {
                        scrollToBottom()
                    })
                }
            },
            { deep: true }
        )
        
        // 手动滚动时暂停自动滚动
        const handleScroll = () => {
            if (logContainer.value) {
                const { scrollTop, scrollHeight, clientHeight } = logContainer.value
                const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 5
                
                if (!isAtBottom && autoScroll.value) {
                    // 用户手动滚动时暂时暂停自动滚动
                    autoScroll.value = false
                }
            }
        }
        
        // 组件挂载后设置滚动监听
        Vue.onMounted(() => {
            if (logContainer.value) {
                logContainer.value.addEventListener('scroll', handleScroll)
            }
        })
        
        // 组件卸载时清理监听
        Vue.onUnmounted(() => {
            if (logContainer.value) {
                logContainer.value.removeEventListener('scroll', handleScroll)
            }
        })
        
        return {
            state,
            logContainer,
            autoScroll,
            visibleLogTypes,
            logTypes,
            filteredLogs,
            getLogClass,
            getLogTagType,
            getLogTypeText,
            getLogCountByType,
            toggleAutoScroll,
            clearLogs,
            t
        }
    }
}

// 导出到全局
window.LogPanelComponent = LogPanelComponent