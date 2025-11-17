<template>
  <div>
    <!-- 1. 系统控制 -->
    <el-row style="margin-bottom: 20px;">
      <!-- 交易核心（全宽显示） -->
      <el-col :span="24">
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
            <!-- 账户登录状态提示 -->
            <el-alert 
              v-if="!tradingAccountStore.isLoggedIn" 
              type="warning" 
              :closable="false"
              style="margin-bottom: 20px;"
            >
              <template #title>
                <span style="font-weight: 600;">⚠️ 未登录券商账户</span>
              </template>
              <div style="margin-top: 8px;">
                启动交易核心并连接网关需要先登录券商账户（输入密码）。
                <br />
                请前往"券商账户"面板登录后再启动交易核心。
              </div>
            </el-alert>
            
            <!-- 免密登录警告（缺少完整配置，且网关未连接） -->
            <el-alert 
              v-else-if="tradingAccountStore.isLoggedIn && !tradingAccountStore.hasBrokerConfig && !isGatewayConnected" 
              type="warning" 
              :closable="false"
              style="margin-bottom: 20px;"
            >
              <template #title>
                <span style="font-weight: 600;">⚠️ 缺少完整账户配置</span>
              </template>
              <div style="margin-top: 8px;">
                您当前是通过<strong>免密登录</strong>，系统未获取到完整的账户配置（包括密码）。
                <br />
                连接网关需要这些敏感信息。请<strong>退出后重新登录并输入密码</strong>。
              </div>
            </el-alert>
            
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
            <div class="gateway-status-container" style="margin-bottom: 20px;">
              <el-tag :type="consoleData.tradingCore.gateway.md_login ? 'success' : 'info'" class="gateway-tag">
                行情网关: {{ consoleData.tradingCore.gateway.md_login ? '✓' : '✗' }}
              </el-tag>
              <el-tag :type="consoleData.tradingCore.gateway.td_login ? 'success' : 'info'" class="gateway-tag">
                交易网关: {{ consoleData.tradingCore.gateway.td_login ? '✓' : '✗' }}
              </el-tag>
              <el-tag :type="consoleData.tradingCore.gateway.td_confirm ? 'success' : 'info'" class="gateway-tag">
                结算确认: {{ consoleData.tradingCore.gateway.td_confirm ? '✓' : '✗' }}
              </el-tag>
              <el-tag :type="consoleData.tradingCore.gateway.instruments_loaded ? 'success' : 'info'" class="gateway-tag">
                合约加载: {{ consoleData.tradingCore.gateway.instruments_loaded ? '✓' : '✗' }}
              </el-tag>
            </div>
            
            <!-- 控制按钮区域 -->
            <div class="control-buttons-container">
              <!-- 核心控制按钮 -->
              <div class="button-group">
                <el-button 
                  type="success" 
                  size="large"
                  :disabled="consoleData.tradingCore.status !== 'stopped'"
                  :loading="consoleData.tradingCore.status === 'initializing'"
                  @click="handleStartTradingCore(true)"
                >
                  <el-icon><VideoPlay /></el-icon>
                  启动核心(自动连接)
                </el-button>
                <el-button 
                  type="danger" 
                  size="large"
                  :disabled="consoleData.tradingCore.status === 'stopped'"
                  :loading="consoleData.tradingCore.status === 'stopping'"
                  @click="handleStopTradingCore"
                >
                  <el-icon><VideoPause /></el-icon>
                  停止核心
                </el-button>
              </div>
              
              <!-- 网关控制按钮（运行时显示） -->
              <div class="button-group" v-if="consoleData.tradingCore.status === 'running'">
                <el-button 
                  type="primary" 
                  size="large"
                  :disabled="isGatewayConnected"
                  @click="handleConnectGateway"
                >
                  <el-icon><Connection /></el-icon>
                  连接网关
                </el-button>
                <el-button 
                  type="warning" 
                  size="large"
                  :disabled="!isGatewayConnected"
                  @click="handleDisconnectGateway"
                >
                  <el-icon><SwitchButton /></el-icon>
                  断开网关
                </el-button>
              </div>
            </div>
            
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

    </el-row>

    <!-- 2. 控制台日志 -->
    <el-row>
      <!-- 交易核心日志（全宽显示） -->
      <el-col :span="24">
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
  selectedTradingCoreLogLevel,
  filteredTradingCoreLogs,
  tradingAccountStore,
  handleStartTradingCore,
  handleStopTradingCore,
  handleConnectGateway,
  handleDisconnectGateway
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
/* 全局卡片优化 - 与Dashboard风格一致 */
:deep(.el-card),
.el-card {
  border-radius: 12px !important;
  border: 1px solid rgba(64, 158, 255, 0.08) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  overflow: hidden !important;
}

:deep(.el-card__header),
.el-card__header {
  border-radius: 12px 12px 0 0 !important;
}

:deep(.el-card__body),
.el-card__body {
  border-radius: 0 0 12px 12px !important;
}

:deep(.el-card.is-hover-shadow:hover),
:deep(.el-card.is-always-shadow),
.el-card.is-hover-shadow:hover,
.el-card.is-always-shadow {
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.12) !important;
}

/* 卡片header优化 - 增加渐变装饰条 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.card-header span {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  position: relative;
  padding-left: 12px;
}

/* header左侧渐变装饰条 */
.card-header span::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 18px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 2px;
}

/* 自定义统计组件样式 - 与Dashboard一致 */
.custom-statistic {
  text-align: center;
  padding: 16px 0; /* 从10px增加到16px */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.statistic-title {
  color: #909399;
  font-size: 14px;
  margin-bottom: 12px; /* 从10px增加到12px */
  line-height: 22px;
  font-weight: 500;
}

.statistic-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px; /* 从8px增加到12px */
}

/* 图标增强 - 与Dashboard一致 */
.statistic-icon {
  font-size: 28px; /* 从24px增加到28px */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

/* 数字增强 - 与Dashboard一致 */
.statistic-value {
  font-size: 32px; /* 从24px增加到32px */
  font-weight: 700; /* 从600增加到700 */
  line-height: 40px; /* 从32px增加到40px */
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

/* 按钮渐变优化 - 与Login页面一致 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45) !important;
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #67c23a 0%, #4a9e2b 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--success:hover) {
  background: linear-gradient(135deg, #85ce61 0%, #67c23a 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(103, 194, 58, 0.45) !important;
}

:deep(.el-button--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #e13f3f 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--danger:hover) {
  background: linear-gradient(135deg, #f78989 0%, #f56c6c 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(245, 108, 108, 0.45) !important;
}

:deep(.el-button--warning) {
  background: linear-gradient(135deg, #e6a23c 0%, #d18b2a 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--warning:hover) {
  background: linear-gradient(135deg, #ebb563 0%, #e6a23c 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(230, 162, 60, 0.45) !important;
}

/* 网关状态容器 - 居中对齐 */
.gateway-status-container {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.gateway-tag {
  min-width: 140px;
  text-align: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.gateway-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
}

/* 控制按钮容器 */
.control-buttons-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 20px;
}

.button-group {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.button-group .el-button {
  min-width: 200px;
  font-size: 15px;
  padding: 12px 24px;
}

/* Tag美化 */
:deep(.el-tag) {
  border-radius: 6px;
  padding: 6px 12px;
  font-weight: 500;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

:deep(.el-tag--success) {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%);
  color: #ffffff;
}

:deep(.el-tag--warning) {
  background: linear-gradient(135deg, #e6a23c 0%, #cf9236 100%);
  color: #ffffff;
}

:deep(.el-tag--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #dd5a5a 100%);
  color: #ffffff;
}

:deep(.el-tag--info) {
  background: linear-gradient(135deg, rgba(144, 147, 153, 0.9) 0%, rgba(144, 147, 153, 0.8) 100%);
  color: #ffffff;
}

/* Alert美化 */
:deep(.el-alert) {
  border-radius: 8px;
  border-left: 4px solid;
}

:deep(.el-alert--warning) {
  border-left-color: #e6a23c;
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.05) 0%, rgba(230, 162, 60, 0.02) 100%);
}

/* 日志容器样式优化 */
.log-container {
  max-height: 500px; /* 从400px增加到500px，更多内容 */
  overflow-y: auto;
  padding: 10px;
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
  border-radius: 8px;
  border: 1px solid rgba(64, 158, 255, 0.05);
}

/* 自定义滚动条 */
.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(135deg, #53a8ff 0%, #85ce61 100%);
}

.log-item {
  display: flex;
  align-items: center;
  padding: 4px 0;
}

.log-message {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}

/* Timeline优化 */
:deep(.el-timeline-item__timestamp) {
  color: #909399;
  font-size: 12px;
  font-weight: 500;
}
</style>
