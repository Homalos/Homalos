<template>
  <div>
    <!-- 1. 系统控制 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <!-- 交易核心 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>交易核心</span>
              <el-tag :type="getCoreStatusType(consoleData.tradingCore.status)">
                {{ getCoreStatusText(consoleData.tradingCore.status) }}
              </el-tag>
            </div>
          </template>
          <div style="padding: 20px 0;">
            <!-- 基础状态 -->
            <el-row :gutter="20" style="margin-bottom: 20px;">
              <el-col :span="8">
                <div class="custom-statistic">
                  <div class="statistic-title">核心状态</div>
                  <div class="statistic-content">
                    <el-icon :color="getCoreStatusColor(consoleData.tradingCore.status)" class="statistic-icon">
                      <SuccessFilled v-if="consoleData.tradingCore.status === 'running'" />
                      <Loading v-else-if="consoleData.tradingCore.status === 'initializing' || consoleData.tradingCore.status === 'connecting'" />
                      <VideoPause v-else />
                    </el-icon>
                    <span 
                      class="statistic-value" 
                      :style="{ color: getCoreStatusColor(consoleData.tradingCore.status) }"
                    >
                      {{ getCoreStatusText(consoleData.tradingCore.status) }}
                    </span>
                  </div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="custom-statistic">
                  <div class="statistic-title">运行时长</div>
                  <div class="statistic-content">
                    <el-icon color="#409EFF" class="statistic-icon"><Clock /></el-icon>
                    <span class="statistic-value">
                      {{ consoleData.tradingCore.runningTime }}
                    </span>
                  </div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="custom-statistic">
                  <div class="statistic-title">网关状态</div>
                  <div class="statistic-content">
                    <el-icon :color="isGatewayConnected ? '#67C23A' : '#909399'" class="statistic-icon">
                      <Connection v-if="isGatewayConnected" />
                      <SwitchButton v-else />
                    </el-icon>
                    <span 
                      class="statistic-value" 
                      :style="{ color: isGatewayConnected ? '#67C23A' : '#909399' }"
                    >
                      {{ isGatewayConnected ? '已连接' : '未连接' }}
                    </span>
                  </div>
                </div>
              </el-col>
            </el-row>
            
            <!-- 网关详细状态（始终显示）-->
            <el-row :gutter="10" style="margin-bottom: 20px;">
              <el-col :span="6">
                <el-tag :type="consoleData.tradingCore.gateway.md_login ? 'success' : 'info'" size="small">
                  行情网关: {{ consoleData.tradingCore.gateway.md_login ? '✓' : '✗' }}
                </el-tag>
              </el-col>
              <el-col :span="6">
                <el-tag :type="consoleData.tradingCore.gateway.td_login ? 'success' : 'info'" size="small">
                  交易网关: {{ consoleData.tradingCore.gateway.td_login ? '✓' : '✗' }}
                </el-tag>
              </el-col>
              <el-col :span="6">
                <el-tag :type="consoleData.tradingCore.gateway.td_confirm ? 'success' : 'info'" size="small">
                  结算确认: {{ consoleData.tradingCore.gateway.td_confirm ? '✓' : '✗' }}
                </el-tag>
              </el-col>
              <el-col :span="6">
                <el-tag :type="consoleData.tradingCore.gateway.instruments_loaded ? 'success' : 'info'" size="small">
                  合约加载: {{ consoleData.tradingCore.gateway.instruments_loaded ? '✓' : '✗' }}
                </el-tag>
              </el-col>
            </el-row>
            
            <!-- 控制按钮 -->
            <el-row :gutter="10" style="margin-bottom: 10px;">
              <el-col :span="12">
                <el-button 
                  type="success" 
                  style="width: 100%;"
                  :disabled="consoleData.tradingCore.status !== 'stopped'"
                  :loading="consoleData.tradingCore.status === 'initializing'"
                  @click="handleStartTradingCore(true)"
                >
                  <el-icon><VideoPlay /></el-icon>
                  启动核心(自动连接)
                </el-button>
              </el-col>
              <el-col :span="12">
                <el-button 
                  type="danger" 
                  style="width: 100%;"
                  :disabled="consoleData.tradingCore.status === 'stopped'"
                  :loading="consoleData.tradingCore.status === 'stopping'"
                  @click="handleStopTradingCore"
                >
                  <el-icon><VideoPause /></el-icon>
                  停止核心
                </el-button>
              </el-col>
            </el-row>
            
            <!-- 网关控制按钮 -->
            <el-row :gutter="10" v-if="consoleData.tradingCore.status === 'running'">
              <el-col :span="12">
                <el-button 
                  type="primary" 
                  style="width: 100%;"
                  :disabled="isGatewayConnected"
                  @click="handleConnectGateway"
                >
                  <el-icon><Connection /></el-icon>
                  连接网关
                </el-button>
              </el-col>
              <el-col :span="12">
                <el-button 
                  type="warning" 
                  style="width: 100%;"
                  :disabled="!isGatewayConnected"
                  @click="handleDisconnectGateway"
                >
                  <el-icon><SwitchButton /></el-icon>
                  断开网关
                </el-button>
              </el-col>
            </el-row>
            
            <!-- 状态消息 -->
            <el-alert 
              v-if="consoleData.tradingCore.message"
              :title="consoleData.tradingCore.message"
              :type="getAlertType(consoleData.tradingCore.status)"
              :closable="false"
              style="margin-top: 15px;"
            />
          </div>
        </el-card>
      </el-col>

      <!-- 数据中心 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>数据中心</span>
              <el-tag :type="consoleData.dataCenter.status === 'running' ? 'success' : 'info'">
                {{ consoleData.dataCenter.status === 'running' ? '运行中' : '已停止' }}
              </el-tag>
            </div>
          </template>
          <div style="padding: 20px 0;">
            <!-- 基础状态 -->
            <el-row :gutter="20" style="margin-bottom: 20px;">
              <el-col :span="8">
                <div class="custom-statistic">
                  <div class="statistic-title">系统状态</div>
                  <div class="statistic-content">
                    <el-icon :color="consoleData.dataCenter.status === 'running' ? '#67C23A' : '#909399'" class="statistic-icon">
                      <SuccessFilled v-if="consoleData.dataCenter.status === 'running'" />
                      <VideoPause v-else />
                    </el-icon>
                    <span 
                      class="statistic-value" 
                      :style="{ color: consoleData.dataCenter.status === 'running' ? '#67C23A' : '#909399' }"
                    >
                      {{ consoleData.dataCenter.status === 'running' ? '运行中' : '已停止' }}
                    </span>
                  </div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="custom-statistic">
                  <div class="statistic-title">进程ID</div>
                  <div class="statistic-content">
                    <el-icon color="#409EFF" class="statistic-icon"><Document /></el-icon>
                    <span class="statistic-value">
                      {{ consoleData.dataCenter.pid || 0 }}
                    </span>
                  </div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="custom-statistic">
                  <div class="statistic-title">运行时长</div>
                  <div class="statistic-content">
                    <el-icon color="#409EFF" class="statistic-icon"><Clock /></el-icon>
                    <span class="statistic-value">
                      {{ consoleData.dataCenter.runningTime }}
                    </span>
                  </div>
                </div>
              </el-col>
            </el-row>
            
            <!-- 资源使用情况 -->
            <el-row :gutter="20" style="margin-bottom: 20px;" v-if="consoleData.dataCenter.status === 'running'">
              <el-col :span="12">
                <el-statistic title="CPU使用率" :value="consoleData.dataCenter.cpu" :precision="2" suffix="%">
                  <template #prefix>
                    <el-icon color="#E6A23C"><Cpu /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="12">
                <el-statistic title="内存使用" :value="consoleData.dataCenter.memory" :precision="2" suffix="MB">
                  <template #prefix>
                    <el-icon color="#F56C6C"><Memo /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
            </el-row>
            
            <!-- 控制按钮 -->
            <el-row :gutter="10">
              <el-col :span="12">
                <el-button 
                  type="success" 
                  style="width: 100%;"
                  :disabled="consoleData.dataCenter.status === 'running'"
                  @click="handleStartDataCenter"
                >
                  <el-icon><VideoPlay /></el-icon>
                  启动数据中心
                </el-button>
              </el-col>
              <el-col :span="12">
                <el-button 
                  type="danger" 
                  style="width: 100%;"
                  :disabled="consoleData.dataCenter.status === 'stopped'"
                  @click="handleStopDataCenter"
                >
                  <el-icon><VideoPause /></el-icon>
                  停止数据中心
                </el-button>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 2. 控制台日志 -->
    <el-row :gutter="20">
      <!-- 交易核心日志 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>交易核心日志</span>
              <el-select 
                v-model="selectedTradingCoreLogLevel" 
                placeholder="选择日志级别" 
                size="small" 
                style="width: 120px;"
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
            <el-timeline v-if="filteredTradingCoreLogs.length > 0">
              <el-timeline-item 
                v-for="log in filteredTradingCoreLogs" 
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
      </el-col>
      
      <!-- 数据中心日志 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>数据中心日志</span>
              <el-select 
                v-model="selectedDataCenterLogLevel" 
                placeholder="选择日志级别" 
                size="small" 
                style="width: 120px;"
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
            <el-timeline v-if="filteredDataCenterLogs.length > 0">
              <el-timeline-item 
                v-for="log in filteredDataCenterLogs" 
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
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  SuccessFilled,
  VideoPause,
  VideoPlay,
  Clock,
  Document,
  Cpu,
  Memo,
  Loading,
  Connection,
  SwitchButton
} from '@element-plus/icons-vue'
import { logLevelMap } from '@/constants'
import { useConsole } from '@/composables'

const {
  consoleData,
  tradingCoreLogs,
  dataCenterLogs,
  selectedTradingCoreLogLevel,
  selectedDataCenterLogLevel,
  filteredTradingCoreLogs,
  filteredDataCenterLogs,
  handleStartTradingCore,
  handleStopTradingCore,
  handleConnectGateway,
  handleDisconnectGateway,
  handleStartDataCenter,
  handleStopDataCenter
} = useConsole()

// 计算网关是否已连接
const isGatewayConnected = computed(() => {
  const gateway = consoleData.tradingCore.gateway
  return !!(gateway && gateway.md_login && gateway.td_login)
})

// 获取核心状态文本
const getCoreStatusText = (status) => {
  // 确保status是字符串
  const statusStr = String(status || 'stopped')
  
  const statusMap = {
    stopped: '已停止',
    initializing: '初始化中',
    connecting: '连接中',
    running: '运行中',
    stopping: '停止中',
    error: '错误'
  }
  
  // 如果在映射中找到了，返回中文，否则返回原值（但不返回数字）
  const result = statusMap[statusStr]
  if (result) {
    return result
  }
  // 如果是数字类型，返回默认值
  if (!isNaN(statusStr) && statusStr !== '') {
    console.warn('[警告] 核心状态是数字:', status, '使用默认值"已停止"')
    return '已停止'
  }
  return statusStr
}

// 获取核心状态类型
const getCoreStatusType = (status) => {
  const statusStr = String(status || 'stopped')
  const typeMap = {
    stopped: 'info',
    initializing: 'warning',
    connecting: 'warning',
    running: 'success',
    stopping: 'warning',
    error: 'danger'
  }
  return typeMap[statusStr] || 'info'
}

// 获取核心状态颜色
const getCoreStatusColor = (status) => {
  const statusStr = String(status || 'stopped')
  const colorMap = {
    stopped: '#909399',
    initializing: '#E6A23C',
    connecting: '#E6A23C',
    running: '#67C23A',
    stopping: '#F56C6C',
    error: '#F56C6C'
  }
  return colorMap[statusStr] || '#909399'
}

// 获取警告框类型
const getAlertType = (status) => {
  const statusStr = String(status || 'stopped')
  const typeMap = {
    stopped: 'info',
    initializing: 'warning',
    connecting: 'warning',
    running: 'success',
    stopping: 'warning',
    error: 'error'
  }
  return typeMap[statusStr] || 'info'
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 自定义统计组件样式 */
.custom-statistic {
  text-align: center;
  padding: 10px 0;
}

.statistic-title {
  color: #909399;
  font-size: 14px;
  margin-bottom: 10px;
  line-height: 22px;
}

.statistic-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.statistic-icon {
  font-size: 24px;
}

.statistic-value {
  font-size: 24px;
  font-weight: 600;
  line-height: 32px;
}

/* 日志容器样式 */
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
</style>
