<template>
  <div class="settings-page">
    <!-- 页面标题卡片 -->
    <el-card class="header-card" shadow="hover">
      <div class="page-header">
        <h2>系统设置</h2>
        <el-button :icon="Refresh" @click="loadAllConfig">刷新所有配置</el-button>
      </div>
    </el-card>

    <!-- 卡片1: 基础配置 -->
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">基础配置</span>
          <el-icon><Setting /></el-icon>
        </div>
      </template>

      <el-form
        ref="basicFormRef"
        :model="basicForm"
        label-width="140px"
        label-position="left"
      >
        <el-form-item :label="basicForm.devMode ? '开发模式' : '生产模式'">
          <div class="form-item-with-hint">
            <el-switch
              v-model="basicForm.devMode"
              active-text="开启"
              inactive-text="关闭"
            />
            <el-text type="info" size="small" class="hint-text">
              开发模式下可调整更多参数
            </el-text>
          </div>
        </el-form-item>

        <el-form-item
          v-if="basicForm.devMode"
          label="交易时间检查"
          style="margin-left: 20px;"
        >
          <div class="form-item-with-hint">
            <el-switch
              v-model="basicForm.tradingTimeCheck"
              active-text="开启"
              inactive-text="关闭"
            />
            <el-text type="info" size="small" class="hint-text">
              开启后将检查是否在交易时间内
            </el-text>
          </div>
        </el-form-item>
      </el-form>

      <div class="card-footer">
        <el-button
          type="primary"
          @click="saveBasicConfig"
          :loading="basicSaving"
        >
          保存基础配置
        </el-button>
        <el-button @click="resetBasicForm">重置</el-button>
      </div>
    </el-card>

    <!-- 卡片2: 日志设置 -->
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">日志设置</span>
          <el-icon><Document /></el-icon>
        </div>
      </template>

      <el-form
        ref="loggingFormRef"
        :model="loggingForm"
        label-width="140px"
        label-position="left"
      >
        <el-form-item label="日志级别">
          <div class="form-item-with-hint">
            <el-select v-model="loggingForm.level" style="width: 200px;">
              <el-option label="DEBUG" value="DEBUG" />
              <el-option label="INFO" value="INFO" />
              <el-option label="WARNING" value="WARNING" />
              <el-option label="ERROR" value="ERROR" />
            </el-select>
            <el-text type="info" size="small" class="hint-text">
              控制日志输出的详细程度
            </el-text>
          </div>
        </el-form-item>

        <el-form-item label="文件大小上限">
          <div class="input-with-unit">
            <el-input-number
              v-model="loggingForm.rotationValue"
              :min="10"
              :max="500"
              :step="10"
              controls-position="right"
            />
            <span class="unit-text">MB</span>
            <el-text type="info" size="small" class="hint-text">
              单个日志文件达到此大小后自动轮转
            </el-text>
          </div>
        </el-form-item>

        <el-form-item label="日志保留时间">
          <div class="input-with-unit">
            <el-input-number
              v-model="loggingForm.retentionValue"
              :min="1"
              :max="365"
              :step="1"
              controls-position="right"
            />
            <span class="unit-text">天</span>
            <el-text type="info" size="small" class="hint-text">
              超过保留时间的日志将被自动删除
            </el-text>
          </div>
        </el-form-item>

        <el-form-item label="压缩格式">
          <div class="form-item-with-hint">
            <el-select v-model="loggingForm.compression" style="width: 200px;">
              <el-option label="ZIP" value="zip" />
              <el-option label="TAR.GZ" value="tar.gz" />
              <el-option label="TAR.BZ2" value="tar.bz2" />
            </el-select>
            <el-text type="info" size="small" class="hint-text">
              归档日志文件的压缩格式
            </el-text>
          </div>
        </el-form-item>
      </el-form>

      <div class="card-footer">
        <el-button
          type="primary"
          @click="saveLoggingConfig"
          :loading="loggingSaving"
        >
          保存日志配置
        </el-button>
        <el-button @click="resetLoggingForm">重置</el-button>
      </div>
    </el-card>

    <!-- 卡片3: 钉钉通知配置 -->
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">钉钉通知配置</span>
          <el-icon><ChatDotRound /></el-icon>
        </div>
      </template>

      <el-form
        ref="dingtalkFormRef"
        :model="dingtalkForm"
        :rules="dingtalkRules"
        label-width="140px"
        label-position="left"
      >
        <el-form-item label="启用钉钉通知">
          <el-switch
            v-model="dingtalkForm.enabled"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>

        <div :class="{ 'disabled-inputs': !dingtalkForm.enabled }">
          <el-form-item label="机器人名称" prop="name">
            <el-input
              v-model="dingtalkForm.name"
              placeholder="请输入钉钉机器人名称"
              style="width: 400px;"
              :disabled="!dingtalkForm.enabled"
            />
          </el-form-item>

          <el-form-item label="机器人ID" prop="id">
            <el-input
              v-model="dingtalkForm.id"
              placeholder="请输入钉钉机器人ID"
              style="width: 400px;"
              :disabled="!dingtalkForm.enabled"
            />
          </el-form-item>

          <el-form-item label="Webhook地址" prop="webhookUrl">
            <el-input
              v-model="dingtalkForm.webhookUrl"
              placeholder="请输入钉钉Webhook地址"
              style="width: 400px;"
              :disabled="!dingtalkForm.enabled"
            >
              <template #prepend>
                <el-icon><Link /></el-icon>
              </template>
            </el-input>
          </el-form-item>
        </div>
      </el-form>

      <div class="card-footer">
        <el-button
          type="primary"
          @click="saveDingtalkConfig"
          :loading="dingtalkSaving"
        >
          保存钉钉配置
        </el-button>
        <el-button @click="resetDingtalkForm">重置</el-button>
      </div>
    </el-card>

    <!-- 卡片4: 企业微信通知配置 -->
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">企业微信通知配置</span>
          <el-icon><Message /></el-icon>
        </div>
      </template>

      <el-form
        ref="wecomFormRef"
        :model="wecomForm"
        :rules="wecomRules"
        label-width="140px"
        label-position="left"
      >
        <el-form-item label="启用企业微信通知">
          <el-switch
            v-model="wecomForm.enabled"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>

        <div :class="{ 'disabled-inputs': !wecomForm.enabled }">
          <el-form-item label="机器人名称" prop="name">
            <el-input
              v-model="wecomForm.name"
              placeholder="请输入企业微信机器人名称"
              style="width: 400px;"
              :disabled="!wecomForm.enabled"
            />
          </el-form-item>

          <el-form-item label="企业微信ID" prop="corpId">
            <el-input
              v-model="wecomForm.corpId"
              placeholder="请输入企业微信ID"
              style="width: 400px;"
              :disabled="!wecomForm.enabled"
            />
          </el-form-item>

          <el-form-item label="应用ID" prop="agentId">
            <el-input
              v-model="wecomForm.agentId"
              placeholder="请输入应用ID"
              style="width: 400px;"
              :disabled="!wecomForm.enabled"
            />
          </el-form-item>

          <el-form-item label="应用密钥" prop="appSecret">
            <el-input
              v-model="wecomForm.appSecret"
              :type="wecomForm.showSecret ? 'text' : 'password'"
              placeholder="请输入企业微信应用密钥"
              style="width: 400px;"
              :disabled="!wecomForm.enabled"
            >
              <template #append>
                <el-checkbox
                  v-model="wecomForm.showSecret"
                  :disabled="!wecomForm.enabled"
                >
                  显示明文
                </el-checkbox>
              </template>
            </el-input>
          </el-form-item>
        </div>
      </el-form>

      <div class="card-footer">
        <el-button
          type="primary"
          @click="saveWecomConfig"
          :loading="wecomSaving"
        >
          保存企业微信配置
        </el-button>
        <el-button @click="resetWecomForm">重置</el-button>
      </div>
    </el-card>

    <!-- 卡片5: 邮箱通知配置 -->
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">邮箱通知配置</span>
          <el-icon><Promotion /></el-icon>
        </div>
      </template>

      <el-form
        ref="emailFormRef"
        :model="emailForm"
        :rules="emailRules"
        label-width="140px"
        label-position="left"
      >
        <el-form-item label="启用邮箱通知">
          <el-switch
            v-model="emailForm.enabled"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>

        <div :class="{ 'disabled-inputs': !emailForm.enabled }">
          <el-form-item label="邮箱地址" prop="address">
            <el-input
              v-model="emailForm.address"
              placeholder="请输入邮箱地址"
              style="width: 400px;"
              :disabled="!emailForm.enabled"
            >
              <template #prepend>
                <el-icon><Message /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="SMTP服务器" prop="smtpServer">
            <el-input
              v-model="emailForm.smtpServer"
              placeholder="请输入SMTP服务器地址"
              style="width: 400px;"
              :disabled="!emailForm.enabled"
            >
              <template #prepend>
                <el-icon><Monitor /></el-icon>
              </template>
            </el-input>
          </el-form-item>
        </div>
      </el-form>

      <div class="card-footer">
        <el-button
          type="primary"
          @click="saveEmailConfig"
          :loading="emailSaving"
        >
          保存邮箱配置
        </el-button>
        <el-button @click="resetEmailForm">重置</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Setting,
  Document,
  ChatDotRound,
  Message,
  Promotion,
  Refresh,
  Link,
  Monitor
} from '@element-plus/icons-vue'
import {
  getSystemConfig,
  updateSystemConfig,
  getNotificationConfig,
  updateNotificationConfig,
  getLoggingConfig,
  updateLoggingConfig
} from '@/api/system'

// ========== 表单引用 ==========
const basicFormRef = ref(null)
const loggingFormRef = ref(null)
const dingtalkFormRef = ref(null)
const wecomFormRef = ref(null)
const emailFormRef = ref(null)

// ========== 基础配置表单 ==========
const basicForm = reactive({
  devMode: true,
  tradingTimeCheck: false
})
const basicSaving = ref(false)
const originalBasicForm = { ...basicForm }

// ========== 日志配置表单 ==========
const loggingForm = reactive({
  level: 'INFO',
  rotationValue: 50,
  retentionValue: 14,
  compression: 'zip'
})
const loggingSaving = ref(false)
const originalLoggingForm = { ...loggingForm }

// ========== 钉钉配置表单 ==========
const dingtalkForm = reactive({
  enabled: false,
  name: '',
  id: '',
  webhookUrl: ''
})
const dingtalkSaving = ref(false)
const originalDingtalkForm = { ...dingtalkForm }

// ========== 企业微信配置表单 ==========
const wecomForm = reactive({
  enabled: false,
  name: '',
  corpId: '',
  agentId: '',
  appSecret: '',
  showSecret: false
})
const wecomSaving = ref(false)
const originalWecomForm = { ...wecomForm }

// ========== 邮箱配置表单 ==========
const emailForm = reactive({
  enabled: false,
  address: '',
  smtpServer: ''
})
const emailSaving = ref(false)
const originalEmailForm = { ...emailForm }

// ========== 验证规则 ==========
const dingtalkRules = computed(() => {
  if (!dingtalkForm.enabled) return {}
  return {
    name: [{ required: true, message: '请输入机器人名称', trigger: 'blur' }],
    id: [{ required: true, message: '请输入机器人ID', trigger: 'blur' }],
    webhookUrl: [
      { required: true, message: '请输入Webhook地址', trigger: 'blur' },
      { type: 'url', message: '请输入正确的URL格式', trigger: 'blur' }
    ]
  }
})

const wecomRules = computed(() => {
  if (!wecomForm.enabled) return {}
  return {
    name: [{ required: true, message: '请输入机器人名称', trigger: 'blur' }],
    corpId: [{ required: true, message: '请输入企业微信ID', trigger: 'blur' }],
    agentId: [{ required: true, message: '请输入应用ID', trigger: 'blur' }],
    appSecret: [{ required: true, message: '请输入应用密钥', trigger: 'blur' }]
  }
})

const emailRules = computed(() => {
  if (!emailForm.enabled) return {}
  return {
    address: [
      { required: true, message: '请输入邮箱地址', trigger: 'blur' },
      { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
    ],
    smtpServer: [{ required: true, message: '请输入SMTP服务器', trigger: 'blur' }]
  }
})

// ========== 加载配置 ==========
const loadAllConfig = async () => {
  await loadSystemConfig()
  await loadLoggingConfig()
  await loadNotificationConfig()
  ElMessage.success('所有配置已刷新')
}

const loadSystemConfig = async () => {
  try {
    const response = await getSystemConfig()
    console.log('获取系统配置:', response)

    if (response.dev_mode !== undefined) {
      basicForm.devMode = response.dev_mode
      originalBasicForm.devMode = response.dev_mode
    }
    if (response.dev_trading_hours_check !== undefined) {
      basicForm.tradingTimeCheck = response.dev_trading_hours_check
      originalBasicForm.tradingTimeCheck = response.dev_trading_hours_check
    }

    console.log('系统配置已加载')
  } catch (error) {
    console.error('加载系统配置失败:', error)
    ElMessage.error('加载系统配置失败')
  }
}

const loadLoggingConfig = async () => {
  try {
    const response = await getLoggingConfig()
    console.log('获取日志配置:', response)

    if (response) {
      loggingForm.level = response.level

      // 拆分 rotation (例如 "50 MB" -> 50)
      if (response.rotation) {
        const rotationMatch = response.rotation.match(/^(\d+)/)
        loggingForm.rotationValue = rotationMatch ? parseInt(rotationMatch[1]) : 50
        originalLoggingForm.rotationValue = loggingForm.rotationValue
      }

      // 拆分 retention (例如 "14 days" -> 14)
      if (response.retention) {
        const retentionMatch = response.retention.match(/^(\d+)/)
        loggingForm.retentionValue = retentionMatch ? parseInt(retentionMatch[1]) : 14
        originalLoggingForm.retentionValue = loggingForm.retentionValue
      }

      loggingForm.compression = response.compression
      originalLoggingForm.level = response.level
      originalLoggingForm.compression = response.compression
    }

    console.log('日志配置已加载')
  } catch (error) {
    console.error('加载日志配置失败:', error)
    ElMessage.warning('加载日志配置失败，使用默认配置')
  }
}

const loadNotificationConfig = async () => {
  try {
    const response = await getNotificationConfig()
    console.log('获取通知配置:', response)

    // 更新钉钉配置
    if (response.dingtalk) {
      dingtalkForm.enabled = response.dingtalk.enabled
      dingtalkForm.name = response.dingtalk.name
      dingtalkForm.id = response.dingtalk.id
      dingtalkForm.webhookUrl = response.dingtalk.webhookUrl
      Object.assign(originalDingtalkForm, { ...dingtalkForm })
    }

    // 更新企业微信配置
    if (response.wecom) {
      wecomForm.enabled = response.wecom.enabled
      wecomForm.name = response.wecom.name
      wecomForm.corpId = response.wecom.corpId
      wecomForm.agentId = response.wecom.agentId
      wecomForm.appSecret = response.wecom.appSecret
      Object.assign(originalWecomForm, { ...wecomForm, showSecret: false })
    }

    // 更新邮件配置
    if (response.email) {
      emailForm.enabled = response.email.enabled
      emailForm.address = response.email.address
      emailForm.smtpServer = response.email.smtpServer
      Object.assign(originalEmailForm, { ...emailForm })
    }

    console.log('通知配置已加载')
  } catch (error) {
    console.error('加载通知配置失败:', error)
    ElMessage.warning('加载通知配置失败，使用默认配置')
  }
}

// ========== 保存配置 ==========
const saveBasicConfig = async () => {
  basicSaving.value = true
  try {
    const config = {
      dev_mode: basicForm.devMode,
      dev_trading_hours_check: basicForm.tradingTimeCheck
    }

    console.log('保存系统配置:', config)
    const response = await updateSystemConfig(config)
    console.log('系统配置保存响应:', response)

    Object.assign(originalBasicForm, { ...basicForm })
    ElMessage.success('基础配置保存成功')
  } catch (error) {
    console.error('保存系统配置失败:', error)
    ElMessage.error('基础配置保存失败')
  } finally {
    basicSaving.value = false
  }
}

const saveLoggingConfig = async () => {
  loggingSaving.value = true
  try {
    const config = {
      level: loggingForm.level,
      rotation: `${loggingForm.rotationValue} MB`,
      retention: `${loggingForm.retentionValue} days`,
      compression: loggingForm.compression
    }

    console.log('保存日志配置:', config)
    const response = await updateLoggingConfig(config)
    console.log('日志配置保存响应:', response)

    Object.assign(originalLoggingForm, { ...loggingForm })
    ElMessage.success('日志配置保存成功')
  } catch (error) {
    console.error('保存日志配置失败:', error)
    ElMessage.error('日志配置保存失败')
  } finally {
    loggingSaving.value = false
  }
}

const saveDingtalkConfig = async () => {
  // 如果启用，先验证表单
  if (dingtalkForm.enabled) {
    const valid = await dingtalkFormRef.value?.validate().catch(() => false)
    if (!valid) {
      ElMessage.warning('请完整填写钉钉配置信息')
      return
    }
  }

  dingtalkSaving.value = true
  try {
    const config = {
      dingtalk: {
        enabled: dingtalkForm.enabled,
        name: dingtalkForm.name,
        id: dingtalkForm.id,
        webhookUrl: dingtalkForm.webhookUrl
      }
    }

    console.log('保存钉钉配置:', config)
    const response = await updateNotificationConfig(config)
    console.log('钉钉配置保存响应:', response)

    Object.assign(originalDingtalkForm, { ...dingtalkForm })
    ElMessage.success('钉钉配置保存成功')
  } catch (error) {
    console.error('保存钉钉配置失败:', error)
    ElMessage.error('钉钉配置保存失败')
  } finally {
    dingtalkSaving.value = false
  }
}

const saveWecomConfig = async () => {
  // 如果启用，先验证表单
  if (wecomForm.enabled) {
    const valid = await wecomFormRef.value?.validate().catch(() => false)
    if (!valid) {
      ElMessage.warning('请完整填写企业微信配置信息')
      return
    }
  }

  wecomSaving.value = true
  try {
    const config = {
      wecom: {
        enabled: wecomForm.enabled,
        name: wecomForm.name,
        corpId: wecomForm.corpId,
        agentId: wecomForm.agentId,
        appSecret: wecomForm.appSecret
      }
    }

    console.log('保存企业微信配置:', config)
    const response = await updateNotificationConfig(config)
    console.log('企业微信配置保存响应:', response)

    Object.assign(originalWecomForm, { ...wecomForm, showSecret: false })
    ElMessage.success('企业微信配置保存成功')
  } catch (error) {
    console.error('保存企业微信配置失败:', error)
    ElMessage.error('企业微信配置保存失败')
  } finally {
    wecomSaving.value = false
  }
}

const saveEmailConfig = async () => {
  // 如果启用，先验证表单
  if (emailForm.enabled) {
    const valid = await emailFormRef.value?.validate().catch(() => false)
    if (!valid) {
      ElMessage.warning('请完整填写邮箱配置信息')
      return
    }
  }

  emailSaving.value = true
  try {
    const config = {
      email: {
        enabled: emailForm.enabled,
        address: emailForm.address,
        smtpServer: emailForm.smtpServer
      }
    }

    console.log('保存邮箱配置:', config)
    const response = await updateNotificationConfig(config)
    console.log('邮箱配置保存响应:', response)

    Object.assign(originalEmailForm, { ...emailForm })
    ElMessage.success('邮箱配置保存成功')
  } catch (error) {
    console.error('保存邮箱配置失败:', error)
    ElMessage.error('邮箱配置保存失败')
  } finally {
    emailSaving.value = false
  }
}

// ========== 重置表单 ==========
const resetBasicForm = () => {
  Object.assign(basicForm, originalBasicForm)
  ElMessage.info('已重置基础配置')
}

const resetLoggingForm = () => {
  Object.assign(loggingForm, originalLoggingForm)
  ElMessage.info('已重置日志配置')
}

const resetDingtalkForm = () => {
  Object.assign(dingtalkForm, originalDingtalkForm)
  dingtalkFormRef.value?.clearValidate()
  ElMessage.info('已重置钉钉配置')
}

const resetWecomForm = () => {
  Object.assign(wecomForm, originalWecomForm)
  wecomForm.showSecret = false
  wecomFormRef.value?.clearValidate()
  ElMessage.info('已重置企业微信配置')
}

const resetEmailForm = () => {
  Object.assign(emailForm, originalEmailForm)
  emailFormRef.value?.clearValidate()
  ElMessage.info('已重置邮箱配置')
}

// ========== 生命周期 ==========
onMounted(() => {
  loadAllConfig()
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

/* 页面布局 */
.settings-page {
  padding: 0;
}

/* 页面标题卡片 */
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

/* 配置卡片 */
.config-card {
  margin-bottom: 20px;
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

/* 卡片底部按钮区优化 */
.card-footer {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 2px solid rgba(64, 158, 255, 0.1);
  display: flex;
  gap: 12px;
}

/* 表单项布局 */
.form-item-with-hint {
  display: flex;
  align-items: center;
  gap: 20px;
}

.input-with-unit {
  display: flex;
  align-items: center;
  gap: 10px;
}

.unit-text {
  font-weight: 600;
  color: #606266;
  min-width: 30px;
}

.hint-text {
  color: #909399;
  font-size: 13px;
  line-height: 1.5;
}

/* 禁用输入框样式 */
.disabled-inputs {
  opacity: 0.5;
  transition: opacity 0.3s ease;
}

/* 表单样式微调 */
:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-form-item__label) {
  font-weight: 600;
  color: #606266;
}

:deep(.el-input-number) {
  width: 150px;
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

:deep(.el-button--default) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-button--default:hover) {
  transform: translateY(-2px);
}

/* Switch开关美化 */
:deep(.el-switch.is-checked .el-switch__core) {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%) !important;
  border-color: transparent !important;
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

/* Select下拉框优化 */
:deep(.el-select .el-input__wrapper) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-select .el-input__wrapper:hover) {
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}

:deep(.el-select .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
}

/* Input输入框优化 */
:deep(.el-input__wrapper) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
}
</style>
