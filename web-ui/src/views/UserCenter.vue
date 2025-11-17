<template>
  <div class="user-center">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="title">用户中心</span>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="border-card">
        <!-- 个人资料 -->
        <el-tab-pane label="个人资料" name="profile">
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-width="100px"
            style="max-width: 600px; margin: 20px auto;"
          >
            <!-- 头像 -->
            <el-form-item label="头像">
              <div class="avatar-container">
                <el-avatar :size="100" :src="profileForm.avatar_url || undefined">
                  <el-icon :size="40"><User /></el-icon>
                </el-avatar>
                <el-button size="small" style="margin-left: 20px;" @click="handleUploadAvatar">
                  更换头像
                </el-button>
              </div>
            </el-form-item>

            <!-- 基本信息 -->
            <el-divider content-position="left">基本信息</el-divider>

            <el-form-item label="用户名">
              <el-input v-model="profileForm.username" disabled />
              <span class="form-tip">用户名不可修改</span>
            </el-form-item>

            <el-form-item label="全名" prop="full_name">
              <el-input
                v-model="profileForm.full_name"
                placeholder="请输入真实姓名（可选）"
                clearable
              />
            </el-form-item>

            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="profileForm.email"
                type="email"
                placeholder="请输入邮箱地址"
                clearable
              />
            </el-form-item>

            <el-form-item label="手机号" prop="phone">
              <el-input
                v-model="profileForm.phone"
                placeholder="请输入手机号（可选）"
                clearable
              />
            </el-form-item>

            <!-- 系统设置 -->
            <el-divider content-position="left">系统设置</el-divider>

            <el-form-item label="时区" prop="timezone">
              <el-select
                v-model="profileForm.timezone"
                placeholder="选择时区"
                style="width: 100%"
              >
                <el-option
                  v-for="tz in timezoneOptions"
                  :key="tz.value"
                  :label="tz.label"
                  :value="tz.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="语言" prop="locale">
              <el-select
                v-model="profileForm.locale"
                placeholder="选择语言"
                style="width: 100%"
              >
                <el-option
                  v-for="lang in languageOptions"
                  :key="lang.value"
                  :label="lang.label"
                  :value="lang.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="handleSaveProfile" :loading="saving">
                保存修改
              </el-button>
              <el-button @click="handleResetProfile">重置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 账户安全 -->
        <el-tab-pane label="账户安全" name="security">
          <div style="max-width: 600px; margin: 20px auto;">
            <!-- 修改密码 -->
            <el-card shadow="never" style="margin-bottom: 20px;">
              <template #header>
                <div style="display: flex; align-items: center; justify-content: space-between;">
                  <span><el-icon><Lock /></el-icon> 登录密码</span>
                  <el-button type="primary" size="small" @click="showPasswordDialog = true">
                    修改密码
                  </el-button>
                </div>
              </template>
              <p style="color: #909399; margin: 0;">
                定期更换密码可以提高账户安全性
              </p>
            </el-card>

            <!-- 登录历史 -->
            <el-card shadow="never">
              <template #header>
                <span><el-icon><Clock /></el-icon> 最近登录</span>
              </template>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="最后登录时间">
                  {{ userStore.userInfo?.last_login_at ? formatDateTime(userStore.userInfo.last_login_at) : '暂无记录' }}
                </el-descriptions-item>
                <el-descriptions-item label="账户创建时间">
                  {{ userStore.userInfo?.created_at ? formatDateTime(userStore.userInfo.created_at) : '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="账户状态">
                  <el-tag :type="getStatusType(userStore.userInfo?.status)">
                    {{ getStatusText(userStore.userInfo?.status) }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 系统偏好 -->
        <el-tab-pane label="系统偏好" name="preferences">
          <el-form
            ref="preferencesFormRef"
            :model="preferencesForm"
            label-width="120px"
            style="max-width: 600px; margin: 20px auto;"
          >
            <el-divider content-position="left">界面设置</el-divider>

            <el-form-item label="主题">
              <el-radio-group v-model="preferencesForm.theme">
                <el-radio label="light">
                  <span class="radio-label">浅色主题</span>
                  <span class="radio-desc">适合白天使用</span>
                </el-radio>
                <el-radio label="dark">
                  <span class="radio-label">深色主题</span>
                  <span class="radio-desc">适合夜间使用</span>
                </el-radio>
                <el-radio label="auto">
                  <span class="radio-label">跟随系统</span>
                  <span class="radio-desc">根据系统设置自动切换</span>
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="handleSavePreferences" :loading="saving">
                保存设置
              </el-button>
              <el-button @click="handleResetPreferences">恢复默认</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 通知设置 -->
        <el-tab-pane label="通知设置" name="notifications">
          <el-form
            label-width="120px"
            style="max-width: 600px; margin: 20px auto;"
          >
            <el-divider content-position="left">系统通知</el-divider>

            <el-form-item label="浏览器通知">
              <el-switch
                v-model="preferencesForm.browser_notification_enabled"
                active-text="开启"
                inactive-text="关闭"
              />
            </el-form-item>

            <el-form-item label="声音提示">
              <el-switch
                v-model="preferencesForm.sound_enabled"
                active-text="开启"
                inactive-text="关闭"
              />
            </el-form-item>

            <el-divider content-position="left">邮件通知</el-divider>

            <el-form-item label="交易通知">
              <el-switch
                v-model="preferencesForm.email_trade_notification"
                active-text="开启"
                inactive-text="关闭"
              />
              <span class="form-tip">订单成交、持仓变化等</span>
            </el-form-item>

            <el-form-item label="告警通知">
              <el-switch
                v-model="preferencesForm.email_alarm_notification"
                active-text="开启"
                inactive-text="关闭"
              />
              <span class="form-tip">价格告警、系统告警等</span>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="handleSavePreferences" :loading="saving">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="showPasswordDialog"
      title="修改密码"
      width="500px"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
      >
        <el-form-item label="当前密码" prop="old_password">
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            placeholder="请输入当前密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            placeholder="请输入新密码（至少6位）"
            show-password
          />
          <div class="password-strength">
            <div class="strength-bar">
              <div 
                class="strength-fill" 
                :class="passwordStrengthClass"
                :style="{ width: passwordStrengthWidth }"
              ></div>
            </div>
            <span class="strength-text">{{ passwordStrengthText }}</span>
          </div>
        </el-form-item>

        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword" :loading="saving">
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Lock, Clock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 当前激活的标签页
const activeTab = ref('profile')
const saving = ref(false)

// 表单引用
const profileFormRef = ref(null)
const preferencesFormRef = ref(null)
const passwordFormRef = ref(null)

// 修改密码对话框
const showPasswordDialog = ref(false)

// 个人资料表单
const profileForm = reactive({
  username: '',
  full_name: '',
  email: '',
  phone: '',
  avatar_url: '',
  timezone: 'Asia/Shanghai',
  locale: 'zh-CN'
})

// 偏好设置表单
const preferencesForm = reactive({
  theme: 'light',
  browser_notification_enabled: true,
  sound_enabled: true,
  email_trade_notification: false,
  email_alarm_notification: true
})

// 修改密码表单
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

// 时区选项
const timezoneOptions = [
  { value: 'Asia/Shanghai', label: '北京时间 (UTC+8)' },
  { value: 'Asia/Hong_Kong', label: '香港时间 (UTC+8)' },
  { value: 'Asia/Tokyo', label: '东京时间 (UTC+9)' },
  { value: 'America/New_York', label: '纽约时间 (UTC-5)' },
  { value: 'Europe/London', label: '伦敦时间 (UTC+0)' },
  { value: 'UTC', label: '协调世界时 (UTC)' }
]

// 语言选项
const languageOptions = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'en-US', label: 'English' },
  { value: 'ja-JP', label: '日本語' }
]

// 表单验证规则
const profileRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

const passwordRules = {
  old_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value === passwordForm.old_password) {
          callback(new Error('新密码不能与当前密码相同'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 密码强度计算
const passwordStrength = computed(() => {
  const pwd = passwordForm.new_password
  if (!pwd) return 0
  
  let strength = 0
  if (pwd.length >= 6) strength += 1
  if (pwd.length >= 10) strength += 1
  if (pwd.length >= 14) strength += 1
  if (/[a-z]/.test(pwd)) strength += 1
  if (/[A-Z]/.test(pwd)) strength += 1
  if (/\d/.test(pwd)) strength += 1
  if (/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) strength += 1
  
  return Math.min(strength, 4)
})

const passwordStrengthText = computed(() => {
  const texts = ['', '弱', '中等', '强', '很强']
  return texts[passwordStrength.value] || ''
})

const passwordStrengthClass = computed(() => {
  const classes = ['', 'weak', 'medium', 'strong', 'very-strong']
  return classes[passwordStrength.value] || ''
})

const passwordStrengthWidth = computed(() => {
  return `${passwordStrength.value * 25}%`
})

// 加载用户信息
onMounted(() => {
  loadUserProfile()
  loadUserPreferences()
})

function loadUserProfile() {
  const userInfo = userStore.userInfo
  if (userInfo) {
    profileForm.username = userInfo.username || ''
    profileForm.full_name = userInfo.full_name || ''
    profileForm.email = userInfo.email || ''
    profileForm.phone = userInfo.phone || ''
    profileForm.avatar_url = userInfo.avatar_url || ''
    profileForm.timezone = userInfo.timezone || 'Asia/Shanghai'
    profileForm.locale = userInfo.locale || 'zh-CN'
  }
}

function loadUserPreferences() {
  // TODO: 从API加载用户偏好设置
  // 暂时使用默认值
}

// 保存个人资料
async function handleSaveProfile() {
  if (!profileFormRef.value) return
  
  await profileFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      // TODO: 调用API保存个人资料
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      ElMessage.success('个人资料保存成功')
      
      // 更新store中的用户信息
      await userStore.fetchUserInfo()
    } catch (error) {
      ElMessage.error(error.message || '保存失败')
    } finally {
      saving.value = false
    }
  })
}

// 重置个人资料
function handleResetProfile() {
  loadUserProfile()
  ElMessage.info('已重置为原始数据')
}

// 保存偏好设置
async function handleSavePreferences() {
  saving.value = true
  try {
    // TODO: 调用API保存偏好设置
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('偏好设置保存成功')
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

// 恢复默认偏好设置
async function handleResetPreferences() {
  try {
    await ElMessageBox.confirm(
      '确定要恢复默认设置吗？此操作不可撤销。',
      '确认恢复',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 恢复默认值
    preferencesForm.theme = 'light'
    preferencesForm.browser_notification_enabled = true
    preferencesForm.sound_enabled = true
    preferencesForm.email_trade_notification = false
    preferencesForm.email_alarm_notification = true
    
    ElMessage.success('已恢复默认设置')
  } catch {
    // 取消操作
  }
}

// 修改密码
async function handleChangePassword() {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      // TODO: 调用API修改密码
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      ElMessage.success('密码修改成功，请重新登录')
      showPasswordDialog.value = false
      passwordFormRef.value.resetFields()
      
      // 延迟后退出登录
      setTimeout(() => {
        userStore.logout()
      }, 1500)
    } catch (error) {
      ElMessage.error(error.message || '密码修改失败')
    } finally {
      saving.value = false
    }
  })
}

// 上传头像
function handleUploadAvatar() {
  ElMessage.info('头像上传功能开发中...')
}

// 格式化日期时间
function formatDateTime(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 获取状态类型
function getStatusType(status) {
  const types = {
    'ACTIVE': 'success',
    'INACTIVE': 'info',
    'FROZEN': 'warning',
    'DISABLED': 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
function getStatusText(status) {
  const texts = {
    'ACTIVE': '正常',
    'INACTIVE': '未激活',
    'FROZEN': '冻结',
    'DISABLED': '禁用'
  }
  return texts[status] || status
}
</script>

<style scoped>
.user-center {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 18px;
  font-weight: 600;
}

.avatar-container {
  display: flex;
  align-items: center;
}

.form-tip {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.radio-label {
  font-weight: 600;
  margin-right: 8px;
}

.radio-desc {
  font-size: 12px;
  color: #909399;
}

:deep(.el-radio) {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  height: auto;
  white-space: normal;
}

:deep(.el-radio__label) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

/* 密码强度显示 */
.password-strength {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.strength-bar {
  flex: 1;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 3px;
}

.strength-fill.weak {
  background: #f56c6c;
}

.strength-fill.medium {
  background: #e6a23c;
}

.strength-fill.strong {
  background: #409eff;
}

.strength-fill.very-strong {
  background: #67c23a;
}

.strength-text {
  font-size: 12px;
  color: #909399;
  min-width: 40px;
}
</style>
