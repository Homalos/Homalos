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
      <el-descriptions-item label="用户手册">
        <el-link type="primary" :href="systemInfo.user_guide" target="_blank">
          <el-icon><Document /></el-icon>
          快速开始
        </el-link>
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
import { Document } from '@element-plus/icons-vue'
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
  user_guide: 'https://homalos.github.io/guide/quick_start',
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
/* 全局卡片优化 - 与所有页面风格一致 */
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

/* 卡片header优化 */
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

/* Descriptions优化 */
:deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
  width: 140px;
}

:deep(.el-descriptions__content) {
  color: #303133;
  font-size: 14px;
}

/* 系统名称样式增强 */
:deep(.el-descriptions__content) span {
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Tag美化 */
:deep(.el-tag) {
  border-radius: 6px;
  padding: 6px 12px;
  font-weight: 500;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 14px;
}

:deep(.el-tag:hover) {
  transform: translateY(-1px);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.12);
}

:deep(.el-tag--success) {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%);
  color: #ffffff;
}

/* Link链接美化 */
:deep(.el-link) {
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 4px 8px;
  border-radius: 4px;
}

:deep(.el-link:hover) {
  background: rgba(64, 158, 255, 0.08);
  transform: translateX(2px);
}

:deep(.el-link.el-link--primary) {
  color: #409eff;
}

:deep(.el-link.el-link--primary:hover) {
  color: #53a8ff;
}

/* 技术栈列表优化 */
:deep(.el-descriptions__content) > div > div {
  padding: 4px 0;
  position: relative;
  padding-left: 16px;
}

:deep(.el-descriptions__content) > div > div::before {
  content: '▸';
  position: absolute;
  left: 0;
  color: #409eff;
  font-weight: bold;
}
</style>

