<template>
  <div class="alarm-management">
    <!-- 告警设置页面 -->
    <AlarmSettings v-if="showSettings" @back="showSettings = false" />
    
    <!-- 告警管理主页面 -->
    <template v-else>
      <el-card class="header-card" shadow="hover">
        <div class="page-header">
          <div class="header-left">
            <h2>告警管理</h2>
            <el-tag type="danger" v-if="stats.active_count > 0">
              {{ stats.active_count }} 条未处理
            </el-tag>
          </div>
          <div class="header-right">
            <el-button :icon="Refresh" @click="handleRefresh">刷新</el-button>
            <el-button type="primary" @click="showSettings = true">告警设置</el-button>
          </div>
        </div>
      </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <el-icon class="stat-icon" color="#409EFF"><Bell /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.today_count }}</div>
              <div class="stat-label">今日告警</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <el-icon class="stat-icon" color="#F56C6C"><Warning /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.active_count }}</div>
              <div class="stat-label">未处理</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <el-icon class="stat-icon" color="#E6A23C"><InfoFilled /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.status_stats?.acknowledged || 0 }}</div>
              <div class="stat-label">已确认</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <el-icon class="stat-icon" color="#67C23A"><CircleCheck /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.status_stats?.resolved || 0 }}</div>
              <div class="stat-label">已解决</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选器 -->
    <el-card class="filter-card" shadow="hover">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable @change="handleFilterChange">
            <el-option label="未处理" value="active" />
            <el-option label="已确认" value="acknowledged" />
            <el-option label="已解决" value="resolved" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="严重程度">
          <el-select v-model="filters.severity" placeholder="全部" clearable @change="handleFilterChange">
            <el-option label="信息" value="info" />
            <el-option label="警告" value="warning" />
            <el-option label="错误" value="error" />
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="告警类型">
          <el-select v-model="filters.alarm_type" placeholder="全部" clearable @change="handleFilterChange">
            <el-option label="进程崩溃" value="process_crash" />
            <el-option label="重载失败" value="reload_failed" />
            <el-option label="CPU过高" value="high_cpu" />
            <el-option label="内存过高" value="high_memory" />
            <el-option label="资源严重不足" value="critical_resource" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="handleDateChange"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button @click="handleReset">重置</el-button>
          <el-button type="primary" @click="handleSearch">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 告警列表 -->
    <el-card class="table-card" shadow="hover">
      <el-table
        v-loading="loading"
        :data="alarms"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">
              {{ getSeverityLabel(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="alarm_type" label="类型" width="120">
          <template #default="{ row }">
            {{ getTypeLabel(row.alarm_type) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="message" label="告警消息" min-width="300" show-overflow-tooltip />
        
        <el-table-column prop="source" label="来源" width="120" />
        
        <el-table-column prop="target" label="目标" width="150" show-overflow-tooltip />
        
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="触发时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'active'"
              size="small"
              type="primary"
              link
              @click.stop="handleAcknowledge(row)"
            >
              确认
            </el-button>
            <el-button
              v-if="row.status !== 'resolved'"
              size="small"
              type="success"
              link
              @click.stop="handleResolve(row)"
            >
              解决
            </el-button>
            <el-button
              size="small"
              link
              @click.stop="handleViewDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalAlarms"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="告警详情"
      width="700px"
    >
      <div v-if="selectedAlarm" class="alarm-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="告警ID" :span="2">
            <el-text type="info" size="small" style="font-family: monospace;">
              {{ selectedAlarm.alarm_id }}
            </el-text>
          </el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityType(selectedAlarm.severity)">
              {{ getSeverityLabel(selectedAlarm.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedAlarm.status)">
              {{ getStatusLabel(selectedAlarm.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="告警类型">
            {{ getTypeLabel(selectedAlarm.alarm_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="告警源">
            {{ selectedAlarm.source }}
          </el-descriptions-item>
          <el-descriptions-item label="目标对象" :span="2" v-if="selectedAlarm.target">
            {{ selectedAlarm.target }}
          </el-descriptions-item>
          <el-descriptions-item label="告警消息" :span="2">
            {{ selectedAlarm.message }}
          </el-descriptions-item>
          <el-descriptions-item label="触发时间">
            {{ formatDateTime(selectedAlarm.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="确认时间" v-if="selectedAlarm.acknowledged_at">
            {{ formatDateTime(selectedAlarm.acknowledged_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="解决时间" :span="2" v-if="selectedAlarm.resolved_at">
            {{ formatDateTime(selectedAlarm.resolved_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="详细信息" :span="2" v-if="selectedAlarm.details">
            <pre class="detail-json">{{ JSON.stringify(selectedAlarm.details, null, 2) }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button
          v-if="selectedAlarm && selectedAlarm.status === 'active'"
          type="primary"
          @click="handleAcknowledge(selectedAlarm)"
        >
          确认告警
        </el-button>
        <el-button
          v-if="selectedAlarm && selectedAlarm.status !== 'resolved'"
          type="success"
          @click="handleResolve(selectedAlarm)"
        >
          解决告警
        </el-button>
      </template>
    </el-dialog>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAlarmStore } from '@/stores/alarm'
import { ElMessage, ElMessageBox } from 'element-plus'
import AlarmSettings from '@/views/AlarmSettings.vue'
import { Bell, Warning, InfoFilled, CircleCheck, Refresh } from '@element-plus/icons-vue'

const router = useRouter()
const alarmStore = useAlarmStore()

// 状态
const showSettings = ref(false)
const loading = ref(false)
const detailDialogVisible = ref(false)
const selectedAlarm = ref(null)
const dateRange = ref([])

// 计算属性
const alarms = computed(() => alarmStore.alarms)
const stats = computed(() => alarmStore.stats)
const filters = computed(() => alarmStore.filters)
const currentPage = computed({
  get: () => alarmStore.currentPage,
  set: (val) => alarmStore.setPage(val)
})
const pageSize = computed(() => alarmStore.pageSize)
const totalAlarms = computed(() => alarmStore.totalAlarms)

// 方法
async function loadData() {
  loading.value = true
  try {
    await Promise.all([
      alarmStore.fetchAlarms(),
      alarmStore.fetchStats()
    ])
  } catch (error) {
    ElMessage.error('加载数据失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  alarmStore.setPage(1)
  loadData()
}

function handleDateChange(dates) {
  if (dates && dates.length === 2) {
    alarmStore.setFilters({
      start_date: dates[0],
      end_date: dates[1]
    })
  } else {
    alarmStore.setFilters({
      start_date: null,
      end_date: null
    })
  }
  handleFilterChange()
}

function handleSearch() {
  loadData()
}

function handleReset() {
  alarmStore.resetFilters()
  dateRange.value = []
  loadData()
}

function handleRefresh() {
  loadData()
}

function handlePageChange(page) {
  alarmStore.setPage(page)
  loadData()
}

function handleSizeChange(size) {
  alarmStore.pageSize = size
  alarmStore.setPage(1)
  loadData()
}

function handleRowClick(row) {
  handleViewDetail(row)
}

function handleViewDetail(row) {
  selectedAlarm.value = row
  detailDialogVisible.value = true
}

async function handleAcknowledge(row) {
  try {
    await ElMessageBox.confirm('确认此告警？', '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await alarmStore.acknowledgeAlarm(row.alarm_id)
    ElMessage.success('告警已确认')
    detailDialogVisible.value = false
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('确认告警失败: ' + error.message)
    }
  }
}

async function handleResolve(row) {
  try {
    await ElMessageBox.confirm('解决此告警？', '提示', {
      confirmButtonText: '解决',
      cancelButtonText: '取消',
      type: 'success'
    })
    
    await alarmStore.resolveAlarm(row.alarm_id)
    ElMessage.success('告警已解决')
    detailDialogVisible.value = false
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('解决告警失败: ' + error.message)
    }
  }
}

// goToSettings函数已移除，现在使用showSettings状态切换视图

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
  loadData()
  
  // 连接WebSocket
  if (!alarmStore.wsConnected) {
    alarmStore.connectWebSocket()
  }
})

onUnmounted(() => {
  // 不断开WebSocket，保持全局连接
})
</script>

<style scoped>
/* 告警管理页面样式 - 使用主内容区域的统一边距 */

.header-card {
  margin-bottom: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 12px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  font-size: 40px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  margin: 0;
}

.table-card {
  margin-bottom: 20px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.alarm-detail .detail-json {
  background: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 300px;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: var(--el-fill-color-light);
}
</style>

