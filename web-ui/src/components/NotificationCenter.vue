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
  transition: opacity 0.3s;
  color: white;
}

.header-icon:hover {
  opacity: 0.8;
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

.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drawer-header .title {
  font-size: 18px;
  font-weight: 600;
}

.stats-card {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stat-item .label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stat-item .value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.stat-item .value.danger {
  color: var(--el-color-danger);
}

.alarm-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alarm-item {
  padding: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.alarm-item:hover {
  border-color: var(--el-color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.alarm-item.severity-critical {
  border-left: 4px solid var(--el-color-danger);
}

.alarm-item.severity-error {
  border-left: 4px solid var(--el-color-warning);
}

.alarm-item.severity-warning {
  border-left: 4px solid var(--el-color-warning);
}

.alarm-item.severity-info {
  border-left: 4px solid var(--el-color-info);
}

.alarm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.alarm-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.alarm-content {
  margin-bottom: 8px;
}

.alarm-type {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--el-text-color-primary);
}

.alarm-message {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
}

.alarm-target {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.alarm-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.drawer-footer {
  display: flex;
  gap: 12px;
}

.drawer-footer .el-button {
  flex: 1;
}

.alarm-detail .detail-json {
  background: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
}
</style>

