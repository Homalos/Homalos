/**
 * 任务调度器逻辑 Composable
 */
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { scheduledTasksData } from '@/mock'
import { getCurrentTime, calculateNextRunTime, getRelativeTime, formatTaskConfig, generateTaskId } from '@/utils'

export function useTaskScheduler() {
  // ===== 状态管理 =====
  const scheduledTasks = ref(scheduledTasksData)
  
  // 对话框状态
  const addTaskDialogVisible = ref(false)
  const editTaskDialogVisible = ref(false)
  const historyDialogVisible = ref(false)
  const currentTask = ref(null)
  
  // 新任务表单数据
  const newTaskForm = reactive({
    name: '',
    type: 'daily',
    config: {
      time: '09:00',
      dateTime: '',
      dayOfWeek: [],
      monthDay: []
    }
  })

  // ===== 计算属性 =====
  const totalTasksCount = computed(() => scheduledTasks.value.length)
  
  const enabledTasksCount = computed(() => 
    scheduledTasks.value.filter(t => t.status === 'enabled').length
  )
  
  const disabledTasksCount = computed(() => 
    scheduledTasks.value.filter(t => t.status === 'disabled').length
  )

  // ===== 方法 =====
  
  /**
   * 启用/禁用任务
   */
  const handleToggleTaskStatus = (task) => {
    task.status = task.status === 'enabled' ? 'disabled' : 'enabled'
    const statusText = task.status === 'enabled' ? '启用' : '禁用'
    ElMessage.success(`任务 "${task.name}" 已${statusText}`)
  }

  /**
   * 删除任务
   */
  const handleDeleteTask = (taskId) => {
    ElMessageBox.confirm(
      '确定要删除这个任务吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      const index = scheduledTasks.value.findIndex(t => t.id === taskId)
      if (index !== -1) {
        const taskName = scheduledTasks.value[index].name
        scheduledTasks.value.splice(index, 1)
        ElMessage.success(`任务 "${taskName}" 已删除`)
      }
    }).catch(() => {
      // 用户取消删除
    })
  }

  /**
   * 显示执行历史
   */
  const handleShowHistory = (task) => {
    currentTask.value = task
    historyDialogVisible.value = true
  }

  /**
   * 编辑任务
   */
  const handleEditTask = (task) => {
    currentTask.value = task
    newTaskForm.name = task.name
    newTaskForm.type = task.type
    newTaskForm.config = { ...task.config }
    editTaskDialogVisible.value = true
  }

  /**
   * 保存新任务
   */
  const handleSaveTask = () => {
    if (!newTaskForm.name.trim()) {
      ElMessage.warning('请输入任务名称')
      return
    }
    
    // 验证配置
    if (newTaskForm.type === 'daily' && !newTaskForm.config.time) {
      ElMessage.warning('请选择执行时间')
      return
    }
    if (newTaskForm.type === 'once' && !newTaskForm.config.dateTime) {
      ElMessage.warning('请选择执行时间')
      return
    }
    if (newTaskForm.type === 'weekday') {
      if (!newTaskForm.config.time || newTaskForm.config.dayOfWeek.length === 0) {
        ElMessage.warning('请选择执行时间和星期')
        return
      }
    }
    if (newTaskForm.type === 'monthly') {
      if (!newTaskForm.config.time || newTaskForm.config.monthDay.length === 0) {
        ElMessage.warning('请选择执行时间和日期')
        return
      }
    }
    
    const newTask = {
      id: generateTaskId(scheduledTasks.value),
      name: newTaskForm.name,
      type: newTaskForm.type,
      config: { ...newTaskForm.config },
      status: 'disabled',
      createTime: getCurrentTime(),
      lastExecuteTime: null,
      executionHistory: []
    }
    
    scheduledTasks.value.push(newTask)
    addTaskDialogVisible.value = false
    
    // 重置表单
    newTaskForm.name = ''
    newTaskForm.type = 'daily'
    newTaskForm.config = {
      time: '09:00',
      dateTime: '',
      dayOfWeek: [],
      monthDay: []
    }
    
    ElMessage.success(`任务 "${newTask.name}" 已添加`)
  }

  /**
   * 更新任务
   */
  const handleUpdateTask = () => {
    if (!newTaskForm.name.trim()) {
      ElMessage.warning('请输入任务名称')
      return
    }
    
    const task = currentTask.value
    task.name = newTaskForm.name
    task.type = newTaskForm.type
    task.config = { ...newTaskForm.config }
    
    editTaskDialogVisible.value = false
    ElMessage.success(`任务 "${task.name}" 已更新`)
  }

  return {
    // 状态
    scheduledTasks,
    addTaskDialogVisible,
    editTaskDialogVisible,
    historyDialogVisible,
    currentTask,
    newTaskForm,
    
    // 计算属性
    totalTasksCount,
    enabledTasksCount,
    disabledTasksCount,
    
    // 方法
    handleToggleTaskStatus,
    handleDeleteTask,
    handleShowHistory,
    handleEditTask,
    handleSaveTask,
    handleUpdateTask,
    
    // 工具方法（透传）
    calculateNextRunTime,
    getRelativeTime,
    formatTaskConfig
  }
}

