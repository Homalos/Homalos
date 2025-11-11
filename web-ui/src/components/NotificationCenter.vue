<template>
  <div class="notification-center">
    <!-- 铃铛图标 -->
    <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="notification-badge">
      <el-icon 
        :size="20" 
        class="header-icon"
        @click="togglePanel"
        :class="{ 'has-unread': unreadCount > 0 }"
      >
        <Bell />
      </el-icon>
    </el-badge>

    <!-- 下拉面板 -->
    <el-drawer
      v-model="panelVisible"
      title="告警通知"
      direction="rtl"
      size="400px"
      :append-to-body="true"
    >
      <!-- 头部操作 -->
      <template #header>
        <div class="drawer-header">
          <span class="title">告警通知</span>
          <el-badge :value="unreadCount" :hidden="unreadCount === 0" type="danger" />
        </div>
      </template>

      <!-- 统计卡片 -->
      <div class="stats-card">
        <div class="stat-item">
          <span class="label">今日告警</span>
          <span class="value">{{ stats.today_count }}</span>
        </div>
        <div class="stat-item">
          <span class="label">未处理</span>
          <span class="value danger">{{ stats.active_count }}</span>
        </div>
      </div>

      <!-- 告警列表 -->
      <div class="alarm-list">
        <el-empty v-if="recentAlarms.length === 0" description="暂无告警" />
        
        <div
          v-for="alarm in recentAlarms"
          :key="alarm.alarm_id"
          class="alarm-item"
          :class="`severity-${alarm.severity}`"
          @click="handleAlarmClick(alarm)"
        >
          <div class="alarm-header">
            <el-tag 
              :type="getSeverityType(alarm.severity)" 
              size="small"
              effect="dark"
            >
              {{ getSeverityLabel(alarm.severity) }}
            </el-tag>
            <span class="alarm-time">{{ formatTime(alarm.created_at) }}</span>
          </div>
          
          <div class="alarm-content">
            <div class="alarm-type">{{ getTypeLabel(alarm.alarm_type) }}</div>
            <div class="alarm-message">{{ alarm.message }}</div>
            <div v-if="alarm.target" class="alarm-target">
              <el-icon><Location /></el-icon>
              {{ alarm.target }}
            </div>
          </div>
          
          <div class="alarm-actions">
            <el-button 
              v-if="alarm.status === 'active'"
              size="small" 
              type="primary" 
              link
              @click.stop="acknowledgeAlarm(alarm.alarm_id)"
            >
              确认
            </el-button>
            <el-button 
              v-if="alarm.status !== 'resolved'"
              size="small" 
              type="success" 
              link
              @click.stop="resolveAlarm(alarm.alarm_id)"
            >
              解决
            </el-button>
          </div>
        </div>
      </div>

      <!-- 底部操作 -->
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="goToAlarmManagement" type="primary">
            查看全部告警
          </el-button>
          <el-button @click="goToAlarmSettings">
            告警设置
          </el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 告警详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="告警详情"
      width="600px"
      :append-to-body="true"
    >
      <div v-if="selectedAlarm" class="alarm-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="告警ID">
            <el-text type="info" size="small" style="font-family: monospace;">
              {{ selectedAlarm.alarm_id }}
            </el-text>
          </el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityType(selectedAlarm.severity)">
              {{ getSeverityLabel(selectedAlarm.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="告警类型">
            {{ getTypeLabel(selectedAlarm.alarm_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="告警源">
            {{ selectedAlarm.source }}
          </el-descriptions-item>
          <el-descriptions-item label="目标对象" v-if="selectedAlarm.target">
            {{ selectedAlarm.target }}
          </el-descriptions-item>
          <el-descriptions-item label="告警消息">
            {{ selectedAlarm.message }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedAlarm.status)">
              {{ getStatusLabel(selectedAlarm.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="触发时间">
            {{ formatDateTime(selectedAlarm.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="确认时间" v-if="selectedAlarm.acknowledged_at">
            {{ formatDateTime(selectedAlarm.acknowledged_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="解决时间" v-if="selectedAlarm.resolved_at">
            {{ formatDateTime(selectedAlarm.resolved_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="详细信息" v-if="selectedAlarm.details">
            <pre class="detail-json">{{ JSON.stringify(selectedAlarm.details, null, 2) }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button 
          v-if="selectedAlarm && selectedAlarm.status === 'active'"
          type="primary" 
          @click="acknowledgeAlarm(selectedAlarm.alarm_id)"
        >
          确认告警
        </el-button>
        <el-button 
          v-if="selectedAlarm && selectedAlarm.status !== 'resolved'"
          type="success" 
          @click="resolveAlarm(selectedAlarm.alarm_id)"
        >
          解决告警
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAlarmStore } from '@/stores/alarm'
import { ElMessage, ElNotification } from 'element-plus'
import { Bell, Location } from '@element-plus/icons-vue'

// 定义事件
const emit = defineEmits(['switchToAlarms', 'switchToAlarmSettings'])

const alarmStore = useAlarmStore()

// 状态
const panelVisible = ref(false)
const detailDialogVisible = ref(false)
const selectedAlarm = ref(null)

// 计算属性
const unreadCount = computed(() => alarmStore.unreadCount)
const recentAlarms = computed(() => alarmStore.recentAlarms)
const stats = computed(() => alarmStore.stats)

// 方法
function togglePanel() {
  panelVisible.value = !panelVisible.value
  if (panelVisible.value) {
    // 打开面板时刷新数据
    alarmStore.fetchStats()
    alarmStore.fetchAlarms()
  }
}

function handleAlarmClick(alarm) {
  selectedAlarm.value = alarm
  detailDialogVisible.value = true
}

async function acknowledgeAlarm(alarmId) {
  try {
    await alarmStore.acknowledgeAlarm(alarmId)
    ElMessage.success('告警已确认')
    detailDialogVisible.value = false
  } catch (error) {
    ElMessage.error('确认告警失败: ' + error.message)
  }
}

async function resolveAlarm(alarmId) {
  try {
    await alarmStore.resolveAlarm(alarmId)
    ElMessage.success('告警已解决')
    detailDialogVisible.value = false
  } catch (error) {
    ElMessage.error('解决告警失败: ' + error.message)
  }
}

function goToAlarmManagement() {
  panelVisible.value = false
  emit('switchToAlarms')
}

function goToAlarmSettings() {
  panelVisible.value = false
  emit('switchToAlarmSettings')
}

// 格式化函数
function getSeverityType(severity) {
  const types = {
    info: 'info',
    warning: 'warning',
    error: 'danger',
    critical: 'danger'
  }
  return types[severity] || 'info'
}

function getSeverityLabel(severity) {
  const labels = {
    info: '信息',
    warning: '警告',
    error: '错误',
    critical: '严重'
  }
  return labels[severity] || severity
}

function getTypeLabel(type) {
  const labels = {
    process_crash: '进程崩溃',
    reload_failed: '重载失败',
    high_cpu: 'CPU过高',
    high_memory: '内存过高',
    critical_resource: '资源严重不足',
    ws_disconnect: 'WebSocket断开',
    test: '测试告警',
    custom: '自定义告警'
  }
  return labels[type] || type
}

function getStatusType(status) {
  const types = {
    active: 'danger',
    acknowledged: 'warning',
    resolved: 'success'
  }
  return types[status] || 'info'
}

function getStatusLabel(status) {
  const labels = {
    active: '未处理',
    acknowledged: '已确认',
    resolved: '已解决'
  }
  return labels[status] || status
}

function formatTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${Math.floor(diff / 86400000)}天前`
}

function formatDateTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 生命周期
onMounted(() => {
  // 连接WebSocket
  alarmStore.connectWebSocket()
  
  // 请求通知权限
  alarmStore.requestNotificationPermission()
  
  // 初始加载统计
  alarmStore.fetchStats()
})

onUnmounted(() => {
  // 断开WebSocket
  alarmStore.disconnectWebSocket()
})
</script>

<style scoped>
.notification-center {
  position: relative;
}

.header-icon {
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: white;
}

.header-icon:hover {
  opacity: 0.8;
  transform: scale(1.1);
}

.notification-badge :deep(.el-badge__content) {
  border: 2px solid #409eff;
  background-color: var(--el-color-danger);
}

.has-unread {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(var(--el-color-danger-rgb), 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(var(--el-color-danger-rgb), 0);
  }
}

/* Drawer header优化 */
.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drawer-header .title {
  font-size: 18px;
  font-weight: 600;
  position: relative;
  padding-left: 12px;
}

/* title左侧渐变装饰条 */
.drawer-header .title::before {
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

/* 统计卡片优化 */
.stats-card {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.05) 0%, rgba(103, 194, 58, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid rgba(64, 158, 255, 0.1);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stat-item .label {
  font-size: 13px;
  color: #909399;
  font-weight: 500;
}

.stat-item .value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.stat-item .value.danger {
  color: #f56c6c;
}

/* 告警列表 */
.alarm-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 告警项优化 - 增强圆角和视觉效果 */
.alarm-item {
  padding: 16px;
  border: 1px solid rgba(64, 158, 255, 0.1);
  border-radius: 12px !important;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 1) 100%);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  position: relative;
}

.alarm-item:hover {
  border-color: #409eff;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.18);
  transform: translateY(-3px);
}

/* 告警项顶部装饰条（hover显示） */
.alarm-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #409eff 0%, #67c23a 50%, #e6a23c 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.alarm-item:hover::before {
  opacity: 1;
}

.alarm-item.severity-critical {
  border-left: 4px solid #f56c6c;
}

.alarm-item.severity-error {
  border-left: 4px solid #e6a23c;
}

.alarm-item.severity-warning {
  border-left: 4px solid #e6a23c;
}

.alarm-item.severity-info {
  border-left: 4px solid #909399;
}

.alarm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.alarm-time {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}

.alarm-content {
  margin-bottom: 10px;
}

.alarm-type {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #303133;
}

.alarm-message {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

.alarm-target {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

/* 告警操作按钮 - 白色字体+渐变背景 */
.alarm-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

:deep(.alarm-actions .el-button.is-link) {
  font-weight: 600;
  padding: 6px 14px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 6px;
  min-width: 56px;
  font-size: 13px;
}

:deep(.alarm-actions .el-button.is-link.el-button--primary) {
  color: #ffffff !important;
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%);
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.25);
}

:deep(.alarm-actions .el-button.is-link.el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(64, 158, 255, 0.35);
}

:deep(.alarm-actions .el-button.is-link.el-button--success) {
  color: #ffffff !important;
  background: linear-gradient(135deg, #67c23a 0%, #4a9e2b 100%);
  box-shadow: 0 2px 6px rgba(103, 194, 58, 0.25);
}

:deep(.alarm-actions .el-button.is-link.el-button--success:hover) {
  background: linear-gradient(135deg, #85ce61 0%, #67c23a 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(103, 194, 58, 0.35);
}

/* Drawer footer按钮 */
.drawer-footer {
  display: flex;
  gap: 12px;
}

.drawer-footer .el-button {
  flex: 1;
}

:deep(.drawer-footer .el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.drawer-footer .el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45) !important;
}

:deep(.drawer-footer .el-button--default) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.drawer-footer .el-button--default:hover) {
  transform: translateY(-2px);
}

/* Tag美化 */
:deep(.el-tag) {
  border-radius: 6px;
  padding: 6px 12px;
  font-weight: 500;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-tag:hover) {
  transform: translateY(-1px);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.12);
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

/* Dialog中的按钮 */
:deep(.el-dialog .el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-dialog .el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45) !important;
}

:deep(.el-dialog .el-button--success) {
  background: linear-gradient(135deg, #67c23a 0%, #4a9e2b 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-dialog .el-button--success:hover) {
  background: linear-gradient(135deg, #85ce61 0%, #67c23a 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(103, 194, 58, 0.45) !important;
}

:deep(.el-dialog .el-button--default) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-dialog .el-button--default:hover) {
  transform: translateY(-2px);
}

/* Descriptions优化 */
:deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
}

:deep(.el-descriptions__content) {
  color: #303133;
}

/* 详情JSON */
.alarm-detail .detail-json {
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
  padding: 16px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  border: 1px solid rgba(64, 158, 255, 0.08);
}
</style>

