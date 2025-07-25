// 交易图表组件 - 多策略交易过程可视化
// 使用ECharts 5 + Vue3实现K线图和交易信号展示

const TradingChartComponent = {
    name: 'TradingChart',
    template: `
        <div class="trading-chart-container">
            <!-- 组件标题 -->
            <div class="chart-header">
                <h2>{{ t('trading.chartTitle') || '📈 交易图表' }}</h2>
                <p>{{ t('trading.chartDescription') || '实时K线图表、交易信号和策略绩效监控' }}</p>
            </div>
            
            <!-- 图表控制面板 -->
            <div class="chart-controls">
                <div class="control-group">
                    <label>{{ t('trading.symbol') || '交易品种' }}:</label>
                    <el-select v-model="selectedSymbol" @change="onSymbolChange" placeholder="选择品种">
                        <el-option
                            v-for="symbol in availableSymbols"
                            :key="symbol"
                            :label="symbol"
                            :value="symbol">
                        </el-option>
                    </el-select>
                </div>
                
                <div class="control-group">
                    <label>{{ t('trading.strategy') || '策略' }}:</label>
                    <el-select v-model="selectedStrategies" multiple placeholder="选择策略" @change="onStrategyChange">
                        <el-option
                            v-for="strategy in activeStrategies"
                            :key="strategy.uuid"
                            :label="strategy.name"
                            :value="strategy.uuid">
                        </el-option>
                    </el-select>
                </div>
                
                <div class="control-group">
                    <label>{{ t('trading.timeframe') || '时间周期' }}:</label>
                    <el-select v-model="selectedTimeframe" @change="onTimeframeChange">
                        <el-option label="1分钟" value="1m"></el-option>
                        <el-option label="5分钟" value="5m"></el-option>
                        <el-option label="15分钟" value="15m"></el-option>
                        <el-option label="30分钟" value="30m"></el-option>
                        <el-option label="1小时" value="1h"></el-option>
                    </el-select>
                </div>
                
                <div class="control-group">
                    <el-button @click="refreshChart" :loading="loading">
                        <i class="el-icon-refresh"></i>
                        {{ t('common.refresh') || '刷新' }}
                    </el-button>
                </div>
            </div>
            
            <!-- K线图表 -->
            <div class="chart-wrapper">
                <div ref="chartContainer" class="chart-container" style="width: 100%; height: 500px;"></div>
            </div>
            
            <!-- 订单列表 -->
            <div class="orders-section">
                <h3>{{ t('trading.orderList') || '订单列表' }}</h3>
                <el-table :data="filteredOrders" stripe style="width: 100%" max-height="300">
                    <el-table-column prop="orderid" :label="t('trading.orderId') || '订单号'" width="120"></el-table-column>
                    <el-table-column prop="datetime" :label="t('trading.tradeTime') || '交易时间'" width="160">
                        <template #default="scope">
                            {{ formatDateTime(scope.row.datetime) }}
                        </template>
                    </el-table-column>
                    <el-table-column prop="direction" :label="t('trading.direction') || '方向'" width="80">
                        <template #default="scope">
                            <el-tag :type="scope.row.direction === 'LONG' ? 'success' : 'danger'">
                                {{ scope.row.direction === 'LONG' ? '多' : '空' }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="volume" :label="t('trading.volume') || '手数'" width="80"></el-table-column>
                    <el-table-column prop="symbol" :label="t('trading.symbol') || '品种'" width="100"></el-table-column>
                    <el-table-column prop="price" :label="t('trading.price') || '价格'" width="100">
                        <template #default="scope">
                            {{ scope.row.price?.toFixed(2) || '-' }}
                        </template>
                    </el-table-column>
                    <el-table-column prop="stop_loss" :label="t('trading.stopLoss') || '止损价'" width="100">
                        <template #default="scope">
                            {{ scope.row.stop_loss?.toFixed(2) || '-' }}
                        </template>
                    </el-table-column>
                    <el-table-column prop="take_profit" :label="t('trading.takeProfit') || '止盈价'" width="100">
                        <template #default="scope">
                            {{ scope.row.take_profit?.toFixed(2) || '-' }}
                        </template>
                    </el-table-column>
                    <el-table-column prop="commission" :label="t('trading.commission') || '手续费'" width="100">
                        <template #default="scope">
                            {{ scope.row.commission?.toFixed(2) || '-' }}
                        </template>
                    </el-table-column>
                    <el-table-column prop="status" :label="t('trading.status') || '状态'" width="100">
                        <template #default="scope">
                            <el-tag :type="getStatusType(scope.row.status)">
                                {{ getStatusText(scope.row.status) }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="strategy_name" :label="t('trading.strategy') || '策略'" width="120"></el-table-column>
                </el-table>
            </div>
            
            <!-- 策略绩效 -->
            <div class="performance-section">
                <h3>{{ t('trading.performance') || '策略绩效' }}</h3>
                <div class="performance-cards">
                    <div v-for="(perf, strategyId) in strategyPerformance" :key="strategyId" class="performance-card">
                        <h4>{{ getStrategyName(strategyId) }}</h4>
                        <div class="metrics">
                            <div class="metric">
                                <span class="label">{{ t('trading.totalPnL') || '总盈亏' }}:</span>
                                <span class="value" :class="perf.total_pnl >= 0 ? 'profit' : 'loss'">
                                    {{ perf.total_pnl?.toFixed(2) || '0.00' }}
                                </span>
                            </div>
                            <div class="metric">
                                <span class="label">{{ t('trading.winRate') || '胜率' }}:</span>
                                <span class="value">{{ (perf.win_rate * 100)?.toFixed(1) || '0.0' }}%</span>
                            </div>
                            <div class="metric">
                                <span class="label">{{ t('trading.totalTrades') || '总交易数' }}:</span>
                                <span class="value">{{ perf.total_trades || 0 }}</span>
                            </div>
                            <div class="metric">
                                <span class="label">{{ t('trading.maxDrawdown') || '最大回撤' }}:</span>
                                <span class="value loss">{{ perf.max_drawdown?.toFixed(2) || '0.00' }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    
    setup() {
        const { state, actions } = window.useGlobalState()
        const { t } = window.useI18n()
        
        // 响应式数据
        const chartContainer = Vue.ref(null)
        const chart = Vue.ref(null)
        const loading = Vue.ref(false)
        
        // 图表配置
        const selectedSymbol = Vue.ref('FG509')
        const selectedStrategies = Vue.ref([])
        const selectedTimeframe = Vue.ref('1m')
        const availableSymbols = Vue.ref(['FG509', 'rb2501', 'hc2501', 'i2501', 'j2501', 'fg2501'])
        
        // 数据存储
        const klineData = Vue.ref([])
        const tradingSignals = Vue.ref([])
        const orders = Vue.ref([])
        const strategyPerformance = Vue.ref({})
        
        // 计算属性
        const activeStrategies = Vue.computed(() => {
            return state.strategies.filter(s => s.status === 'running')
        })
        
        const filteredOrders = Vue.computed(() => {
            return orders.value.filter(order => {
                const symbolMatch = !selectedSymbol.value || order.symbol === selectedSymbol.value
                const strategyMatch = selectedStrategies.value.length === 0 || 
                                    selectedStrategies.value.includes(order.strategy_id)
                return symbolMatch && strategyMatch
            })
        })
        
        // 初始化ECharts
        const initChart = () => {
            if (!chartContainer.value) {
                console.warn('图表容器未找到，跳过图表初始化')
                return
            }
            
            // 检查ECharts是否已加载
            if (typeof echarts === 'undefined') {
                console.error('ECharts未加载，请确保已引入ECharts库')
                // 显示错误信息而不是阻塞页面
                chartContainer.value.innerHTML = '<div style="text-align: center; padding: 50px; color: #999;">ECharts库未加载，无法显示图表</div>'
                return
            }
            
            try {
                chart.value = echarts.init(chartContainer.value)
            } catch (error) {
                console.error('ECharts初始化失败:', error)
                chartContainer.value.innerHTML = '<div style="text-align: center; padding: 50px; color: #999;">图表初始化失败</div>'
                return
            }
            
            // 基础配置
            const option = {
                title: {
                    text: `${selectedSymbol.value} - ${selectedTimeframe.value}`,
                    left: 'center'
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'cross'
                    },
                    formatter: function(params) {
                        const data = params[0]
                        if (data && data.data) {
                            // ECharts candlestick数据格式: [open, close, low, high]
                            const [open, close, low, high] = data.data
                            const timeIndex = data.dataIndex
                            const originalData = klineData.value[timeIndex]
                            
                            let time, volume
                            if (Array.isArray(originalData)) {
                                // API返回格式: [timestamp, open, high, low, close, volume]
                                time = new Date(originalData[0]).toLocaleString()
                                volume = originalData[5]
                            } else {
                                // 对象格式
                                time = new Date(originalData.datetime).toLocaleString()
                                volume = originalData.volume
                            }
                            
                            return `
                                时间: ${time}<br/>
                                开盘: ${open}<br/>
                                收盘: ${close}<br/>
                                最低: ${low}<br/>
                                最高: ${high}<br/>
                                成交量: ${volume || '-'}
                            `
                        }
                        return ''
                    }
                },
                legend: {
                    data: ['K线', '买入信号', '卖出信号'],
                    top: 30
                },
                grid: {
                    left: '10%',
                    right: '10%',
                    bottom: '15%'
                },
                xAxis: {
                    type: 'category',
                    data: [],
                    scale: true,
                    boundaryGap: false,
                    axisLine: { onZero: false },
                    splitLine: { show: false },
                    splitNumber: 20,
                    min: 'dataMin',
                    max: 'dataMax'
                },
                yAxis: {
                    scale: true,
                    splitArea: {
                        show: true
                    }
                },
                dataZoom: [
                    {
                        type: 'inside',
                        start: 80,
                        end: 100
                    },
                    {
                        show: true,
                        type: 'slider',
                        top: '90%',
                        start: 80,
                        end: 100
                    }
                ],
                series: [
                    {
                        name: 'K线',
                        type: 'candlestick',
                        data: [],
                        itemStyle: {
                            color: '#ec0000',
                            color0: '#00da3c',
                            borderColor: '#8A0000',
                            borderColor0: '#008F28'
                        }
                    },
                    {
                        name: '买入信号',
                        type: 'scatter',
                        data: [],
                        symbol: 'triangle',
                        symbolSize: 15,
                        itemStyle: {
                            color: '#ff4757'
                        },
                        z: 10
                    },
                    {
                        name: '卖出信号',
                        type: 'scatter',
                        data: [],
                        symbol: 'triangle',
                        symbolRotate: 180,
                        symbolSize: 15,
                        itemStyle: {
                            color: '#2ed573'
                        },
                        z: 10
                    }
                ]
            }
            
            chart.value.setOption(option)
            
            // 窗口大小变化时重新调整图表
            window.addEventListener('resize', () => {
                if (chart.value) {
                    chart.value.resize()
                }
            })
        }
        
        // 更新图表数据
        const updateChart = () => {
            if (!chart.value) return
            
            // 准备K线数据 - API返回格式: [timestamp, open, high, low, close, volume]
            const candlestickData = klineData.value.map(bar => {
                if (Array.isArray(bar)) {
                    // 数组格式: [timestamp, open, high, low, close, volume]
                    const [timestamp, open, high, low, close, volume] = bar
                    return [open, close, low, high]
                } else {
                    // 对象格式
                    return [bar.open, bar.close, bar.low, bar.high]
                }
            })
            
            const timeData = klineData.value.map(bar => {
                if (Array.isArray(bar)) {
                    // 数组格式: [timestamp, open, high, low, close, volume]
                    return new Date(bar[0]).toLocaleTimeString()
                } else {
                    // 对象格式
                    return new Date(bar.datetime).toLocaleTimeString()
                }
            })
            
            // 准备交易信号数据
            const buySignals = []
            const sellSignals = []
            
            tradingSignals.value.forEach(signal => {
                const timeIndex = klineData.value.findIndex(bar => 
                    new Date(bar.datetime).getTime() === new Date(signal.datetime).getTime()
                )
                
                if (timeIndex !== -1) {
                    const signalData = [timeIndex, signal.price]
                    
                    if (signal.direction === 'LONG') {
                        buySignals.push(signalData)
                    } else if (signal.direction === 'SHORT') {
                        sellSignals.push(signalData)
                    }
                }
            })
            
            // 更新图表
            chart.value.setOption({
                title: {
                    text: `${selectedSymbol.value} - ${selectedTimeframe.value}`
                },
                xAxis: {
                    data: timeData
                },
                series: [
                    {
                        name: 'K线',
                        data: candlestickData
                    },
                    {
                        name: '买入信号',
                        data: buySignals
                    },
                    {
                        name: '卖出信号',
                        data: sellSignals
                    }
                ]
            })
        }
        
        // 获取K线数据
        const fetchKlineData = async () => {
            try {
                loading.value = true
                
                // 使用正确的API调用方式
                const response = await window.ApiService.getKlineData(
                    selectedSymbol.value,
                    selectedTimeframe.value,
                    200
                )
                
                if (window.ApiResponse.isSuccess(response)) {
                    const data = window.ApiResponse.getData(response)
                    // 后端返回的数据格式：{symbol, interval, klines: []}
                    klineData.value = data.klines || []
                    console.log('K线数据获取成功:', data.klines?.length || 0, '条数据')
                    updateChart()
                } else {
                    console.warn('K线数据为空或获取失败')
                    // 显示空数据提示
                    if (chart.value) {
                        chart.value.setOption({
                            title: {
                                text: `${selectedSymbol.value} - ${selectedTimeframe.value} (暂无数据)`,
                                subtext: '策略运行中，等待数据生成...'
                            }
                        })
                    }
                }
            } catch (error) {
                console.error('获取K线数据失败:', error)
                window.ElMessage.error('获取K线数据失败')
                // 显示错误提示
                if (chart.value) {
                    chart.value.setOption({
                        title: {
                            text: `${selectedSymbol.value} - ${selectedTimeframe.value} (数据获取失败)`,
                            subtext: '请检查网络连接或稍后重试'
                        }
                    })
                }
            } finally {
                loading.value = false
            }
        }
        
        // 获取交易信号
        const fetchTradingSignals = async () => {
            try {
                const response = await window.ApiService.request(
                    `/api/v1/trading/signals`,
                    {
                        method: 'GET',
                        params: {
                            symbol: selectedSymbol.value,
                            strategies: selectedStrategies.value.join(','),
                            timeframe: selectedTimeframe.value
                        }
                    }
                )
                
                if (window.ApiResponse.isSuccess(response)) {
                    tradingSignals.value = window.ApiResponse.getData(response).signals || []
                    updateChart()
                }
            } catch (error) {
                console.error('获取交易信号失败:', error)
            }
        }
        
        // 获取订单数据
        const fetchOrders = async () => {
            try {
                const response = await window.ApiService.request(
                    `/api/v1/trading/orders`,
                    {
                        method: 'GET',
                        params: {
                            symbol: selectedSymbol.value,
                            strategies: selectedStrategies.value.join(',')
                        }
                    }
                )
                
                if (window.ApiResponse.isSuccess(response)) {
                    orders.value = window.ApiResponse.getData(response).orders || []
                }
            } catch (error) {
                console.error('获取订单数据失败:', error)
            }
        }
        
        // 获取策略绩效
        const fetchStrategyPerformance = async () => {
            try {
                const response = await window.ApiService.request(
                    `/api/v1/trading/performance`,
                    {
                        method: 'GET',
                        params: {
                            strategies: selectedStrategies.value.join(',')
                        }
                    }
                )
                
                if (window.ApiResponse.isSuccess(response)) {
                    strategyPerformance.value = window.ApiResponse.getData(response).performance || {}
                }
            } catch (error) {
                console.error('获取策略绩效失败:', error)
            }
        }
        
        // 刷新图表
        const refreshChart = async () => {
            await Promise.all([
                fetchKlineData(),
                fetchTradingSignals(),
                fetchOrders(),
                fetchStrategyPerformance()
            ])
        }
        
        // 事件处理
        const onSymbolChange = () => {
            refreshChart()
        }
        
        const onStrategyChange = () => {
            fetchTradingSignals()
            fetchOrders()
            fetchStrategyPerformance()
        }
        
        const onTimeframeChange = () => {
            fetchKlineData()
            fetchTradingSignals()
        }
        
        // 工具函数
        const formatDateTime = (datetime) => {
            if (!datetime) return '-'
            return new Date(datetime).toLocaleString()
        }
        
        const getStatusType = (status) => {
            const statusMap = {
                'submitted': 'info',
                'filled': 'success',
                'cancelled': 'warning',
                'rejected': 'danger'
            }
            return statusMap[status] || 'info'
        }
        
        const getStatusText = (status) => {
            const statusMap = {
                'submitted': '已提交',
                'filled': '已成交',
                'cancelled': '已撤销',
                'rejected': '已拒绝'
            }
            return statusMap[status] || status
        }
        
        const getStrategyName = (strategyId) => {
            const strategy = state.strategies.find(s => s.uuid === strategyId)
            return strategy ? strategy.name : strategyId
        }
        
        // WebSocket事件监听
        const setupWebSocketListeners = () => {
            if (window.wsService) {
                // 监听K线数据更新
                window.wsService.on('kline_update', (data) => {
                    if (data.symbol === selectedSymbol.value && data.timeframe === selectedTimeframe.value) {
                        // 更新K线数据
                        const existingIndex = klineData.value.findIndex(bar => 
                            new Date(bar.datetime).getTime() === new Date(data.datetime).getTime()
                        )
                        
                        if (existingIndex !== -1) {
                            klineData.value[existingIndex] = data
                        } else {
                            klineData.value.push(data)
                            // 限制数据长度
                            if (klineData.value.length > 200) {
                                klineData.value = klineData.value.slice(-200)
                            }
                        }
                        
                        updateChart()
                    }
                })
                
                // 监听交易信号
                window.wsService.on('trading_signal', (data) => {
                    if (data.symbol === selectedSymbol.value && 
                        selectedStrategies.value.includes(data.strategy_id)) {
                        tradingSignals.value.push(data)
                        updateChart()
                    }
                })
                
                // 监听订单更新
                window.wsService.on('order_update', (data) => {
                    if (data.symbol === selectedSymbol.value) {
                        const existingIndex = orders.value.findIndex(order => order.orderid === data.orderid)
                        if (existingIndex !== -1) {
                            orders.value[existingIndex] = data
                        } else {
                            orders.value.push(data)
                        }
                    }
                })
            }
        }
        
        // 生命周期
        Vue.onMounted(() => {
            Vue.nextTick(() => {
                try {
                    initChart()
                    refreshChart()
                    setupWebSocketListeners()
                } catch (error) {
                    console.error('TradingChart组件初始化失败:', error)
                    // 不阻塞页面渲染，只记录错误
                }
            })
        })
        
        Vue.onUnmounted(() => {
            if (chart.value) {
                chart.value.dispose()
            }
        })
        
        return {
            // 模板引用
            chartContainer,
            
            // 响应式数据
            loading,
            selectedSymbol,
            selectedStrategies,
            selectedTimeframe,
            availableSymbols,
            
            // 计算属性
            activeStrategies,
            filteredOrders,
            strategyPerformance,
            
            // 方法
            refreshChart,
            onSymbolChange,
            onStrategyChange,
            onTimeframeChange,
            formatDateTime,
            getStatusType,
            getStatusText,
            getStrategyName,
            
            // 国际化
            t
        }
    }
}

// 将组件暴露到全局变量
window.TradingChartComponent = TradingChartComponent
console.log('✅ TradingChartComponent已暴露到全局变量')