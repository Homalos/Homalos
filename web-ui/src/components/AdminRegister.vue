<template>
  <div class="admin-register">
      <el-alert
        type="warning"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        <template #title>
          <el-icon><Warning /></el-icon>
          管理员注册须知
        </template>
        管理员账户具有系统管理权限，请确保信息准确。超级管理员需要特殊邀请码。
      </el-alert>
      
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        label-width="120px"
        @submit.prevent="handleRegister"
      >
        <!-- 账户类型选择 -->
        <div class="form-section">
          <h4 class="section-title">账户类型</h4>
          
          <el-form-item label="管理员角色" prop="role">
            <el-radio-group v-model="registerForm.role" size="large">
              <div class="radio-wrapper">
                <el-radio label="normal">
                  <div class="role-option">
                    <div class="role-title">
                      <el-icon class="role-icon normal-icon"><UserFilled /></el-icon>
                      普通管理员
                    </div>
                    <div class="role-desc">管理用户账户、交易策略和基础系统功能，适合日常运营管理</div>
                  </div>
                </el-radio>
              </div>
              <div class="radio-wrapper">
                <el-radio label="super">
                  <div class="role-option">
                    <div class="role-title">
                      <el-icon class="role-icon super-icon">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M12,7C13.4,7 14.8,8.6 14.8,10V11.4C14.8,12.8 13.4,14.4 12,14.4C10.6,14.4 9.2,12.8 9.2,11.4V10C9.2,8.6 10.6,7 12,7M18,11C18,15.1 15.1,18 12,18C8.9,18 6,15.1 6,11V6.3L12,3.7L18,6.3V11Z"/>
                        </svg>
                      </el-icon>
                      超级管理员
                    </div>
                    <div class="role-desc">拥有所有系统权限，包括管理其他管理员、系统配置和安全设置</div>
                  </div>
                </el-radio>
              </div>
            </el-radio-group>
          </el-form-item>
          
          <!-- 超级管理员邀请码 -->
          <el-form-item 
            v-if="registerForm.role === 'super'" 
            label="邀请码" 
            prop="invitationCode"
            class="invitation-code-item"
          >
            <el-input
              v-model="registerForm.invitationCode"
              placeholder="请输入超级管理员邀请码"
              :prefix-icon="Key"
              size="large"
              show-password
            />
            <div class="form-tip">
              超级管理员需要特殊邀请码，请联系系统管理员获取
            </div>
          </el-form-item>
        </div>
        
        <!-- 基本信息 -->
        <div class="form-section">
          <h4 class="section-title">基本信息</h4>
          
          <el-form-item label="管理员用户名" prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="请输入管理员用户名（3-50字符）"
              :prefix-icon="User"
              size="large"
              clearable
            />
          </el-form-item>
          
          <el-form-item label="邮箱地址" prop="email">
            <el-input
              v-model="registerForm.email"
              type="email"
              placeholder="请输入邮箱地址"
              :prefix-icon="Message"
              size="large"
              clearable
            />
          </el-form-item>
          
          <el-form-item label="手机号" prop="phone">
            <el-input
              v-model="registerForm.phone"
              placeholder="请输入手机号（建议填写）"
              :prefix-icon="Phone"
              size="large"
              clearable
            />
          </el-form-item>
          
          <el-form-item label="真实姓名" prop="fullName">
            <el-input
              v-model="registerForm.fullName"
              placeholder="请输入真实姓名"
              :prefix-icon="UserFilled"
              size="large"
              clearable
            />
          </el-form-item>
        </div>
        
        <!-- 安全设置 -->
        <div class="form-section">
          <h4 class="section-title">安全设置</h4>
          
          <el-form-item label="登录密码" prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码（至少12位，包含大小写字母、数字和特殊字符）"
              :prefix-icon="Lock"
              show-password
              size="large"
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
          
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              :prefix-icon="Lock"
              show-password
              size="large"
            />
          </el-form-item>
        </div>
        
        <!-- 系统设置 -->
        <div class="form-section">
          <h4 class="section-title">系统设置</h4>
          
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="时区" prop="timezone">
                <el-select
                  v-model="registerForm.timezone"
                  placeholder="选择时区"
                  size="large"
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
            </el-col>
            <el-col :span="12">
              <el-form-item label="语言" prop="locale">
                <el-select
                  v-model="registerForm.locale"
                  placeholder="选择语言"
                  size="large"
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
            </el-col>
          </el-row>
        </div>
        
        <!-- 安全确认 -->
        <el-form-item prop="agreeTerms">
          <el-checkbox v-model="registerForm.agreeTerms">
            我确认已了解管理员职责，同意遵守
            <el-link type="primary" :underline="false" @click="showAdminTermsDialog = true">
              《管理员服务协议》
            </el-link>
            和
            <el-link type="primary" :underline="false" @click="showSecurityDialog = true">
              《安全管理规范》
            </el-link>
          </el-checkbox>
        </el-form-item>
        
        <!-- 注册按钮 -->
        <el-form-item>
          <div v-if="showCancel" style="display: flex; gap: 12px; justify-content: center;">
            <el-button
              size="large"
              style="flex: 1; max-width: 120px;"
              @click="$emit('cancel')"
            >
              取消
            </el-button>
            <el-button
              type="primary"
              :loading="registerLoading"
              style="flex: 1; max-width: 200px;"
              size="large"
              @click="handleRegister"
            >
              <el-icon class="mr-2"><UserFilled /></el-icon>
              创建管理员账户
            </el-button>
          </div>
          <div v-else style="display: flex; justify-content: center;">
            <el-button
              type="primary"
              :loading="registerLoading"
              style="max-width: 300px; flex: 1;"
              size="large"
              @click="handleRegister"
            >
              <el-icon class="mr-2"><UserFilled /></el-icon>
              创建管理员账户
            </el-button>
          </div>
        </el-form-item>
        
        <!-- 返回链接 -->
        <div class="back-link">
          <el-link type="info" :underline="false" @click="$emit('back-to-login')">
            <el-icon><ArrowLeft /></el-icon>
            返回登录页面
          </el-link>
        </div>
      </el-form>
    
    <!-- 管理员服务协议对话框 -->
    <el-dialog
      v-model="showAdminTermsDialog"
      title="管理员服务协议"
      width="70%"
      :close-on-click-modal="false"
    >
      <div class="terms-content">
        <h4>1. 管理员职责</h4>
        <p>管理员负责系统的日常运维、用户管理、安全监控等工作，需要严格遵守操作规范。</p>
        
        <h4>2. 权限管理</h4>
        <p>管理员权限分为普通管理员和超级管理员，不同级别拥有不同的系统访问权限。</p>
        
        <h4>3. 安全责任</h4>
        <p>管理员需要保护账户安全，定期更换密码，启用多因素认证，不得泄露账户信息。</p>
        
        <h4>4. 操作审计</h4>
        <p>所有管理员操作都会被记录和审计，请确保操作的合规性和必要性。</p>
        
        <h4>5. 违规处理</h4>
        <p>违反管理规定的行为将导致账户被暂停或永久禁用。</p>
      </div>
      <template #footer>
        <el-button @click="showAdminTermsDialog = false">关闭</el-button>
      </template>
    </el-dialog>
    
    <!-- 安全管理规范对话框 -->
    <el-dialog
      v-model="showSecurityDialog"
      title="安全管理规范"
      width="70%"
      :close-on-click-modal="false"
    >
      <div class="security-content">
        <h4>1. 密码安全</h4>
        <p>管理员密码必须至少12位，包含大小写字母、数字和特殊字符，每90天强制更换。</p>
        
        <h4>2. 多因素认证</h4>
        <p>强烈建议启用MFA，超级管理员必须启用多因素认证。</p>
        
        <h4>3. 访问控制</h4>
        <p>仅在必要时使用管理员权限，遵循最小权限原则。</p>
        
        <h4>4. 网络安全</h4>
        <p>避免在不安全的网络环境下进行管理操作，使用VPN等安全连接。</p>
        
        <h4>5. 事件响应</h4>
        <p>发现安全事件时应立即报告并采取相应措施。</p>
      </div>
      <template #footer>
        <el-button @click="showSecurityDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { 
  User, Lock, Message, Phone, UserFilled, 
  Key, Warning, ArrowLeft 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 定义props
const props = defineProps({
  showCancel: {
    type: Boolean,
    default: false
  }
})

// 定义事件
const emit = defineEmits(['success', 'cancel', 'back-to-login', 'register-success'])

// 表单引用
const registerFormRef = ref(null)
const registerLoading = ref(false)

// 对话框状态
const showAdminTermsDialog = ref(false)
const showSecurityDialog = ref(false)

// 表单数据
const registerForm = reactive({
  role: 'normal',
  invitationCode: '',
  username: '',
  email: '',
  phone: '',
  fullName: '',
  password: '',
  confirmPassword: '',
  timezone: 'Asia/Shanghai',
  locale: 'zh-CN',
  agreeTerms: false
})

// 时区选项
const timezoneOptions = [
  { value: 'Asia/Shanghai', label: '北京/上海时间 (UTC+8)' },
  { value: 'Asia/Hong_Kong', label: '香港时间 (UTC+8)' },
  { value: 'America/New_York', label: '纽约时间 (UTC-5)' },
  { value: 'Europe/London', label: '伦敦时间 (UTC+0)' },
  { value: 'UTC', label: '协调世界时 (UTC)' }
]

// 语言选项
const languageOptions = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'en-US', label: 'English' }
]

// 密码强度计算
const passwordStrength = computed(() => {
  const password = registerForm.password
  if (!password) return 0
  
  let score = 0
  
  // 长度检查
  if (password.length >= 12) score += 25
  else if (password.length >= 8) score += 15
  else if (password.length >= 6) score += 10
  
  // 字符类型检查
  if (/[a-z]/.test(password)) score += 15
  if (/[A-Z]/.test(password)) score += 15
  if (/[0-9]/.test(password)) score += 15
  if (/[^a-zA-Z0-9]/.test(password)) score += 20
  
  // 复杂度检查
  if (/(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^a-zA-Z0-9])/.test(password)) {
    score += 10
  }
  
  return Math.min(score, 100)
})

const passwordStrengthText = computed(() => {
  const strength = passwordStrength.value
  if (strength < 30) return '弱'
  if (strength < 60) return '中等'
  if (strength < 80) return '强'
  return '很强'
})

const passwordStrengthClass = computed(() => {
  const strength = passwordStrength.value
  if (strength < 30) return 'weak'
  if (strength < 60) return 'medium'
  if (strength < 80) return 'strong'
  return 'very-strong'
})

const passwordStrengthWidth = computed(() => {
  return `${passwordStrength.value}%`
})

// 监听角色变化，清空邀请码
watch(() => registerForm.role, (newRole) => {
  if (newRole !== 'super') {
    registerForm.invitationCode = ''
  }
})

// 表单验证规则
const registerRules = {
  role: [
    { required: true, message: '请选择管理员角色', trigger: 'change' }
  ],
  invitationCode: [
    {
      validator: (rule, value, callback) => {
        if (registerForm.role === 'super' && !value) {
          callback(new Error('超级管理员需要邀请码'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  username: [
    { required: true, message: '请输入管理员用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/, message: '用户名只能包含字母、数字、下划线和中文', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^(\+\d{1,3}[- ]?)?\d{10,11}$/, message: '请输入正确的手机号格式', trigger: 'blur' }
  ],
  fullName: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '姓名长度为2-50字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 12, max: 50, message: '密码长度为12-50字符', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback()
          return
        }
        
        const hasUpper = /[A-Z]/.test(value)
        const hasLower = /[a-z]/.test(value)
        const hasDigit = /[0-9]/.test(value)
        const hasSpecial = /[^a-zA-Z0-9]/.test(value)
        
        if (!hasUpper || !hasLower || !hasDigit || !hasSpecial) {
          callback(new Error('密码必须包含大小写字母、数字和特殊字符'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  agreeTerms: [
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请阅读并同意管理员服务协议和安全管理规范'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

// 注册处理
const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    registerLoading.value = true
    try {
      // 构建注册数据
      const registerData = {
        username: registerForm.username,
        email: registerForm.email,
        phone: registerForm.phone || undefined,
        password: registerForm.password,
        confirm_password: registerForm.confirmPassword,
        full_name: registerForm.fullName,
        timezone: registerForm.timezone,
        locale: registerForm.locale,
        role: registerForm.role,
        invitation_code: registerForm.role === 'super' ? registerForm.invitationCode : undefined
      }
      
      // 发送注册请求
      const response = await fetch('/api/admin/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(registerData)
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || '注册失败')
      }
      
      ElMessage.success('管理员账户创建成功！')
      
      // 先保存要传递的管理员信息
      const adminInfo = {
        username: registerForm.username,
        email: registerForm.email,
        role: registerForm.role
      }
      
      // 再清空表单
      registerFormRef.value.resetFields()
      
      // 触发注册成功事件
      emit('success', adminInfo)
      emit('register-success', adminInfo)
      
    } catch (error) {
      console.error('管理员注册失败:', error)
      ElMessage.error(error.message || '注册失败，请稍后重试')
    } finally {
      registerLoading.value = false
    }
  })
}
</script>

<style scoped>
.admin-register {
  padding: 30px 40px;
  color: var(--text-primary, #F0F2F5);
}

/* 表单样式与登录页面保持一致 */
.admin-register :deep(.el-form) {
  background: transparent;
}

.admin-register :deep(.el-form-item__label) {
  color: var(--text-primary, #F0F2F5) !important;
  font-weight: 500;
  font-size: 14px;
}

.admin-register :deep(.el-input__wrapper) {
  background: var(--input-bg, rgba(255, 255, 255, 0.05)) !important;
  border: 1px solid var(--border-default, rgba(255, 255, 255, 0.15)) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  transition: all 0.3s ease !important;
}

.admin-register :deep(.el-input__wrapper:hover) {
  border-color: rgba(64, 158, 255, 0.4) !important;
  background: rgba(255, 255, 255, 0.08) !important;
}

.admin-register :deep(.el-input__wrapper.is-focus) {
  border-color: #409eff !important;
  background: rgba(255, 255, 255, 0.1) !important;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2) !important;
}

.admin-register :deep(.el-input__inner) {
  color: var(--text-primary, #F0F2F5) !important;
  background: transparent !important;
}

.admin-register :deep(.el-input__inner::placeholder) {
  color: var(--text-placeholder, #6F7A87) !important;
}

.admin-register :deep(.el-select .el-input__wrapper) {
  background: var(--input-bg, rgba(255, 255, 255, 0.05)) !important;
  border: 1px solid var(--border-default, rgba(255, 255, 255, 0.15)) !important;
}

.admin-register :deep(.el-checkbox__label) {
  color: var(--text-secondary, #A8B3C0) !important;
  font-size: 14px;
}

.admin-register :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #409eff !important;
  border-color: #409eff !important;
}

.admin-register :deep(.el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #67b5ff 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3) !important;
  transition: all 0.3s ease !important;
}

.admin-register :deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #67b5ff 0%, #409eff 100%) !important;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4) !important;
  transform: translateY(-1px);
}

.admin-register :deep(.el-alert) {
  background: rgba(255, 193, 7, 0.1) !important;
  border: 1px solid rgba(255, 193, 7, 0.3) !important;
  border-radius: 8px !important;
}

.admin-register :deep(.el-alert__title) {
  color: #ffc107 !important;
  font-weight: 600;
}

.admin-register :deep(.el-alert__description) {
  color: rgba(255, 255, 255, 0.8) !important;
}

.form-section {
  margin-bottom: 32px;
  padding-bottom: 52px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.form-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.form-section .el-form-item:last-child {
  margin-bottom: 16px;
}

.section-title {
  margin: 0 0 16px 0;
  color: #409eff;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.section-title::before {
  content: '';
  width: 4px;
  height: 16px;
  background: linear-gradient(135deg, #409eff 0%, #67b5ff 100%);
  margin-right: 8px;
  border-radius: 2px;
}

.role-option {
  display: block;
  width: 100%;
}

.role-title {
  display: flex;
  align-items: center;
  font-weight: 700;
  font-size: 16px;
  color: #ffffff;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
  line-height: 1.3;
}

.role-icon {
  margin-right: 8px;
  font-size: 18px;
  flex-shrink: 0;
}

.normal-icon {
  color: #67c23a;
}

.super-icon {
  color: #ffd700;
}


.role-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  line-height: 1.4;
  font-weight: 400;
  margin: 0;
  padding-right: 8px;
}

.invitation-code-item {
  position: relative;
  z-index: 10;
  margin-top: 48px;
  margin-bottom: 16px !important;
}

.form-tip {
  font-size: 12px;
  color: #ffc107;
  margin-top: 4px;
  line-height: 1.4;
}

.password-strength {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.strength-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 2px;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.3);
}

.strength-fill.weak {
  background: linear-gradient(90deg, #ff4757 0%, #ff6b7a 100%);
}

.strength-fill.medium {
  background: linear-gradient(90deg, #ffa502 0%, #ffb142 100%);
}

.strength-fill.strong {
  background: linear-gradient(90deg, #409eff 0%, #67b5ff 100%);
}

.strength-fill.very-strong {
  background: linear-gradient(90deg, #2ed573 0%, #7bed9f 100%);
}

.strength-text {
  font-size: 12px;
  color: var(--text-secondary, #A8B3C0);
  min-width: 60px;
  font-weight: 500;
}

.back-link {
  text-align: center;
  margin-top: 16px;
}

.back-link :deep(.el-link) {
  color: var(--text-secondary, #A8B3C0) !important;
  transition: all 0.3s ease;
}

.back-link :deep(.el-link:hover) {
  color: #409eff !important;
}

/* 单选框组样式 */
.admin-register :deep(.el-radio-group) {
  width: 100%;
  display: block;
}

.radio-wrapper {
  margin-bottom: 48px;
  display: block;
  position: relative;
  overflow: visible;
  z-index: auto;
}

.radio-wrapper:last-child {
  margin-bottom: 0;
}

.admin-register :deep(.el-radio) {
  width: 100%;
  margin-right: 0 !important;
  margin-bottom: 0 !important;
  padding: 0 !important;
  border: none !important;
  background: none !important;
  display: block !important;
  position: relative;
  z-index: 1;
}

.admin-register :deep(.el-radio) .role-option {
  padding: 18px 20px 18px 52px;
  border: 2px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  transition: all 0.3s ease;
  cursor: pointer;
  min-height: 70px;
  max-height: 80px;
  box-sizing: border-box;
  display: block;
  position: relative;
  overflow: hidden;
}

.admin-register :deep(.el-radio:hover) .role-option {
  border-color: rgba(64, 158, 255, 0.5);
  background: rgba(64, 158, 255, 0.08);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
}

.admin-register :deep(.el-radio.is-checked) .role-option {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.15);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.25);
}


.admin-register :deep(.el-radio__input) {
  position: absolute;
  top: 22px;
  left: 22px;
  margin: 0 !important;
  z-index: 2;
}

.admin-register :deep(.el-radio__label) {
  display: block;
  width: 100%;
  padding: 0;
  margin: 0;
}

.admin-register :deep(.el-radio__inner) {
  width: 18px !important;
  height: 18px !important;
  border: 2px solid rgba(255, 255, 255, 0.4) !important;
  background: transparent !important;
  transition: all 0.3s ease !important;
}

.admin-register :deep(.el-radio__input.is-checked .el-radio__inner) {
  border-color: #409eff !important;
  background: #409eff !important;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.2) !important;
}

.admin-register :deep(.el-radio__inner::after) {
  width: 6px !important;
  height: 6px !important;
  background: #ffffff !important;
}

.terms-content,
.security-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 0 16px;
}

.terms-content h4,
.security-content h4 {
  color: #409eff;
  margin: 16px 0 8px 0;
  font-size: 16px;
  font-weight: 600;
}

.terms-content p,
.security-content p {
  color: var(--text-secondary, #A8B3C0);
  line-height: 1.6;
  margin: 8px 0;
}

.mr-2 {
  margin-right: 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .admin-register {
    padding: 20px 16px;
  }
  
  .card-header h3 {
    font-size: 20px;
  }
  
  :deep(.el-form-item__label) {
    width: 100px !important;
  }
}
</style>
