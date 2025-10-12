<template>
  <el-card shadow="hover" v-loading="loading">
    <template #header>
      <div class="card-header">
        <span>关于系统</span>
      </div>
    </template>
    <el-descriptions :column="1" border size="large">
      <el-descriptions-item label="系统名称">
        <span style="font-weight: 600; font-size: 16px;">{{ systemInfo.name }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="版本">
        <el-tag type="success">v{{ systemInfo.version }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="作者">
        {{ systemInfo.author }}
      </el-descriptions-item>
      <el-descriptions-item label="版权">
        {{ systemInfo.copyright }}
      </el-descriptions-item>
      <el-descriptions-item label="简介">
        {{ systemInfo.describe }}
      </el-descriptions-item>
      <el-descriptions-item label="技术栈">
        <div style="line-height: 1.8;">
          <div v-for="(tech, index) in systemInfo.technology_stack" :key="index">
            {{ tech }}
          </div>
        </div>
      </el-descriptions-item>
      <el-descriptions-item label="时区">
        {{ systemInfo.timezone }}
      </el-descriptions-item>
      <el-descriptions-item label="联系方式">
        <div>
          <el-link type="primary" :href="systemInfo.contact" target="_blank">{{ systemInfo.contact }}</el-link>
        </div>
      </el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSystemInfo } from '@/api/system'

// 加载状态
const loading = ref(false)

// 系统信息
const systemInfo = ref({
  name: 'Homalos 量化交易系统',
  version: '0.0.1',
  author: 'Homalos Team',
  copyright: 'Copyright © 2025 Homalos Team. All rights reserved.',
  describe: 'Homalos 是一个专业的期货量化交易系统，提供策略开发、回测、实盘交易等功能。',
  technology_stack: [
    '后端：Python 3.10 + FastAPI',
    '前端：Vue 3 + Element Plus + Vite',
    '数据库：SQLite'
  ],
  timezone: 'Asia/Shanghai',
  contact: 'https://github.com/homalos'
})

/**
 * 加载系统信息
 */
const loadSystemInfo = async () => {
  loading.value = true
  try {
    const response = await getSystemInfo()
    console.log('获取系统信息:', response)
    
    // 更新系统信息
    systemInfo.value = response
    
    console.log('系统信息已加载')
  } catch (error) {
    console.error('加载系统信息失败:', error)
    ElMessage.warning('加载系统信息失败，使用默认配置')
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载系统信息
onMounted(() => {
  loadSystemInfo()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

