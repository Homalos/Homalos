// 策略加载对话框组件
// 使用全局变量替代ES6 import

const StrategyDialogComponent = {
    name: 'StrategyDialogComponent',
    template: `
        <el-dialog 
            v-model="state.ui.strategyDialogVisible" 
            title="加载策略" 
            width="800px"
            class="strategy-dialog"
            :close-on-click-modal="false">
            
            <!-- 策略选择区域 -->
            <div v-if="availableStrategies.length > 0">
                <h4>1. 选择策略文件：</h4>
                
                <el-radio-group v-model="selectedStrategyId">
                    <div v-for="strategy in availableStrategies" 
                         :key="strategy.file_name" 
                         class="strategy-option" 
                         :class="{ selected: selectedStrategyId === strategy.file_name }"
                         :data-strategy="strategy.file_name"
                         @click="selectStrategy(strategy)">
                         
                        <el-radio :label="strategy.file_name" class="strategy-radio">
                            <span class="strategy-filename">📁 {{ strategy.file_name }}</span>
                        </el-radio>
                        
                        <div class="strategy-classes-container">
                            <div v-for="cls in strategy.strategy_classes" 
                                 :key="cls.class_name" 
                                 class="strategy-class-card">
                                 
                                <div class="strategy-class-header">
                                    <el-tag size="small" type="primary">{{ cls.name }}</el-tag>
                                    <el-tag size="small" type="info">v{{ cls.version }}</el-tag>
                                    <el-tag size="small" type="success">{{ cls.class_name }}</el-tag>
                                </div>
                                
                                <div class="strategy-class-meta">
                                    <i class="el-icon-user"></i> 
                                    作者: {{ Array.isArray(cls.authors) ? cls.authors.join(', ') : cls.authors }}
                                </div>
                                
                                <div class="strategy-class-description">
                                    {{ cls.description }}
                                </div>
                            </div>
                        </div>
                    </div>
                </el-radio-group>
                
                <!-- 参数配置区域 -->
                <div v-if="selectedStrategy" class="strategy-params-section">
                    <h4>2. 配置策略参数（可选）：</h4>
                    
                    <el-form :model="strategyFormData" label-width="120px" class="strategy-form">
                        <el-form-item label="策略参数">
                            <div style="width: 100%;">
                                <el-input 
                                    v-model="paramsJsonText" 
                                    type="textarea" 
                                    :rows="4"
                                    placeholder='{"symbol": "rb2510", "volume": 1}'
                                    @input="updateParams"
                                    style="width: 100%;">
                                </el-input>
                                <div style="margin-top: 0.5rem;">
                                    <el-text type="info">
                                        请输入JSON格式的策略参数（可选）
                                    </el-text>
                                    <el-text v-if="paramError" type="danger" style="margin-left: 1rem;">
                                        {{ paramError }}
                                    </el-text>
                                </div>
                            </div>
                        </el-form-item>
                    </el-form>
                    
                    <!-- 预览信息 -->
                    <div class="strategy-preview">
                        <h5>预览信息：</h5>
                        <p><strong>文件路径：</strong>{{ selectedStrategy.file_path }}</p>
                        <p><strong>策略类：</strong>{{ selectedStrategy.strategy_classes.map(c => c.class_name).join(', ') }}</p>
                        <p><strong>是否模板：</strong>{{ selectedStrategy.is_template ? '是' : '否' }}</p>
                        <p v-if="strategyFormData.params && Object.keys(strategyFormData.params).length > 0">
                            <strong>参数预览：</strong>{{ JSON.stringify(strategyFormData.params, null, 2) }}
                        </p>
                        <p><strong>说明：</strong>系统将自动生成策略UUID作为唯一标识</p>
                    </div>
                </div>
            </div>
            
            <!-- 空状态 -->
            <div v-else-if="!loadingStrategies" style="text-align: center; padding: 2rem;">
                <el-empty :description="getEmptyDescription">
                    <el-button @click="refreshAvailableStrategies" type="primary">
                        重新扫描
                    </el-button>
                    <el-button @click="closeDialog" style="margin-left: 1rem;">
                        关闭
                    </el-button>
                </el-empty>
            </div>
            
            <!-- 加载状态 -->
            <div v-else style="text-align: center; padding: 2rem;">
                <el-skeleton :rows="3" animated />
            </div>
            
            <!-- 对话框底部 -->
            <template #footer>
                <span class="dialog-footer">
                    <el-button @click="closeDialog">取消</el-button>
                    <el-button 
                        type="primary" 
                        @click="executeStrategyLoad"
                        :disabled="!canLoadStrategy"
                        :loading="loadingStrategy">
                        加载策略
                    </el-button>
                </span>
            </template>
        </el-dialog>
    `,
    
    setup() {
        const { state, actions } = window.useGlobalState()
        
        // 本地响应式数据
        const availableStrategies = Vue.ref([])
        const selectedStrategy = Vue.ref(null) // 完整的策略对象
        const selectedStrategyId = Vue.ref('') // 策略文件名，用于ElRadio绑定
        const loadingStrategies = Vue.ref(false)
        const loadingStrategy = Vue.ref(false)
        const paramError = Vue.ref('')
        const allDiscoveredStrategies = Vue.ref([]) // 保存所有发现的策略，用于区分空状态
        
        // 表单数据
        const strategyFormData = Vue.reactive({
            params: {}
        })
        
        const paramsJsonText = Vue.ref('')
        
        // 计算是否可以加载策略 - 移除策略ID检查，只检查策略选择和参数格式
        const canLoadStrategy = Vue.computed(() => {
            return selectedStrategy.value && !paramError.value
        })
        
        // 获取空状态描述
        const getEmptyDescription = Vue.computed(() => {
            if (loadingStrategies.value) {
                return '正在扫描策略文件...'
            }
            
            if (allDiscoveredStrategies.value.length === 0) {
                return '未发现任何策略文件，请检查策略目录'
            }
            
            if (availableStrategies.value.length === 0 && allDiscoveredStrategies.value.length > 0) {
                return `所有 ${allDiscoveredStrategies.value.length} 个策略都已加载，暂无新策略可加载`
            }
            
            return '未发现可用策略文件'
        })
        
        // 选择策略
        const selectStrategy = (strategy) => {
            selectedStrategy.value = strategy
            selectedStrategyId.value = strategy.file_name
            actions.selectStrategy(strategy)
        }
        
        // 更新参数
        const updateParams = () => {
            paramError.value = ''
            
            try {
                if (paramsJsonText.value.trim() === '') {
                    strategyFormData.params = {}
                } else {
                    strategyFormData.params = JSON.parse(paramsJsonText.value)
                }
            } catch (error) {
                paramError.value = 'JSON格式错误'
            }
        }
        
        // 加载可用策略
        const loadAvailableStrategies = async () => {
            try {
                loadingStrategies.value = true
                
                const response = await window.ApiService.discoverStrategies()
                
                if (window.ApiResponse.isSuccess(response)) {
                    const allStrategies = window.ApiResponse.getData(response).available_strategies
                    
                    // 过滤掉已加载的策略，避免重复加载 - 使用UUID精确匹配
                    const loadedStrategyUuids = new Set()
                    const loadedStrategyPaths = new Set()
                    
                    // 从已加载策略中收集UUID和路径信息
                    Object.values(state.strategies).forEach(s => {
                        // 优先使用UUID进行匹配
                        if (s.strategy_uuid) {
                            loadedStrategyUuids.add(s.strategy_uuid)
                        }
                        
                        // 同时收集路径信息作为备用匹配方式
                        if (s.strategy_path) {
                            loadedStrategyPaths.add(s.strategy_path)
                            // 标准化路径处理，同时支持Windows和Unix风格
                            const normalizedPath = s.strategy_path.replace(/\\/g, '/')
                            loadedStrategyPaths.add(normalizedPath)
                            
                            // 获取绝对路径的相对部分
                            const relativePath = normalizedPath.startsWith('src/') ? 
                                normalizedPath : normalizedPath.substring(normalizedPath.indexOf('src/'))
                            if (relativePath !== normalizedPath) {
                                loadedStrategyPaths.add(relativePath)
                            }
                        }
                    })
                    
                    console.debug('已加载策略UUID:', Array.from(loadedStrategyUuids))
                    console.debug('已加载策略路径:', Array.from(loadedStrategyPaths))
                    
                    // 过滤策略文件 - 改进的匹配算法，优先使用路径匹配
                    const filteredStrategies = allStrategies.filter(strategy => {
                        const strategyPath = strategy.file_path
                        const normalizedStrategyPath = strategyPath.replace(/\\/g, '/')
                        
                        // 检查完整路径匹配
                        if (loadedStrategyPaths.has(strategyPath) || 
                            loadedStrategyPaths.has(normalizedStrategyPath)) {
                            console.debug(`策略已加载(完整路径匹配): ${strategyPath}`)
                            return false
                        }
                        
                        // 检查相对路径匹配
                        const relativeStrategyPath = normalizedStrategyPath.startsWith('src/') ? 
                            normalizedStrategyPath : normalizedStrategyPath.substring(normalizedStrategyPath.indexOf('src/'))
                        if (loadedStrategyPaths.has(relativeStrategyPath)) {
                            console.debug(`策略已加载(相对路径匹配): ${strategyPath}`)
                            return false
                        }
                        
                        console.debug(`策略可加载: ${strategyPath}`)
                        return true
                    })
                    
                    availableStrategies.value = filteredStrategies
                    actions.updateAvailableStrategies(filteredStrategies)
                    allDiscoveredStrategies.value = allStrategies // 更新所有发现的策略
                    
                    // 如果没有可用策略，显示提示
                    if (filteredStrategies.length === 0 && allStrategies.length > 0) {
                        actions.addLog('info', '所有策略都已加载，没有新的策略可以加载')
                    } else if (filteredStrategies.length > 0) {
                        actions.addLog('info', `发现 ${filteredStrategies.length} 个可加载的策略文件`)
                    }
                    
                } else {
                    window.ElMessage.error('获取策略列表失败')
                }
                
            } catch (error) {
                console.error('获取策略列表失败:', error)
                window.ElMessage.error('获取策略列表失败')
            } finally {
                loadingStrategies.value = false
            }
        }
        
        // 刷新可用策略
        const refreshAvailableStrategies = () => {
            loadAvailableStrategies()
        }
        
        // 执行策略加载 - 移除策略ID输入要求
        const executeStrategyLoad = async () => {
            if (!selectedStrategy.value) {
                window.ElMessage.warning('请选择策略文件')
                return
            }
            
            try {
                loadingStrategy.value = true
                
                const payload = {
                    strategy_path: selectedStrategy.value.file_path,
                    strategy_name: selectedStrategy.value.file_name.replace('.py', ''),  // 使用文件名作为默认名称
                    params: strategyFormData.params
                }
                
                const response = await window.ApiService.loadStrategy(payload)
                
                if (window.ApiResponse.isSuccess(response)) {
                    const responseData = window.ApiResponse.getData(response)
                    const strategyUuid = responseData.strategy_uuid
                    
                    window.ElMessage.success('策略加载成功')
                    closeDialog()
                    
                    // 通知父组件刷新策略列表
                    actions.addLog('info', `策略加载成功，UUID: ${strategyUuid}`)
                    
                } else {
                    window.ElMessage.error(window.ApiResponse.getMessage(response))
                }
                
            } catch (error) {
                console.error('策略加载失败:', error)
                window.ElMessage.error('策略加载失败')
            } finally {
                loadingStrategy.value = false
            }
        }
        
        // 关闭对话框
        const closeDialog = () => {
            actions.toggleStrategyDialog(false)
            resetForm()
        }
        
        // 重置表单
        const resetForm = () => {
            selectedStrategy.value = null
            selectedStrategyId.value = ''
            strategyFormData.params = {}
            paramsJsonText.value = ''
            paramError.value = ''
            actions.selectStrategy(null)
        }
        
        // 监听对话框打开事件
        Vue.watch(
            () => state.ui.strategyDialogVisible,
            (visible) => {
                if (visible) {
                    resetForm()
                    loadAvailableStrategies()
                }
            }
        )
        
        return {
            state,
            availableStrategies,
            selectedStrategy,
            selectedStrategyId,
            loadingStrategies,
            loadingStrategy,
            strategyFormData,
            paramsJsonText,
            paramError,
            canLoadStrategy,
            selectStrategy,
            updateParams,
            refreshAvailableStrategies,
            executeStrategyLoad,
            closeDialog,
            getEmptyDescription
        }
    }
}

// 导出到全局
window.StrategyDialogComponent = StrategyDialogComponent 