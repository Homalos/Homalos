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
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="任务名称" width="150" />
        <el-table-column label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag :color="taskTypeMap[row.type].color" style="color: white;">
              {{ taskTypeMap[row.type].name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行配置" width="200">
          <template #default="{ row }">
            {{ formatTaskConfig(row) }}
          </template>
        </el-table-column>
        <el-table-column label="下次执行" width="180">
          <template #default="{ row }">
            {{ getRelativeTime(calculateNextRunTime(row)) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'enabled' ? 'success' : 'info'">
              {{ row.status === 'enabled' ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300">
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
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

