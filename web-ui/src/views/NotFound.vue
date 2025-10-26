<template>
  <div class="not-found-container">
    <div class="not-found-content">
      <!-- 404大号显示 -->
      <div class="error-code">404</div>
      
      <!-- 提示信息 -->
      <div class="error-message">
        <el-icon :size="48" color="#909399">
          <WarningFilled />
        </el-icon>
        <h2>页面未找到</h2>
        <p class="description">抱歉，您访问的页面不存在或已被移除</p>
      </div>
      
      <!-- 倒计时提示 -->
      <div class="countdown-info">
        <el-text type="info" size="large">
          {{ countdown }} 秒后将自动跳转到仪表盘...
        </el-text>
      </div>
      
      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button type="primary" size="large" @click="goToDashboard">
          <el-icon><House /></el-icon>
          <span>立即跳转</span>
        </el-button>
        <el-button size="large" @click="goBack">
          <el-icon><Back /></el-icon>
          <span>返回上一页</span>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { WarningFilled, House, Back } from '@element-plus/icons-vue'

const router = useRouter()
const countdown = ref(3)
let timer = null

// 跳转到仪表盘
const goToDashboard = () => {
  clearTimer()
  router.push('/dashboard')
}

// 返回上一页
const goBack = () => {
  clearTimer()
  router.back()
}

// 清除定时器
const clearTimer = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

// 启动倒计时
onMounted(() => {
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      goToDashboard()
    }
  }, 1000)
})

// 组件卸载时清除定时器
onUnmounted(() => {
  clearTimer()
})
</script>

<style scoped>
.not-found-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.not-found-content {
  text-align: center;
  background: white;
  border-radius: 16px;
  padding: 60px 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  width: 100%;
}

.error-code {
  font-size: 120px;
  font-weight: bold;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
  margin-bottom: 30px;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.error-message {
  margin-bottom: 40px;
}

.error-message h2 {
  font-size: 28px;
  color: #303133;
  margin: 20px 0 10px;
  font-weight: 600;
}

.error-message .description {
  font-size: 16px;
  color: #606266;
  margin: 0;
}

.countdown-info {
  margin-bottom: 30px;
  padding: 15px;
  background: #f4f4f5;
  border-radius: 8px;
}

.action-buttons {
  display: flex;
  gap: 15px;
  justify-content: center;
  flex-wrap: wrap;
}

.action-buttons .el-button {
  min-width: 150px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .not-found-content {
    padding: 40px 20px;
  }
  
  .error-code {
    font-size: 80px;
  }
  
  .error-message h2 {
    font-size: 24px;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .action-buttons .el-button {
    width: 100%;
  }
}
</style>

