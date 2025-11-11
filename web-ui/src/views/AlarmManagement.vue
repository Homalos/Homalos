<template>
  <div class="alarm-management">
    <!-- 使用路由视图支持子路由（告警设置） -->
    <router-view v-slot="{ Component }">
      <component :is="Component" v-if="Component" />
      <template v-else>
        <!-- 告警管理主页面（告警列表） -->
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
            <el-button type="primary" @click="$router.push('/alarms/settings')">告警设置</el-button>
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
          <el-select v-model="filters.status" placeholder="全部" clearable @change="handleFilterChange" class="filter-select-status">
            <el-option label="未处理" value="active" />
            <el-option label="已确认" value="acknowledged" />
            <el-option label="已解决" value="resolved" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="严重程度">
          <el-select v-model="filters.severity" placeholder="全部" clearable @change="handleFilterChange" class="filter-select-severity">
            <el-option label="信息" value="info" />
            <el-option label="警告" value="warning" />
            <el-option label="错误" value="error" />
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="告警类型">
          <el-select v-model="filters.alarm_type" placeholder="全部" clearable @change="handleFilterChange" class="filter-select-type">
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
            class="filter-date-picker"
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
        
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
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
            </div>
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
    </router-view>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAlarmStore } from '@/stores/alarm'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell, Warning, InfoFilled, CircleCheck, Refresh } from '@element-plus/icons-vue'

const router = useRouter()
const alarmStore = useAlarmStore()

// 状态
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

// 不需要 onUnmounted，因为不再使用事件监听器和自定义事件
</script>

<style scoped>
/* 全局卡片优化 - 与Dashboard/Console/StrategyManagement风格一致 */
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

.header-card {
  margin-bottom: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
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
  color: #303133;
  position: relative;
  padding-left: 12px;
}

/* h2左侧渐变装饰条 */
.header-left h2::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 22px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 2px;
}

.header-right {
  display: flex;
  gap: 12px;
}

/* 统计卡片行 */
.stats-row {
  margin-bottom: 20px;
}

/* 统计卡片优化 */
.stat-card {
  cursor: pointer;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.03) 0%, rgba(103, 194, 58, 0.03) 100%);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.15);
  border-color: rgba(64, 158, 255, 0.15);
}

/* 统计卡片顶部装饰条 */
.stat-card::before {
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

.stat-card:hover::before {
  opacity: 1;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 8px;
}

.stat-icon {
  font-size: 48px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.1));
}

.stat-card:hover .stat-icon {
  transform: scale(1.1);
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.15));
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 8px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.stat-label {
  font-size: 14px;
  color: #909399;
  font-weight: 500;
}

/* 筛选卡片 */
.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  margin: 0;
}

/* 筛选器组件宽度设置 */
.filter-select-status {
  width: 100px;
}

.filter-select-severity {
  width: 100px;
}

.filter-select-type {
  width: 140px;
}

.filter-date-picker {
  width: 240px;
}

/* 表格卡片 */
.table-card {
  margin-bottom: 20px;
}

/* 分页容器 */
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

/* 详情JSON */
.alarm-detail .detail-json {
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
  padding: 16px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  max-height: 300px;
  border: 1px solid rgba(64, 158, 255, 0.08);
}

/* 表格行交互 */
:deep(.el-table__row) {
  cursor: pointer;
  transition: all 0.2s ease;
}

:deep(.el-table__row:hover) {
  background-color: rgba(64, 158, 255, 0.03) !important;
}

/* 按钮渐变优化 - 与其他页面一致 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45) !important;
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #67c23a 0%, #4a9e2b 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--success:hover) {
  background: linear-gradient(135deg, #85ce61 0%, #67c23a 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(103, 194, 58, 0.45) !important;
}

:deep(.el-button--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #e13f3f 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--danger:hover) {
  background: linear-gradient(135deg, #f78989 0%, #f56c6c 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(245, 108, 108, 0.45) !important;
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

/* 表格优化 */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
  color: #303133;
  font-weight: 600;
  border-bottom: 2px solid rgba(64, 158, 255, 0.1);
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
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.05) 100%);
  border: 1px solid rgba(0, 0, 0, 0.1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-dialog .el-button--default:hover) {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0.08) 100%);
  border-color: rgba(64, 158, 255, 0.2);
  transform: translateY(-2px);
}

/* 操作按钮容器 - 横向排列 */
.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: nowrap;
}

/* 链接按钮优化 - 白色字体+渐变背景+紧凑型 */
:deep(.el-button.is-link) {
  font-weight: 600;
  padding: 6px 14px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 6px;
  min-width: 56px;
  font-size: 13px;
}

:deep(.el-button.is-link.el-button--primary) {
  color: #ffffff !important;
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%);
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.25);
}

:deep(.el-button.is-link.el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(64, 158, 255, 0.35);
}

:deep(.el-button.is-link.el-button--success) {
  color: #ffffff !important;
  background: linear-gradient(135deg, #67c23a 0%, #4a9e2b 100%);
  box-shadow: 0 2px 6px rgba(103, 194, 58, 0.25);
}

:deep(.el-button.is-link.el-button--success:hover) {
  background: linear-gradient(135deg, #85ce61 0%, #67c23a 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(103, 194, 58, 0.35);
}

:deep(.el-button.is-link.el-button--default) {
  color: #ffffff !important;
  background: linear-gradient(135deg, #909399 0%, #7a7d82 100%);
  box-shadow: 0 2px 6px rgba(144, 147, 153, 0.25);
}

:deep(.el-button.is-link.el-button--default:hover) {
  background: linear-gradient(135deg, #a6a9ad 0%, #909399 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(144, 147, 153, 0.35);
}
</style>

