<template>
  <el-card shadow="hover">
    <template #header>
      <div class="card-header">
        <span>关于系统</span>
      </div>
    </template>
    <el-descriptions :column="1" border size="large">
      <el-descriptions-item label="系统名称">
        <span style="font-weight: 600; font-size: 16px;">Homalos 量化交易系统</span>
      </el-descriptions-item>
      <el-descriptions-item label="版本">
        <el-tag type="success">v0.0.1</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="作者">
        Homalos Team
      </el-descriptions-item>
      <el-descriptions-item label="版权">
        Copyright © 2025 Homalos. All rights reserved.
      </el-descriptions-item>
      <el-descriptions-item label="简介">
        Homalos 是一个专业的期货量化交易系统，提供策略开发、回测、实盘交易等功能，助力投资者实现量化交易目标。
      </el-descriptions-item>
      <el-descriptions-item label="技术栈">
        <div style="line-height: 1.8;">
          <div>后端：Python 3.10 + FastAPI + SQLite</div>
          <div>前端：Vue 3 + Element Plus + Vite</div>
          <div>数据：行情接口 + 数据中心</div>
        </div>
      </el-descriptions-item>
      <el-descriptions-item label="联系方式">
        <div>
          <el-link type="primary" href="https://github.com/homalos" target="_blank">GitHub</el-link>
        </div>
      </el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup>
// 纯静态展示组件，无需任何逻辑
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

