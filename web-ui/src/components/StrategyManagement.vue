<template>
  <!-- 策略管理主面板 -->
  <el-card shadow="hover">
    <template #header>
      <div class="card-header">
        <span>策略管理</span>
        <el-button type="primary" size="small" @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </template>
    
    <!-- 策略统计 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="8">
        <el-statistic title="已注册策略" :value="Object.keys(strategyStore.strategies).length">
          <template #prefix>
            <el-icon color="#409eff"><DataAnalysis /></el-icon>
          </template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="运行中" :value="strategyStore.runningCount">
          <template #prefix>
            <el-icon color="#67C23A"><SuccessFilled /></el-icon>
          </template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="已停止" :value="strategyStore.stoppedCount">
          <template #prefix>
            <el-icon color="#909399"><Setting /></el-icon>
          </template>
        </el-statistic>
      </el-col>
    </el-row>
    
    <!-- 策略列表 -->
    <el-table 
      :data="strategyList" 
      style="width: 100%"
      v-loading="strategyStore.isLoading"
    >
      <el-table-column prop="sid" label="策略ID" width="180" />
      <el-table-column prop="module" label="模块路径" min-width="200" />
      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-tag :type="getStrategyStatus(scope.row.sid) === '运行中' ? 'success' : 'info'">
            {{ getStrategyStatus(scope.row.sid) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="scope">
          <el-switch
            :model-value="scope.row.enabled"
            @change="handleToggleEnabled(scope.row.sid, $event)"
          />
        </template>
      </el-table-column>
      <el-table-column label="PID" width="100">
        <template #default="scope">
          {{ getStrategyPID(scope.row.sid) || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="scope">
          <el-button
            v-if="getStrategyStatus(scope.row.sid) === '已停止'"
            size="small"
            type="success"
            @click="handleStartStrategy(scope.row.sid)"
          >
            启动
          </el-button>
          <el-button
            v-if="getStrategyStatus(scope.row.sid) === '运行中'"
            size="small"
            type="warning"
            @click="handleStopStrategy(scope.row.sid)"
          >
            停止
          </el-button>
          <el-button
            v-if="getStrategyStatus(scope.row.sid) === '运行中'"
            size="small"
            type="primary"
            @click="handleReloadStrategy(scope.row.sid)"
          >
            重载
          </el-button>
          <el-button 
            size="small" 
            @click="handleShowDetail(scope.row)"
          >
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 实时日志 -->
  <el-card shadow="hover" style="margin-top: 20px;">
    <template #header>
      <div class="card-header">
        <span>实时日志</span>
        <div>
          <el-select 
            v-model="selectedLogType" 
            placeholder="筛选日志类型" 
            size="small" 
            style="width: 150px; margin-right: 10px;"
            clearable
          >
            <el-option label="全部" value="" />
            <el-option label="日志(log)" value="log" />
            <el-option label="错误(error)" value="error" />
            <el-option label="状态(status)" value="status" />
          </el-select>
          <el-button size="small" @click="strategyStore.clearMessages">清空</el-button>
        </div>
      </div>
    </template>
    <div class="log-container">
      <el-timeline v-if="filteredMessages.length > 0">
        <el-timeline-item 
          v-for="(msg, index) in filteredMessages.slice(-50)" 
          :key="index"
          :timestamp="msg.displayTime || msg.timestamp"
          placement="top"
        >
          <div class="log-item">
            <el-tag 
              :type="getLogTypeColor(msg.type)" 
              size="small" 
              style="margin-right: 8px;"
            >
              [{{ msg.sid }}]
            </el-tag>
            <el-tag 
              :type="getLogTypeColor(msg.type)" 
              size="small" 
              style="margin-right: 8px;"
            >
              {{ msg.type }}
            </el-tag>
            <span class="log-message">{{ msg.payload }}</span>
            <div v-if="msg.trace" class="log-trace">
              <pre>{{ msg.trace }}</pre>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无日志记录" />
    </div>
  </el-card>

  <!-- 策略详情抽屉 -->
  <el-drawer
    v-model="detailDrawerVisible"
    :title="`策略详情 - ${currentStrategy?.sid || ''}`"
    size="60%"
    direction="rtl"
  >
    <div v-if="currentStrategy" class="strategy-detail">
      <!-- 基础信息 -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <span class="section-title">基础信息</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="策略ID">{{ currentStrategy.sid }}</el-descriptions-item>
          <el-descriptions-item label="模块路径">{{ currentStrategy.module }}</el-descriptions-item>
          <el-descriptions-item label="类名">{{ currentStrategy.class }}</el-descriptions-item>
          <el-descriptions-item label="文件路径">{{ currentStrategy.file }}</el-descriptions-item>
          <el-descriptions-item label="是否启用" :span="2">
            <el-tag :type="currentStrategy.enabled ? 'success' : 'info'">
              {{ currentStrategy.enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="参数配置" :span="2">
            <pre>{{ JSON.stringify(currentStrategy.params, null, 2) }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 运行状态 -->
      <el-card shadow="never" class="detail-section" v-if="currentStrategyStatus">
        <template #header>
          <span class="section-title">运行状态</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="进程ID">{{ currentStrategyStatus.pid || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运行状态">
            <el-tag :type="currentStrategyStatus.alive ? 'success' : 'info'">
              {{ currentStrategyStatus.alive ? '运行中' : '已停止' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 占位：持仓/委托/成交信息（待对接交易网关） -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <span class="section-title">交易信息</span>
        </template>
        <el-alert
          title="提示"
          type="info"
          description="持仓、委托、成交数据需要对接交易网关后才能显示"
          :closable="false"
        />
      </el-card>
    </div>
  </el-drawer>
</template>

<script setup>
import {
  DataAnalysis, SuccessFilled, Setting, Refresh
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useStrategyStore } from '@/stores/strategy'

// ========== 初始化 ==========
const strategyStore = useStrategyStore()

// ========== 状态 ==========
const detailDrawerVisible = ref(false)
const currentStrategy = ref(null)
const selectedLogType = ref('')

// ========== 计算属性 ==========
const strategyList = computed(() => {
  return Object.entries(strategyStore.strategies).map(([sid, config]) => ({
    sid,
    ...config
  }))
})

const currentStrategyStatus = computed(() => {
  if (!currentStrategy.value) return null
  return strategyStore.strategyStatus[currentStrategy.value.sid]
})

const filteredMessages = computed(() => {
  if (!selectedLogType.value) {
    return strategyStore.messages
  }
  return strategyStore.messages.filter(msg => msg.type === selectedLogType.value)
})

// ========== 工具方法 ==========
function getStrategyStatus(sid) {
  const status = strategyStore.strategyStatus[sid]
  return status && status.alive ? '运行中' : '已停止'
}

function getStrategyPID(sid) {
  const status = strategyStore.strategyStatus[sid]
  return status ? status.pid : null
}

function getLogTypeColor(type) {
  const colorMap = {
    log: '',
    error: 'danger',
    status: 'warning',
    stopped: 'info'
  }
  return colorMap[type] || ''
}

// ========== 事件处理 ==========
async function handleRefresh() {
  await Promise.all([
    strategyStore.fetchStrategies(),
    strategyStore.fetchStatus()
  ])
  ElMessage.success('刷新成功')
}

async function handleStartStrategy(sid) {
  await strategyStore.start(sid)
}

async function handleStopStrategy(sid) {
  try {
    await ElMessageBox.confirm(
      `确认停止策略 ${sid}？`,
      '停止确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await strategyStore.stop(sid)
  } catch {
    ElMessage.info('已取消')
  }
}

async function handleReloadStrategy(sid) {
  try {
    await ElMessageBox.confirm(
      `确认重载策略 ${sid}？\n重载会保存状态、重启进程、恢复状态`,
      '重载确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await strategyStore.reload(sid)
  } catch {
    ElMessage.info('已取消')
  }
}

async function handleToggleEnabled(sid, enabled) {
  if (enabled) {
    await strategyStore.enable(sid)
  } else {
    await strategyStore.disable(sid)
  }
}

function handleShowDetail(row) {
  currentStrategy.value = row
  detailDrawerVisible.value = true
}

// ========== 生命周期 ==========
onMounted(async () => {
  // 加载策略列表和状态
  await Promise.all([
    strategyStore.fetchStrategies(),
    strategyStore.fetchStatus()
  ])
  
  // 连接WebSocket
  strategyStore.connectWebSocket()
  
  // 定时刷新状态（每5秒）
  const intervalId = setInterval(() => {
    strategyStore.fetchStatus()
  }, 5000)
  
  // 保存定时器ID用于清理
  onUnmounted(() => {
    clearInterval(intervalId)
    strategyStore.disconnectWebSocket()
  })
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-container {
  max-height: 500px;
  overflow-y: auto;
}

.log-item {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
}

.log-message {
  color: #606266;
  font-size: 14px;
  flex: 1;
}

.log-trace {
  width: 100%;
  margin-top: 8px;
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  overflow-x: auto;
}

.log-trace pre {
  margin: 0;
  font-size: 12px;
  color: #e74c3c;
}

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
</style>
