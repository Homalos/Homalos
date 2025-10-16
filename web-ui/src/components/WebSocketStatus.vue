<template>
  <div class="websocket-status" :class="statusClass">
    <el-tooltip :content="tooltipContent" placement="bottom">
      <div class="status-indicator" @click="handleClick">
        <span class="status-dot"></span>
        <span class="status-text">{{ statusText }}</span>
        <el-icon v-if="wsStatus.attempts > 0" class="loading-icon">
          <Loading />
        </el-icon>
      </div>
    </el-tooltip>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useStrategyStore } from '@/stores/strategy'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const strategyStore = useStrategyStore()
const wsStatus = ref({ connected: false, status: '未连接', attempts: 0 })

// 定时更新状态
let statusTimer = null

onMounted(() => {
  updateStatus()
  statusTimer = setInterval(updateStatus, 1000)
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
  }
})

function updateStatus() {
  wsStatus.value = strategyStore.getWebSocketStatus()
}

const statusClass = computed(() => {
  if (wsStatus.value.connected) {
    return 'status-connected'
  } else if (wsStatus.value.attempts > 0) {
    return 'status-reconnecting'
  } else {
    return 'status-disconnected'
  }
})

const statusText = computed(() => {
  if (wsStatus.value.connected) {
    return '已连接'
  } else if (wsStatus.value.attempts > 0) {
    return `重连中(${wsStatus.value.attempts})`
  } else {
    return '未连接'
  }
})

const tooltipContent = computed(() => {
  if (wsStatus.value.connected) {
    return 'WebSocket已连接，实时接收策略消息\n点击查看详情'
  } else if (wsStatus.value.attempts > 0) {
    return `正在尝试第${wsStatus.value.attempts}次重连...\n点击查看详情`
  } else {
    return 'WebSocket未连接\n点击查看详情'
  }
})

function handleClick() {
  const status = wsStatus.value
  let message = `WebSocket状态: ${status.status}`
  if (status.attempts > 0) {
    message += ` (重连尝试: ${status.attempts})`
  }
  ElMessage.info({
    message,
    duration: 2000
  })
}
</script>

<style scoped>
.websocket-status {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  transition: all 0.3s;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: all 0.3s;
}

.status-connected {
  background-color: #f0f9ff;
  border: 1px solid #67c23a;
}

.status-connected .status-dot {
  background-color: #67c23a;
  box-shadow: 0 0 6px #67c23a;
  animation: pulse 2s infinite;
}

.status-connected .status-text {
  color: #67c23a;
}

.status-reconnecting {
  background-color: #fef0f0;
  border: 1px solid #e6a23c;
}

.status-reconnecting .status-dot {
  background-color: #e6a23c;
  animation: blink 1s infinite;
}

.status-reconnecting .status-text {
  color: #e6a23c;
}

.status-disconnected {
  background-color: #f4f4f5;
  border: 1px solid #909399;
}

.status-disconnected .status-dot {
  background-color: #909399;
}

.status-disconnected .status-text {
  color: #909399;
}

.loading-icon {
  animation: rotate 1s linear infinite;
  color: #e6a23c;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes blink {
  0%, 50%, 100% {
    opacity: 1;
  }
  25%, 75% {
    opacity: 0.3;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>


