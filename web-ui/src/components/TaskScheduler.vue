<template>
  <div>
    <!-- 任务调度器面板 -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>任务调度器</span>
          <el-button type="primary" size="small" @click="addTaskDialogVisible = true">
            <el-icon style="margin-right: 5px;"><Plus /></el-icon>
            添加任务
          </el-button>
        </div>
      </template>
      
      <!-- 任务统计 -->
      <el-row :gutter="20" style="margin-bottom: 20px;">
        <el-col :span="8">
          <el-statistic title="总任务数" :value="totalTasksCount">
            <template #prefix>
              <el-icon color="#409eff"><Timer /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="8">
          <el-statistic title="已启用" :value="enabledTasksCount">
            <template #prefix>
              <el-icon color="#67C23A"><VideoPlay /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="8">
          <el-statistic title="已禁用" :value="disabledTasksCount">
            <template #prefix>
              <el-icon color="#909399"><VideoPause /></el-icon>
            </template>
          </el-statistic>
        </el-col>
      </el-row>
      
      <!-- 任务列表表格 -->
      <el-table :data="scheduledTasks" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" min-width="50" />
        <el-table-column prop="name" label="任务名称" min-width="120" />
        <el-table-column label="任务类型" min-width="100">
          <template #default="{ row }">
            <el-tag :color="taskTypeMap[row.type].color" style="color: white;">
              {{ taskTypeMap[row.type].name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行配置" min-width="160">
          <template #default="{ row }">
            {{ formatTaskConfig(row) }}
          </template>
        </el-table-column>
        <el-table-column label="下次执行" min-width="150">
          <template #default="{ row }">
            {{ getRelativeTime(calculateNextRunTime(row)) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'enabled' ? 'success' : 'info'">
              {{ row.status === 'enabled' ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="260" fixed="right">
          <template #default="{ row }">
            <el-button 
              size="small" 
              :type="row.status === 'enabled' ? 'warning' : 'success'"
              @click="handleToggleTaskStatus(row)"
            >
              {{ row.status === 'enabled' ? '禁用' : '启用' }}
            </el-button>
            <el-button size="small" @click="handleEditTask(row)">
              <el-icon style="margin-right: 3px;"><Edit /></el-icon>
              编辑
            </el-button>
            <el-button size="small" @click="handleShowHistory(row)">
              <el-icon style="margin-right: 3px;"><Clock /></el-icon>
              历史
            </el-button>
            <el-button size="small" type="danger" @click="handleDeleteTask(row.id)">
              <el-icon style="margin-right: 3px;"><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑任务对话框 -->
    <el-dialog 
      v-model="addTaskDialogVisible" 
      title="添加任务" 
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="newTaskForm" label-width="120px">
        <el-form-item label="任务名称" required>
          <el-input v-model="newTaskForm.name" placeholder="请输入任务名称" />
        </el-form-item>
        
        <el-form-item label="任务类型" required>
          <el-select v-model="newTaskForm.type" style="width: 100%;">
            <el-option label="每日任务" value="daily" />
            <el-option label="一次性任务" value="once" />
            <el-option label="每分钟任务" value="minute" />
            <el-option label="每周任务" value="weekday" />
            <el-option label="每月任务" value="monthly" />
          </el-select>
        </el-form-item>
        
        <!-- 每日任务配置 -->
        <el-form-item v-if="newTaskForm.type === 'daily'" label="执行时间" required>
          <el-time-picker 
            v-model="newTaskForm.config.time" 
            format="HH:mm" 
            value-format="HH:mm"
            placeholder="选择时间"
          />
        </el-form-item>
        
        <!-- 一次性任务配置 -->
        <el-form-item v-if="newTaskForm.type === 'once'" label="执行时间" required>
          <el-date-picker 
            v-model="newTaskForm.config.dateTime" 
            type="datetime" 
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm:00"
            placeholder="选择日期时间"
          />
        </el-form-item>
        
        <!-- 每周任务配置 -->
        <template v-if="newTaskForm.type === 'weekday'">
          <el-form-item label="执行时间" required>
            <el-time-picker 
              v-model="newTaskForm.config.time" 
              format="HH:mm" 
              value-format="HH:mm"
              placeholder="选择时间"
            />
          </el-form-item>
          <el-form-item label="星期" required>
            <el-checkbox-group v-model="newTaskForm.config.dayOfWeek">
              <el-checkbox label="周一" />
              <el-checkbox label="周二" />
              <el-checkbox label="周三" />
              <el-checkbox label="周四" />
              <el-checkbox label="周五" />
              <el-checkbox label="周六" />
              <el-checkbox label="周日" />
            </el-checkbox-group>
          </el-form-item>
        </template>
        
        <!-- 每月任务配置 -->
        <template v-if="newTaskForm.type === 'monthly'">
          <el-form-item label="执行时间" required>
            <el-time-picker 
              v-model="newTaskForm.config.time" 
              format="HH:mm" 
              value-format="HH:mm"
              placeholder="选择时间"
            />
          </el-form-item>
          <el-form-item label="日期" required>
            <el-select v-model="newTaskForm.config.monthDay" multiple placeholder="选择日期" style="width: 100%;">
              <el-option v-for="day in 31" :key="day" 
                         :label="`${day}号`" 
                         :value="String(day).padStart(2, '0')" />
            </el-select>
          </el-form-item>
        </template>
        
        <el-form-item v-if="newTaskForm.type === 'minute'" label="说明">
          <el-alert 
            type="info" 
            :closable="false"
            show-icon
          >
            此任务将每分钟执行一次
          </el-alert>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="addTaskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveTask">保存</el-button>
      </template>
    </el-dialog>

    <!-- 编辑任务对话框 -->
    <el-dialog 
      v-model="editTaskDialogVisible" 
      title="编辑任务" 
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="newTaskForm" label-width="120px">
        <el-form-item label="任务名称" required>
          <el-input v-model="newTaskForm.name" placeholder="请输入任务名称" />
        </el-form-item>
        
        <el-form-item label="任务类型" required>
          <el-select v-model="newTaskForm.type" style="width: 100%;">
            <el-option label="每日任务" value="daily" />
            <el-option label="一次性任务" value="once" />
            <el-option label="每分钟任务" value="minute" />
            <el-option label="每周任务" value="weekday" />
            <el-option label="每月任务" value="monthly" />
          </el-select>
        </el-form-item>
        
        <!-- 每日任务配置 -->
        <el-form-item v-if="newTaskForm.type === 'daily'" label="执行时间" required>
          <el-time-picker 
            v-model="newTaskForm.config.time" 
            format="HH:mm" 
            value-format="HH:mm"
            placeholder="选择时间"
          />
        </el-form-item>
        
        <!-- 一次性任务配置 -->
        <el-form-item v-if="newTaskForm.type === 'once'" label="执行时间" required>
          <el-date-picker 
            v-model="newTaskForm.config.dateTime" 
            type="datetime" 
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm:00"
            placeholder="选择日期时间"
          />
        </el-form-item>
        
        <!-- 每周任务配置 -->
        <template v-if="newTaskForm.type === 'weekday'">
          <el-form-item label="执行时间" required>
            <el-time-picker 
              v-model="newTaskForm.config.time" 
              format="HH:mm" 
              value-format="HH:mm"
              placeholder="选择时间"
            />
          </el-form-item>
          <el-form-item label="星期" required>
            <el-checkbox-group v-model="newTaskForm.config.dayOfWeek">
              <el-checkbox label="周一" />
              <el-checkbox label="周二" />
              <el-checkbox label="周三" />
              <el-checkbox label="周四" />
              <el-checkbox label="周五" />
              <el-checkbox label="周六" />
              <el-checkbox label="周日" />
            </el-checkbox-group>
          </el-form-item>
        </template>
        
        <!-- 每月任务配置 -->
        <template v-if="newTaskForm.type === 'monthly'">
          <el-form-item label="执行时间" required>
            <el-time-picker 
              v-model="newTaskForm.config.time" 
              format="HH:mm" 
              value-format="HH:mm"
              placeholder="选择时间"
            />
          </el-form-item>
          <el-form-item label="日期" required>
            <el-select v-model="newTaskForm.config.monthDay" multiple placeholder="选择日期" style="width: 100%;">
              <el-option v-for="day in 31" :key="day" 
                         :label="`${day}号`" 
                         :value="String(day).padStart(2, '0')" />
            </el-select>
          </el-form-item>
        </template>
        
        <el-form-item v-if="newTaskForm.type === 'minute'" label="说明">
          <el-alert 
            type="info" 
            :closable="false"
            show-icon
          >
            此任务将每分钟执行一次
          </el-alert>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="editTaskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdateTask">保存</el-button>
      </template>
    </el-dialog>

    <!-- 执行历史对话框 -->
    <el-dialog 
      v-model="historyDialogVisible" 
      :title="`执行历史 - ${currentTask?.name}`" 
      width="700px"
    >
      <el-timeline v-if="currentTask?.executionHistory && currentTask.executionHistory.length > 0">
        <el-timeline-item 
          v-for="(record, index) in currentTask.executionHistory" 
          :key="index"
          :type="record.status === 'success' ? 'success' : 'danger'"
          :icon="record.status === 'success' ? SuccessFilled : Warning"
        >
          <el-card>
            <div style="margin-bottom: 8px;">
              <strong style="font-size: 14px;">{{ record.time }}</strong>
            </div>
            <div style="margin-bottom: 5px;">
              状态: 
              <el-tag :type="record.status === 'success' ? 'success' : 'danger'" size="small">
                {{ record.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </div>
            <div style="margin-bottom: 5px;">耗时: <el-tag size="small">{{ record.duration }}</el-tag></div>
            <div v-if="record.error" style="color: #F56C6C; margin-top: 8px; padding: 8px; background-color: #FEF0F0; border-radius: 4px;">
              <el-icon style="margin-right: 5px;"><Warning /></el-icon>
              错误: {{ record.error }}
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无执行历史" />
    </el-dialog>
  </div>
</template>

<script setup>
import {
  Plus,
  Timer,
  Edit,
  Delete,
  Clock,
  Warning,
  SuccessFilled,
  VideoPlay,
  VideoPause
} from '@element-plus/icons-vue'
import { taskTypeMap } from '@/constants'
import {
  formatTaskConfig,
  calculateNextRunTime,
  getRelativeTime
} from '@/utils'
import { useTaskScheduler } from '@/composables'

const {
  scheduledTasks,
  addTaskDialogVisible,
  editTaskDialogVisible,
  historyDialogVisible,
  currentTask,
  newTaskForm,
  totalTasksCount,
  enabledTasksCount,
  disabledTasksCount,
  handleToggleTaskStatus,
  handleDeleteTask,
  handleShowHistory,
  handleEditTask,
  handleSaveTask,
  handleUpdateTask
} = useTaskScheduler()
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

/* 按钮渐变优化 */
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

:deep(.el-button--warning) {
  background: linear-gradient(135deg, #e6a23c 0%, #d18b2a 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--warning:hover) {
  background: linear-gradient(135deg, #ebb563 0%, #e6a23c 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(230, 162, 60, 0.45) !important;
}

:deep(.el-button--default) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-button--default:hover) {
  transform: translateY(-2px);
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

:deep(.el-tag--info) {
  background: linear-gradient(135deg, rgba(144, 147, 153, 0.9) 0%, rgba(144, 147, 153, 0.8) 100%);
  color: #ffffff;
}

/* 统计组件优化 */
:deep(.el-statistic) {
  text-align: center;
  padding: 16px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.03) 0%, rgba(103, 194, 58, 0.03) 100%);
  border-radius: 12px;
  border: 1px solid rgba(64, 158, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-statistic:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.15);
}

:deep(.el-statistic__head) {
  color: #909399;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
}

:deep(.el-statistic__content) {
  font-size: 32px;
  font-weight: 700;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
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

:deep(.el-table tbody tr:hover > td) {
  background: rgba(64, 158, 255, 0.03) !important;
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

:deep(.el-dialog .el-button--default) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-dialog .el-button--default:hover) {
  transform: translateY(-2px);
}

/* Alert美化 */
:deep(.el-alert) {
  border-radius: 8px;
  border-left: 4px solid;
}

:deep(.el-alert--info) {
  border-left-color: #409eff;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.05) 0%, rgba(64, 158, 255, 0.02) 100%);
}

/* Timeline卡片圆角 */
:deep(.el-timeline .el-card) {
  border-radius: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-timeline .el-card:hover) {
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.1);
}
</style>

