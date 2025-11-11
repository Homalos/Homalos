<template>
  <div class="alarm-settings">
          <el-card class="header-card" shadow="hover">
      <div class="page-header">
        <h2>告警设置</h2>
        <el-button @click="goBack">返回</el-button>
      </div>
    </el-card>

    <!-- 当前配置预览 -->
    <el-card class="preview-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">当前配置预览</span>
          <el-button :icon="Refresh" size="small" @click="loadConfig">刷新</el-button>
        </div>
      </template>

      <el-descriptions :column="3" border>
        <el-descriptions-item label="CPU告警阈值">
          {{ config.cpu_threshold }}%
        </el-descriptions-item>
        <el-descriptions-item label="内存告警阈值">
          {{ config.memory_threshold }}%
        </el-descriptions-item>
        <el-descriptions-item label="历史保留天数">
          {{ config.retention_days }} 天
        </el-descriptions-item>
        <el-descriptions-item label="邮件通知">
          <el-tag :type="config.email_enabled ? 'success' : 'info'">
            {{ config.email_enabled ? '已启用' : '已禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="WebSocket状态">
          <el-tag :type="wsConnected ? 'success' : 'danger'">
            {{ wsConnected ? '已连接' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="浏览器通知">
          <el-tag :type="browserNotificationEnabled ? 'success' : 'info'">
            {{ browserNotificationEnabled ? '已授权' : '未授权' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 告警阈值配置 -->
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">告警阈值配置</span>
          <el-icon><Setting /></el-icon>
        </div>
      </template>

          <el-form
            ref="thresholdFormRef"
            :model="thresholdForm"
            :rules="thresholdRules"
            label-width="140px"
            label-position="left"
          >
            <el-form-item label="CPU告警阈值" prop="cpu_threshold">
              <div class="slider-with-hint">
                <el-slider
                  v-model="thresholdForm.cpu_threshold"
                  :min="50"
                  :max="100"
                  :step="5"
                  show-input
                  :marks="{ 50: '50%', 75: '75%', 100: '100%' }"
                  class="threshold-slider"
                >
                  <template #default="{ value }">
                    {{ value }}%
                  </template>
                </el-slider>
                <el-text type="info" size="small" class="slider-hint">
                  当CPU使用率持续60秒超过此阈值时触发告警
                </el-text>
              </div>
            </el-form-item>

            <el-form-item label="内存告警阈值" prop="memory_threshold">
              <div class="slider-with-hint">
                <el-slider
                  v-model="thresholdForm.memory_threshold"
                  :min="50"
                  :max="100"
                  :step="5"
                  show-input
                  :marks="{ 50: '50%', 75: '75%', 100: '100%' }"
                  class="threshold-slider"
                >
                  <template #default="{ value }">
                    {{ value }}%
                  </template>
                </el-slider>
                <el-text type="info" size="small" class="slider-hint">
                  当内存使用率持续60秒超过此阈值时触发告警
                </el-text>
              </div>
            </el-form-item>

            <el-form-item label="历史保留天数" prop="retention_days">
              <div class="input-with-hint">
                <el-input-number
                  v-model="thresholdForm.retention_days"
                  :min="1"
                  :max="365"
                  :step="1"
                  controls-position="right"
                />
                <el-text type="info" size="small" class="hint-text">
                  超过此天数的告警记录将被自动清理
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="handleSaveThreshold" :loading="saving">
                保存配置
              </el-button>
              <el-button @click="handleResetThreshold">重置</el-button>
            </el-form-item>
      </el-form>
    </el-card>

    <!-- 通知配置 -->
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">通知配置</span>
          <el-icon><Message /></el-icon>
        </div>
      </template>

      <el-form
        ref="notificationFormRef"
        :model="notificationForm"
        label-width="140px"
        label-position="left"
      >
        <el-form-item label="邮件通知">
          <div class="switch-with-hint">
            <el-switch
              v-model="notificationForm.email_enabled"
              active-text="启用"
              inactive-text="禁用"
            />
            <el-text type="info" size="small" class="switch-hint">
              启用后，error和critical级别的告警将发送邮件通知
            </el-text>
          </div>
        </el-form-item>

        <el-form-item label="WebSocket推送">
          <div class="switch-with-hint">
            <el-switch
              v-model="wsConnected"
              disabled
              active-text="已连接"
              inactive-text="未连接"
            />
            <el-text type="info" size="small" class="switch-hint">
              WebSocket连接状态，所有告警都会实时推送到前端
            </el-text>
          </div>
        </el-form-item>

        <el-form-item label="浏览器通知">
          <div class="switch-with-hint">
            <el-switch
              v-model="browserNotificationEnabled"
              @change="handleBrowserNotificationChange"
              active-text="已授权"
              inactive-text="未授权"
            />
            <el-text type="info" size="small" class="switch-hint">
              启用后，新告警将显示浏览器桌面通知
            </el-text>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSaveNotification" :loading="saving">
            保存配置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 测试告警 -->
    <el-card class="config-card test-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">测试告警</span>
          <el-icon><Bell /></el-icon>
        </div>
      </template>

      <el-form
        ref="testFormRef"
        :model="testForm"
        label-width="140px"
        label-position="left"
      >
        <el-form-item label="告警类型">
          <el-input v-model="testForm.alarm_type" placeholder="test" />
        </el-form-item>

        <el-form-item label="严重程度">
          <el-select v-model="testForm.severity" placeholder="选择严重程度">
            <el-option label="信息" value="info" />
            <el-option label="警告" value="warning" />
            <el-option label="错误" value="error" />
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>

        <el-form-item label="告警消息">
          <el-input
            v-model="testForm.message"
            type="textarea"
            :rows="3"
            placeholder="输入测试告警消息"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="warning" @click="handleTriggerTest" :loading="testing">
            <el-icon><Bell /></el-icon>
            触发测试告警
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAlarmStore } from '@/stores/alarm'
import { ElMessage } from 'element-plus'
import { Setting, Message, Bell, Refresh } from '@element-plus/icons-vue'

const router = useRouter()
const alarmStore = useAlarmStore()

// 表单引用
const thresholdFormRef = ref(null)
const notificationFormRef = ref(null)
const testFormRef = ref(null)

// 状态
const saving = ref(false)
const testing = ref(false)

// 表单数据
const thresholdForm = ref({
  cpu_threshold: 80,
  memory_threshold: 85,
  retention_days: 30
})

const notificationForm = ref({
  email_enabled: true
})

const testForm = ref({
  alarm_type: 'test',
  severity: 'info',
  message: '这是一条测试告警消息'
})

// 表单验证规则
const thresholdRules = {
  cpu_threshold: [
    { required: true, message: '请设置CPU告警阈值', trigger: 'blur' },
    { type: 'number', min: 50, max: 100, message: '阈值范围：50-100', trigger: 'blur' }
  ],
  memory_threshold: [
    { required: true, message: '请设置内存告警阈值', trigger: 'blur' },
    { type: 'number', min: 50, max: 100, message: '阈值范围：50-100', trigger: 'blur' }
  ],
  retention_days: [
    { required: true, message: '请设置历史保留天数', trigger: 'blur' },
    { type: 'number', min: 1, max: 365, message: '保留天数范围：1-365', trigger: 'blur' }
  ]
}

// 计算属性
const config = computed(() => alarmStore.config)
const wsConnected = computed(() => alarmStore.wsConnected)
const browserNotificationEnabled = ref(false)

// 方法
async function loadConfig() {
  try {
    await alarmStore.fetchConfig()
    
    // 更新表单数据
    thresholdForm.value = {
      cpu_threshold: config.value.cpu_threshold,
      memory_threshold: config.value.memory_threshold,
      retention_days: config.value.retention_days
    }
    
    notificationForm.value = {
      email_enabled: config.value.email_enabled
    }
    
    // 检查浏览器通知权限
    checkBrowserNotificationPermission()
  } catch (error) {
    ElMessage.error('加载配置失败: ' + error.message)
  }
}

async function handleSaveThreshold() {
  try {
    await thresholdFormRef.value.validate()
    
    saving.value = true
    await alarmStore.updateConfig(thresholdForm.value)
    ElMessage.success('阈值配置已保存')
  } catch (error) {
    if (error !== false) {
      ElMessage.error('保存配置失败: ' + error.message)
    }
  } finally {
    saving.value = false
  }
}

function handleResetThreshold() {
  thresholdForm.value = {
    cpu_threshold: config.value.cpu_threshold,
    memory_threshold: config.value.memory_threshold,
    retention_days: config.value.retention_days
  }
  thresholdFormRef.value.clearValidate()
}

async function handleSaveNotification() {
  try {
    saving.value = true
    await alarmStore.updateConfig(notificationForm.value)
    ElMessage.success('通知配置已保存')
  } catch (error) {
    ElMessage.error('保存配置失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

async function handleTriggerTest() {
  try {
    testing.value = true
    await alarmStore.triggerTestAlarm(testForm.value)
    ElMessage.success('测试告警已触发，请查看通知中心')
  } catch (error) {
    ElMessage.error('触发测试告警失败: ' + error.message)
  } finally {
    testing.value = false
  }
}

function checkBrowserNotificationPermission() {
  if ('Notification' in window) {
    browserNotificationEnabled.value = Notification.permission === 'granted'
  }
}

async function handleBrowserNotificationChange(enabled) {
  if (enabled && 'Notification' in window) {
    if (Notification.permission === 'default') {
      const permission = await Notification.requestPermission()
      browserNotificationEnabled.value = permission === 'granted'
      
      if (permission !== 'granted') {
        ElMessage.warning('浏览器通知权限被拒绝')
      }
    } else if (Notification.permission === 'denied') {
      ElMessage.error('浏览器通知权限已被拒绝，请在浏览器设置中允许通知')
      browserNotificationEnabled.value = false
    }
  }
}

function goBack() {
  router.push('/alarms')
}

// 生命周期
onMounted(() => {
  loadConfig()
  
  // 连接WebSocket
  if (!alarmStore.wsConnected) {
    alarmStore.connectWebSocket()
  }
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

.header-card {
  margin-bottom: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  position: relative;
  padding-left: 12px;
}

/* h2左侧渐变装饰条 */
.page-header h2::before {
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

.config-card {
  margin-bottom: 20px;
}

.test-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  position: relative;
  padding-left: 12px;
}

/* card-title左侧渐变装饰条 */
.card-title::before {
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

.preview-card {
  margin-bottom: 20px;
}

/* 输入框与提示文字容器 */
.input-with-hint {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.hint-text {
  flex: 1;
}

/* 开关与提示文字容器 */
.switch-with-hint {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.switch-hint {
  flex: 1;
  margin-left: 0;
}

/* 滑块与提示文字容器 */
.slider-with-hint {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.slider-hint {
  flex: 1;
  margin-left: 0;
}

/* 表单项样式优化 */
:deep(.el-form-item) {
  margin-bottom: 32px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  line-height: 32px;
}

:deep(.el-form-item__content) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

/* Slider样式优化 */
:deep(.el-slider) {
  width: 100%;
}

/* 阈值滑块特定样式 */
.threshold-slider {
  width: 600px; /* 设置固定宽度，为提示文字留出空间 */
  flex-shrink: 0; /* 防止滑块被压缩 */
}

/* 提示文字样式 */
:deep(.el-text) {
  display: block;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

/* Input Number样式 */
:deep(.el-input-number) {
  width: 150px;
}

/* Switch样式优化 */
:deep(.el-switch) {
  height: 24px;
}

/* 按钮组样式 */
:deep(.el-form-item:last-child) {
  margin-bottom: 0;
  margin-top: 8px;
}

:deep(.el-form-item:last-child .el-form-item__content) {
  flex-direction: row;
  gap: 12px;
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

/* Descriptions优化 */
:deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
}

:deep(.el-descriptions__content) {
  color: #303133;
}

/* Switch开关美化 */
:deep(.el-switch.is-checked .el-switch__core) {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%) !important;
  border-color: transparent !important;
}

/* Slider滑块美化 */
:deep(.el-slider__runway) {
  background: rgba(64, 158, 255, 0.08);
}

:deep(.el-slider__bar) {
  background: linear-gradient(90deg, #409eff 0%, #67c23a 100%);
}

:deep(.el-slider__button) {
  border: 2px solid #409eff;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

:deep(.el-slider__button:hover) {
  transform: scale(1.2);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}
</style>

