<template>
  <div class="user-register">
    <el-card class="register-card">
      <template #header>
        <div class="card-header">
          <h3>用户注册</h3>
          <p class="card-subtitle">创建您的 Homalos 交易账户</p>
        </div>
      </template>
      
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        label-width="100px"
        @submit.prevent="handleRegister"
      >
        <!-- 基本信息 -->
        <div class="form-section">
          <h4 class="section-title">基本信息</h4>
          
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="请输入用户名（3-50字符）"
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
              placeholder="请输入手机号（可选）"
              :prefix-icon="Phone"
              size="large"
              clearable
            />
          </el-form-item>
        </div>
        
        <!-- 密码设置 -->
        <div class="form-section">
          <h4 class="section-title">密码设置</h4>
          
          <el-form-item label="登录密码" prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码（至少6位）"
              :prefix-icon="Lock"
              show-password
              size="large"
            />
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
        
        <!-- 个人信息 -->
        <div class="form-section">
          <h4 class="section-title">个人信息</h4>
          
          <el-form-item label="真实姓名" prop="fullName">
            <el-input
              v-model="registerForm.fullName"
              placeholder="请输入真实姓名（可选）"
              :prefix-icon="UserFilled"
              size="large"
              clearable
            />
          </el-form-item>
          
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
        
        <!-- 服务条款 -->
        <el-form-item prop="agreeTerms">
          <el-checkbox v-model="registerForm.agreeTerms">
            我已阅读并同意
            <el-link type="primary" :underline="false" @click="showTermsDialog = true">
              《用户服务协议》
            </el-link>
            和
            <el-link type="primary" :underline="false" @click="showPrivacyDialog = true">
              《隐私政策》
            </el-link>
          </el-checkbox>
        </el-form-item>
        
        <!-- 注册按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            :loading="registerLoading"
            style="width: 100%"
            size="large"
            @click="handleRegister"
          >
            <el-icon class="mr-2"><UserFilled /></el-icon>
            立即注册
          </el-button>
        </el-form-item>
        
        <!-- 登录链接 -->
        <div class="login-link">
          已有账户？
          <el-link type="primary" :underline="false" @click="$emit('switch-to-login')">
            立即登录
          </el-link>
        </div>
      </el-form>
    </el-card>
    
    <!-- 服务条款对话框 -->
    <el-dialog
      v-model="showTermsDialog"
      title="用户服务协议"
      width="60%"
      :close-on-click-modal="false"
    >
      <div class="terms-content">
        <h4>1. 服务说明</h4>
        <p>Homalos是一个量化交易系统，为用户提供策略开发、回测和实盘交易服务。</p>
        
        <h4>2. 用户责任</h4>
        <p>用户需要对自己的交易行为负责，合理控制风险，遵守相关法律法规。</p>
        
        <h4>3. 风险提示</h4>
        <p>量化交易存在风险，过往业绩不代表未来表现，请谨慎投资。</p>
        
        <h4>4. 服务条款</h4>
        <p>我们保留修改服务条款的权利，修改后的条款将在网站上公布。</p>
      </div>
      <template #footer>
        <el-button @click="showTermsDialog = false">关闭</el-button>
      </template>
    </el-dialog>
    
    <!-- 隐私政策对话框 -->
    <el-dialog
      v-model="showPrivacyDialog"
      title="隐私政策"
      width="60%"
      :close-on-click-modal="false"
    >
      <div class="privacy-content">
        <h4>1. 信息收集</h4>
        <p>我们收集您提供的注册信息，用于账户管理和服务提供。</p>
        
        <h4>2. 信息使用</h4>
        <p>您的个人信息仅用于提供服务，不会泄露给第三方。</p>
        
        <h4>3. 数据安全</h4>
        <p>我们采用行业标准的安全措施保护您的数据安全。</p>
        
        <h4>4. 联系我们</h4>
        <p>如有隐私相关问题，请联系我们的客服团队。</p>
      </div>
      <template #footer>
        <el-button @click="showPrivacyDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { User, Lock, Message, Phone, UserFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 定义事件
const emit = defineEmits(['switch-to-login', 'register-success'])

// 表单引用
const registerFormRef = ref(null)
const registerLoading = ref(false)

// 对话框状态
const showTermsDialog = ref(false)
const showPrivacyDialog = ref(false)

// 表单数据
const registerForm = reactive({
  username: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
  fullName: '',
  timezone: 'Asia/Shanghai',
  locale: 'zh-CN',
  agreeTerms: false
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
const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
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
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度为6-50字符', trigger: 'blur' }
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
          callback(new Error('请阅读并同意服务协议和隐私政策'))
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
        full_name: registerForm.fullName || undefined,
        timezone: registerForm.timezone,
        locale: registerForm.locale,
        avatar_url: undefined
      }
      
      // 发送注册请求
      const response = await fetch('/api/auth/register', {
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
      
      ElMessage.success('注册成功！请登录您的账户')
      
      // 清空表单
      registerFormRef.value.resetFields()
      
      // 触发注册成功事件
      emit('register-success', {
        username: registerForm.username,
        email: registerForm.email
      })
      
    } catch (error) {
      console.error('注册失败:', error)
      ElMessage.error(error.message || '注册失败，请稍后重试')
    } finally {
      registerLoading.value = false
    }
  })
}
</script>

<style scoped>
.user-register {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.register-card {
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.card-header {
  text-align: center;
  margin-bottom: 20px;
}

.card-header h3 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.card-subtitle {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.form-section {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.form-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
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
  background: #409eff;
  margin-right: 8px;
  border-radius: 2px;
}

.login-link {
  text-align: center;
  margin-top: 16px;
  color: #909399;
  font-size: 14px;
}

.terms-content,
.privacy-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 0 16px;
}

.terms-content h4,
.privacy-content h4 {
  color: #303133;
  margin: 16px 0 8px 0;
  font-size: 16px;
}

.terms-content p,
.privacy-content p {
  color: #606266;
  line-height: 1.6;
  margin: 8px 0;
}

.mr-2 {
  margin-right: 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .user-register {
    padding: 10px;
  }
  
  .card-header h3 {
    font-size: 20px;
  }
  
  :deep(.el-form-item__label) {
    width: 80px !important;
  }
}
</style>
