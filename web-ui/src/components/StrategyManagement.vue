<template>
  <!-- 策略管理主面板 -->
  <el-card shadow="hover">
    <template #header>
      <div class="card-header">
        <span>策略管理</span>
        <el-button type="primary" size="small" @click="addStrategyDialogVisible = true">加载策略</el-button>
      </div>
    </template>
    <!-- 策略统计 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="8">
        <el-statistic title="活跃策略" :value="activeStrategiesCount">
          <template #prefix>
            <el-icon color="#409eff"><DataAnalysis /></el-icon>
          </template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="运行中" :value="runningStrategiesCount">
          <template #prefix>
            <el-icon color="#67C23A"><SuccessFilled /></el-icon>
          </template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="已停止" :value="stoppedStrategiesCount">
          <template #prefix>
            <el-icon color="#909399"><Setting /></el-icon>
          </template>
        </el-statistic>
      </el-col>
    </el-row>
    <el-table :data="strategies" style="width: 100%">
      <el-table-column prop="id" label="策略ID" width="100" />
      <el-table-column prop="name" label="策略名称" />
      <el-table-column label="浮动盈亏" width="120">
        <template #default="scope">
          <span :style="{ color: getTotalProfitLoss(scope.row) > 0 ? '#F56C6C' : getTotalProfitLoss(scope.row) < 0 ? '#67C23A' : '#000000' }">
            {{ getTotalProfitLoss(scope.row) > 0 ? '+' : '' }}{{ getTotalProfitLoss(scope.row).toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="交易次数" width="100">
        <template #default="scope">
          {{ scope.row.positions.length }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.status === '运行中' ? 'success' : 'info'">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="startTime" label="启动时间" width="180" />
      <el-table-column prop="runningTime" label="运行时长" width="120" />
      <el-table-column label="操作" width="220">
        <template #default="scope">
          <el-button
            v-if="scope.row.status === '已停止'"
            size="small"
            type="success"
            @click="handleStartStrategy(scope.row)"
          >
            启动
          </el-button>
          <el-button
            v-if="scope.row.status === '运行中'"
            size="small"
            type="warning"
            @click="handleStopStrategy(scope.row)"
          >
            停止
          </el-button>
          <el-button size="small" type="primary" @click="handleShowDetail(scope.row)">详情</el-button>
          <el-button size="small" type="danger" @click="handleDeleteStrategy(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 操作日志 -->
  <el-card shadow="hover" style="margin-top: 20px;">
    <template #header>
      <div class="card-header">
        <span>操作日志</span>
        <el-select 
          v-model="selectedLogLevel" 
          placeholder="选择日志级别" 
          size="small" 
          style="width: 150px;"
        >
          <el-option label="全部" value="all" />
          <el-option label="信息" value="info" />
          <el-option label="成功" value="success" />
          <el-option label="警告" value="warning" />
          <el-option label="错误" value="error" />
        </el-select>
      </div>
    </template>
    <div class="log-container">
      <el-timeline v-if="filteredStrategyLogs.length > 0">
        <el-timeline-item 
          v-for="log in filteredStrategyLogs" 
          :key="log.id"
          :timestamp="log.timestamp"
          placement="top"
        >
          <div class="log-item">
            <el-tag 
              :type="logLevelMap[log.level].color" 
              size="small" 
              style="margin-right: 8px;"
            >
              {{ log.category }}
            </el-tag>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无日志记录" />
    </div>
  </el-card>

  <!-- 策略详情面板 -->
  <el-drawer
    v-model="detailDrawerVisible"
    :title="`策略详情 - ${currentStrategy?.name || ''}`"
    size="70%"
    direction="rtl"
  >
    <div v-if="currentStrategy" class="strategy-detail">
      <!-- 1. 基础信息 -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <span class="section-title">基础信息</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="策略名称">{{ currentStrategy.name }}</el-descriptions-item>
          <el-descriptions-item label="策略ID">{{ currentStrategy.id }}</el-descriptions-item>
          <el-descriptions-item label="作者">{{ currentStrategy.author }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentStrategy.createTime }}</el-descriptions-item>
          <el-descriptions-item label="最后修改时间" :span="2">{{ currentStrategy.lastModifyTime }}</el-descriptions-item>
          <el-descriptions-item label="策略描述" :span="2">{{ currentStrategy.description }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 2. 持仓信息 -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <span class="section-title">持仓</span>
        </template>
        <el-table :data="currentStrategy.positions" border stripe>
          <el-table-column prop="contract" label="合约" width="80" />
          <el-table-column prop="direction" label="多空" width="60">
            <template #default="scope">
              <el-tag :type="scope.row.direction === '多' ? 'danger' : 'success'">
                {{ scope.row.direction }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="volume" label="总仓" width="60" />
          <el-table-column prop="available" label="可用" width="60" />
          <el-table-column prop="holdPrice" label="开仓均价" width="100">
            <template #default="scope">
              {{ scope.row.holdPrice.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="latestPrice" label="当前价格" width="100">
            <template #default="scope">
              {{ scope.row.latestPrice.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="profitLoss" label="逐笔浮盈" width="100">
            <template #default="scope">
              <span :style="{ color: scope.row.profitLoss > 0 ? '#F56C6C' : scope.row.profitLoss < 0 ? '#67C23A' : '#000000' }">
                {{ scope.row.profitLoss > 0 ? '+' : '' }}{{ scope.row.profitLoss.toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="priceDiff" label="盈利价差" width="90">
            <template #default="scope">
              <span :style="{ color: scope.row.priceDiff > 0 ? '#F56C6C' : scope.row.priceDiff < 0 ? '#67C23A' : '#000000' }">
                {{ scope.row.priceDiff > 0 ? '+' : '' }}{{ scope.row.priceDiff.toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="returnRate" label="浮盈比例" width="90">
            <template #default="scope">
              <span :style="{ color: scope.row.returnRate > 0 ? '#F56C6C' : scope.row.returnRate < 0 ? '#67C23A' : '#000000' }">
                {{ scope.row.returnRate > 0 ? '+' : '' }}{{ scope.row.returnRate.toFixed(2) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="margin" label="保证金" width="90">
            <template #default="scope">
              {{ scope.row.margin.toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column prop="marketValue" label="市值" width="100">
            <template #default="scope">
              {{ scope.row.marketValue.toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column prop="markToMarketPL" label="盯市浮盈" width="100">
            <template #default="scope">
              <span :style="{ color: scope.row.markToMarketPL > 0 ? '#F56C6C' : scope.row.markToMarketPL < 0 ? '#67C23A' : '#000000' }">
                {{ scope.row.markToMarketPL > 0 ? '+' : '' }}{{ scope.row.markToMarketPL.toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="takeProfitPrice" label="止盈价" width="100">
            <template #default="scope">
              {{ scope.row.takeProfitPrice.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="stopLossPrice" label="止损价" width="100">
            <template #default="scope">
              {{ scope.row.stopLossPrice.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="scope">
              <el-button size="small" type="danger" @click="handleClosePosition(scope.row)">
                一键平仓
              </el-button>
              <el-button size="small" type="warning" @click="handlePartialClose(scope.row)">
                部分平仓
              </el-button>
              <el-button size="small" type="primary" @click="handleReversePosition(scope.row)">
                反手开仓
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 3. 委托 -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <span class="section-title">委托</span>
        </template>
        <el-table :data="currentStrategy.orders" border stripe>
          <!-- 1. 合约 -->
          <el-table-column prop="contract" label="合约" width="80" />
          <!-- 2. 状态 -->
          <el-table-column prop="status" label="状态" width="80">
            <template #default="scope">
              <el-tag :type="orderStatusMap[scope.row.status].color" size="small">
                {{ orderStatusMap[scope.row.status].name }}
              </el-tag>
            </template>
          </el-table-column>
          <!-- 3. 多空 -->
          <el-table-column prop="direction" label="多空" width="60">
            <template #default="scope">
              <el-tag :type="scope.row.direction === '买' ? 'danger' : 'success'" size="small">
                {{ scope.row.direction === '买' ? '多' : '空' }}
              </el-tag>
            </template>
          </el-table-column>
          <!-- 4. 开平 -->
          <el-table-column prop="offset" label="开平" width="60">
            <template #default="scope">
              <el-tag :type="scope.row.offset === '开仓' ? 'primary' : 'warning'" size="small">
                {{ scope.row.offset === '开仓' ? '开' : '平' }}
              </el-tag>
            </template>
          </el-table-column>
          <!-- 5. 委托价 -->
          <el-table-column prop="orderPrice" label="委托价" width="80">
            <template #default="scope">
              {{ scope.row.orderPrice.toFixed(2) }}
            </template>
          </el-table-column>
          <!-- 6. 委托量 -->
          <el-table-column prop="orderVolume" label="委托量" width="70" />
          <!-- 7. 已成交 -->
          <el-table-column prop="filledVolume" label="已成交" width="70" />
          <!-- 8. 可撤 -->
          <el-table-column prop="cancelableVolume" label="可撤" width="60">
            <template #default="scope">
              {{ scope.row.cancelableVolume || 0 }}
            </template>
          </el-table-column>
          <!-- 9. 成交价 -->
          <el-table-column prop="avgPrice" label="成交价" width="80">
            <template #default="scope">
              {{ scope.row.avgPrice ? scope.row.avgPrice.toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <!-- 10. 时间 -->
          <el-table-column prop="orderTime" label="时间" width="160" />
          <!-- 操作 -->
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="scope">
              <el-button 
                v-if="scope.row.status === 'submitted' || scope.row.status === 'partiallyFilled'"
                size="small" 
                type="warning"
                @click="handleCancelOrder(scope.row)"
              >
                撤单
              </el-button>
              <el-button 
                v-if="scope.row.status === 'submitted' || scope.row.status === 'partiallyFilled'"
                size="small" 
                type="primary"
                @click="handleModifyOrder(scope.row)"
              >
                修改
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 4. 成交明细 -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <span class="section-title">成交明细</span>
        </template>
        <el-table :data="currentStrategy.trades" border stripe>
          <el-table-column prop="tradeTime" label="成交时间" width="160" />
          <el-table-column prop="contract" label="合约代码" width="100" />
          <el-table-column prop="direction" label="买卖方向" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.direction === '买' ? 'danger' : 'success'">
                {{ scope.row.direction }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="offset" label="开平仓" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.offset === '开仓' ? 'warning' : 'info'">
                {{ scope.row.offset }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="tradePrice" label="成交价格" width="100">
            <template #default="scope">
              {{ scope.row.tradePrice.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="tradeVolume" label="成交数量" width="80" />
          <el-table-column prop="tradeId" label="成交编号" width="180" />
          <el-table-column prop="commission" label="手续费" width="100">
            <template #default="scope">
              {{ scope.row.commission.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="tradeType" label="成交类型" width="120">
            <template #default="scope">
              <el-tag :type="tradeTypeMap[scope.row.tradeType].color">
                {{ tradeTypeMap[scope.row.tradeType].name }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 5. 风险控制 -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <span class="section-title">风险控制</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="最大仓位">{{ currentStrategy.riskControl.maxPosition }} 手</el-descriptions-item>
          <el-descriptions-item label="止损比例">{{ currentStrategy.riskControl.stopLossRatio }}%</el-descriptions-item>
          <el-descriptions-item label="止盈比例">{{ currentStrategy.riskControl.takeProfitRatio }}%</el-descriptions-item>
          <el-descriptions-item label="最大回撤">{{ currentStrategy.riskControl.maxDrawdown }}%</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 6. 风险控制参数配置 -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <div class="section-header">
            <span class="section-title">风险控制参数配置</span>
            <div>
              <el-button size="small" @click="handleCancelEdit">取消</el-button>
              <el-button size="small" type="primary" @click="handleSaveParameters">保存</el-button>
            </div>
          </div>
        </template>
        
        <el-form :model="editableParameters" label-width="140px">
          <!-- 风险参数 -->
          <el-divider content-position="left">风险参数</el-divider>
          <el-form-item label="最大仓位（手）">
            <el-input-number v-model="editableParameters.riskControl.maxPosition" :min="1" :max="200" />
          </el-form-item>
          <el-form-item label="止损比例（%）">
            <el-input-number v-model="editableParameters.riskControl.stopLossRatio" :min="0.1" :max="10" :step="0.1" :precision="1" />
          </el-form-item>
          <el-form-item label="止盈比例（%）">
            <el-input-number v-model="editableParameters.riskControl.takeProfitRatio" :min="0.1" :max="20" :step="0.1" :precision="1" />
          </el-form-item>
          <el-form-item label="最大回撤（%）">
            <el-input-number v-model="editableParameters.riskControl.maxDrawdown" :min="1" :max="50" :step="1" :precision="1" />
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </el-drawer>

  <!-- 加载策略对话框 -->
  <el-dialog
    v-model="addStrategyDialogVisible"
    title="选择要加载的策略"
    width="80%"
    :close-on-click-modal="false"
  >
    <el-row :gutter="20">
      <el-col :span="24" v-for="template in strategyTemplates" :key="template.fileName" style="margin-bottom: 20px;">
        <el-card class="strategy-card" shadow="hover">
          <!-- 文件名 -->
          <div class="strategy-file-name">
            <el-icon :size="18" color="#409eff"><Document /></el-icon>
            <span style="margin-left: 8px; font-family: 'Courier New', monospace; color: #606266;">{{ template.fileName }}</span>
          </div>
          
          <!-- 策略名称 -->
          <h3 style="margin: 15px 0 10px 0; font-size: 18px; color: #303133;">{{ template.name }}</h3>
          
          <!-- 策略描述 -->
          <p class="strategy-description">{{ template.description }}</p>
          
          <!-- 默认参数预览 -->
          <div class="strategy-params">
            <el-tag size="small" style="margin-right: 8px;">最大仓位: {{ template.defaultRiskControl.maxPosition }}</el-tag>
            <el-tag size="small" type="warning" style="margin-right: 8px;">止损: {{ template.defaultRiskControl.stopLossRatio }}%</el-tag>
            <el-tag size="small" type="success" style="margin-right: 8px;">止盈: {{ template.defaultRiskControl.takeProfitRatio }}%</el-tag>
            <el-tag size="small" type="info">回撤: {{ template.defaultRiskControl.maxDrawdown }}%</el-tag>
          </div>
          
          <!-- 加载按钮 -->
          <el-button type="primary" style="width: 100%; margin-top: 15px;" @click="handleAddStrategy(template)">
            <el-icon style="margin-right: 5px;"><Plus /></el-icon>
            加载此策略
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </el-dialog>
</template>

<script setup>
import {
  DataAnalysis, SuccessFilled, Setting, Plus, Document
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { logLevelMap, orderStatusMap, orderTypeMap, tradeTypeMap } from '@/constants'
import { getTotalProfitLoss } from '@/utils'
import { strategyTemplates } from '@/mock'
import { useStrategyManagement } from '@/composables'

const {
  strategies,
  strategyLogs,
  selectedLogLevel,
  detailDrawerVisible,
  currentStrategy,
  addStrategyDialogVisible,
  editableParameters,
  activeStrategiesCount,
  runningStrategiesCount,
  stoppedStrategiesCount,
  filteredStrategyLogs,
  handleAddStrategy,
  handleStartStrategy,
  handleStopStrategy,
  handleDeleteStrategy,
  handleShowDetail,
  handleSaveParameters,
  handleCancelEdit
} = useStrategyManagement()

/**
 * 一键平仓处理
 */
const handleClosePosition = (position) => {
  ElMessageBox.confirm(
    `确认平仓？\n合约：${position.contract}\n多空：${position.direction}\n总仓：${position.volume} 手\n当前价格：${position.latestPrice.toFixed(2)}\n预计盈亏：${position.profitLoss > 0 ? '+' : ''}${position.profitLoss.toFixed(2)}`,
    '一键平仓确认',
    {
      confirmButtonText: '确认平仓',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: false
    }
  ).then(() => {
    // TODO: 调用API执行平仓操作
    console.log('一键平仓:', position)
    ElMessage.success('平仓指令已提交')
    
    // 模拟平仓后移除持仓
    // 实际应用中应该等待后端返回确认
  }).catch(() => {
    ElMessage.info('已取消平仓操作')
  })
}

/**
 * 部分平仓处理
 */
const handlePartialClose = (position) => {
  ElMessageBox.prompt(
    `当前总仓：${position.volume} 手\n请输入平仓数量（1-${position.volume}）`,
    '部分平仓',
    {
      confirmButtonText: '确认平仓',
      cancelButtonText: '取消',
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入有效的整数',
      inputPlaceholder: '请输入平仓数量',
      inputValidator: (value) => {
        const num = parseInt(value)
        if (num < 1 || num > position.volume) {
          return `平仓数量必须在 1 到 ${position.volume} 之间`
        }
        return true
      }
    }
  ).then(({ value }) => {
    // TODO: 调用API执行部分平仓操作
    console.log('部分平仓:', position, '数量:', value)
    ElMessage.success(`已提交平仓 ${value} 手的指令`)
    
    // 模拟部分平仓后更新持仓量
    // 实际应用中应该等待后端返回确认
  }).catch(() => {
    ElMessage.info('已取消平仓操作')
  })
}

/**
 * 反手开仓处理
 */
const handleReversePosition = (position) => {
  const reverseDirection = position.direction === '多' ? '空' : '多'
  ElMessageBox.confirm(
    `确认反手开仓？\n当前持仓：${position.contract} ${position.direction} ${position.volume} 手\n操作说明：\n1. 平掉当前 ${position.direction} 仓 ${position.volume} 手\n2. 开立 ${reverseDirection} 仓 ${position.volume} 手`,
    '反手开仓确认',
    {
      confirmButtonText: '确认反手',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: false
    }
  ).then(() => {
    // TODO: 调用API执行反手操作
    console.log('反手开仓:', position, '新方向:', reverseDirection)
    ElMessage.success('反手操作指令已提交')
    
    // 模拟反手后更新持仓方向
    // 实际应用中应该等待后端返回确认
  }).catch(() => {
    ElMessage.info('已取消反手操作')
  })
}

/**
 * 撤单处理
 */
const handleCancelOrder = (order) => {
  ElMessageBox.confirm(
    `确认撤销委托？合约：${order.contract}，方向：${order.direction}，数量：${order.orderVolume}`,
    '撤单确认',
    {
      confirmButtonText: '确认撤单',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // TODO: 调用API撤销委托
    console.log('撤销委托:', order)
    ElMessage.success('委托已撤销')
    
    // 更新委托状态为已撤单
    order.status = 'cancelled'
  }).catch(() => {
    ElMessage.info('已取消操作')
  })
}

/**
 * 修改委托处理
 */
const handleModifyOrder = (order) => {
  ElMessageBox.prompt(
    `当前委托价格：${order.orderPrice}，委托数量：${order.orderVolume}`,
    '修改委托',
    {
      confirmButtonText: '确认修改',
      cancelButtonText: '取消',
      inputPattern: /^\d+(\.\d+)?$/,
      inputErrorMessage: '请输入有效的数字',
      inputPlaceholder: '请输入新的委托价格'
    }
  ).then(({ value }) => {
    // TODO: 调用API修改委托
    console.log('修改委托:', order, '新价格:', value)
    ElMessage.success(`委托价格已修改为 ${value}`)
    
    // 更新委托价格
    order.orderPrice = parseFloat(value)
  }).catch(() => {
    ElMessage.info('已取消操作')
  })
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-container {
  max-height: 400px;
  overflow-y: auto;
}

.log-item {
  display: flex;
  align-items: center;
}

.log-message {
  color: #606266;
  font-size: 14px;
}

/* 策略详情面板样式 */
.strategy-detail {
  padding: 0 20px 20px;
}

.detail-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 持仓表格紧凑布局 */
.detail-section :deep(.el-table) {
  font-size: 13px;
}

/* 表单项间距 */
.detail-section :deep(.el-form-item) {
  margin-bottom: 18px;
}

/* 分割线样式 */
.detail-section :deep(.el-divider__text) {
  font-weight: 600;
  color: #606266;
}

.strategy-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.strategy-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.strategy-file-name {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 10px;
}

.strategy-description {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  margin: 10px 0;
  min-height: 44px;
}

.strategy-params {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}
</style>

