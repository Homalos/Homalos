<template>
  <div>
    <!-- 1. 系统控制 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <!-- 交易系统 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>交易系统</span>
              <el-tag :type="consoleData.tradingSystem.status === 'running' ? 'success' : 'info'">
                {{ consoleData.tradingSystem.status === 'running' ? '运行中' : '已停止' }}
              </el-tag>
            </div>
          </template>
          <div style="padding: 20px 0;">
            <el-row :gutter="20" style="margin-bottom: 20px;">
              <el-col :span="12">
                <el-statistic title="系统状态">
                  <template #prefix>
                    <el-icon :color="consoleData.tradingSystem.status === 'running' ? '#67C23A' : '#909399'">
                      <SuccessFilled v-if="consoleData.tradingSystem.status === 'running'" />
                      <VideoPause v-else />
                    </el-icon>
                  </template>
                  <template #default>
                    <span 
                      style="font-size: 24px; font-weight: 600;" 
                      :style="{ color: consoleData.tradingSystem.status === 'running' ? '#67C23A' : '#909399' }"
                    >
                      {{ consoleData.tradingSystem.status === 'running' ? '运行中' : '已停止' }}
                    </span>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="12">
                <el-statistic title="运行时长" :value="consoleData.tradingSystem.runningTime">
                  <template #prefix>
                    <el-icon color="#409EFF"><Clock /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
            </el-row>
            <el-row :gutter="10">
              <el-col :span="12">
                <el-button 
                  type="success" 
                  style="width: 100%;"
                  :disabled="consoleData.tradingSystem.status === 'running'"
                  @click="handleStartTradingSystem"
                >
                  <el-icon><VideoPlay /></el-icon>
                  启动交易系统
                </el-button>
              </el-col>
              <el-col :span="12">
                <el-button 
                  type="danger" 
                  style="width: 100%;"
                  :disabled="consoleData.tradingSystem.status === 'stopped'"
                  @click="handleStopTradingSystem"
                >
                  <el-icon><VideoPause /></el-icon>
                  停止交易系统
                </el-button>
              </el-col>
            </el-row>
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
                <el-statistic title="系统状态">
                  <template #prefix>
                    <el-icon :color="consoleData.dataCenter.status === 'running' ? '#67C23A' : '#909399'">
                      <SuccessFilled v-if="consoleData.dataCenter.status === 'running'" />
                      <VideoPause v-else />
                    </el-icon>
                  </template>
                  <template #default>
                    <span 
                      style="font-size: 24px; font-weight: 600;" 
                      :style="{ color: consoleData.dataCenter.status === 'running' ? '#67C23A' : '#909399' }"
                    >
                      {{ consoleData.dataCenter.status === 'running' ? '运行中' : '已停止' }}
                    </span>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="8">
                <el-statistic title="进程ID" :value="consoleData.dataCenter.pid || 0">
                  <template #prefix>
                    <el-icon color="#409EFF"><Document /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="8">
                <el-statistic title="运行时长" :value="consoleData.dataCenter.runningTime">
                  <template #prefix>
                    <el-icon color="#409EFF"><Clock /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
            </el-row>
            
            <!-- 资源使用情况 -->
            <el-row :gutter="20" style="margin-bottom: 20px;" v-if="consoleData.dataCenter.status === 'running'">
              <el-col :span="12">
                <el-statistic title="CPU使用率" :value="consoleData.dataCenter.cpu" suffix="%">
                  <template #prefix>
                    <el-icon color="#E6A23C"><Cpu /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="12">
                <el-statistic title="内存使用" :value="consoleData.dataCenter.memory" suffix="MB">
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
      <!-- 交易系统日志 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>交易系统日志</span>
              <el-select 
                v-model="selectedTradingLogLevel" 
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
            <el-timeline v-if="filteredTradingLogs.length > 0">
              <el-timeline-item 
                v-for="log in filteredTradingLogs" 
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
import {
  SuccessFilled,
  VideoPause,
  VideoPlay,
  Clock,
  Document,
  Cpu,
  Memo
} from '@element-plus/icons-vue'
import { logLevelMap } from '@/constants'
import { useConsole } from '@/composables'

const {
  consoleData,
  tradingSystemLogs,
  dataCenterLogs,
  selectedTradingLogLevel,
  selectedDataCenterLogLevel,
  filteredTradingLogs,
  filteredDataCenterLogs,
  handleStartTradingSystem,
  handleStopTradingSystem,
  handleStartDataCenter,
  handleStopDataCenter
} = useConsole()
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

