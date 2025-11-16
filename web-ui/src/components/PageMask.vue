<template>
  <div v-if="show" class="page-mask">
    <div class="mask-content">
      <el-icon :size="60" color="#409EFF" class="mask-icon">
        <Lock />
      </el-icon>
      <h3 class="mask-title">{{ title }}</h3>
      <p class="mask-description">{{ description }}</p>
      <el-button
        type="primary"
        size="large"
        @click="handleLogin"
      >
        登录券商账户
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { Lock } from '@element-plus/icons-vue'

defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '请先登录券商账户'
  },
  description: {
    type: String,
    default: '此页面需要登录券商账户后才能访问'
  }
})

const emit = defineEmits(['login'])

function handleLogin() {
  emit('login')
}
</script>

<style scoped>
.page-mask {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.mask-content {
  text-align: center;
  padding: 40px;
  max-width: 500px;
}

.mask-icon {
  margin-bottom: 20px;
  animation: bounce 2s infinite;
}

.mask-title {
  font-size: 24px;
  color: #303133;
  margin-bottom: 12px;
}

.mask-description {
  font-size: 14px;
  color: #606266;
  margin-bottom: 30px;
  line-height: 1.6;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}
</style>

