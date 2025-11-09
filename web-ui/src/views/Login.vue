<template>
  <div class="login-container">
    <!-- 深色主题动画背景 -->
    <div class="video-background">
      <div class="data-stream-container">
        <!-- 10条垂直数据流 -->
        <div class="data-stream stream-1"></div>
        <div class="data-stream stream-2"></div>
        <div class="data-stream stream-3"></div>
        <div class="data-stream stream-4"></div>
        <div class="data-stream stream-5"></div>
        <div class="data-stream stream-6"></div>
        <div class="data-stream stream-7"></div>
        <div class="data-stream stream-8"></div>
        <div class="data-stream stream-9"></div>
        <div class="data-stream stream-10"></div>
        
        <!-- 8个交易粒子 -->
        <div class="particles">
          <div class="particle"></div>
          <div class="particle"></div>
          <div class="particle"></div>
          <div class="particle"></div>
          <div class="particle"></div>
          <div class="particle"></div>
          <div class="particle"></div>
          <div class="particle"></div>
        </div>
      </div>
    </div>
    
    <!-- 顶部导航栏 -->
    <div class="top-nav">
      <!-- 左侧Logo -->
      <div class="nav-logo">
        <el-icon :size="32" class="nav-logo-icon">
          <TrendCharts />
        </el-icon>
      </div>
      
      <!-- 右侧语言切换 -->
      <div class="nav-language">
        <el-dropdown @command="handleLanguageChange" trigger="hover" placement="bottom-end">
          <div class="language-icon-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <line x1="2" y1="12" x2="22" y2="12"/>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
          </div>
          <template #dropdown>
            <el-dropdown-menu class="language-dropdown-menu">
              <el-dropdown-item
                v-for="item in languageOptions"
                :key="item.value"
                :command="item.value"
                :class="{ 'is-active': currentLanguage === item.value }"
              >
                <span class="language-option-content">
                  <span class="language-icon">{{ item.icon }}</span>
                  <span class="language-text">{{ item.label }}</span>
                </span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <!-- 登录卡片 -->
    <el-card class="login-card">
      <!-- 标题 -->
      <div class="card-header">
        <h2>Homalos 量化交易系统</h2>
      </div>
      
      <!-- Tab切换 -->
      <el-tabs v-model="activeTab" class="login-tabs">
        <!-- 登录Tab -->
        <el-tab-pane label="登录" name="login">
          <el-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="账号名/邮箱/手机号"
                :prefix-icon="User"
                size="large"
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入登录密码"
                :prefix-icon="Lock"
                show-password
                size="large"
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            
            <el-form-item>
              <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                <el-checkbox v-model="rememberMe" size="default">
                  记住用户名
                </el-checkbox>
                <el-link type="primary" :underline="false" @click="showResetDialog = true">
                  忘记密码？
                </el-link>
              </div>
            </el-form-item>
            
            <el-form-item>
              <el-button
                type="primary"
                :loading="loginLoading"
                style="width: 100%"
                @click="handleLogin"
              >
                登录
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <!-- 注册Tab -->
        <el-tab-pane label="注册" name="register">
          <el-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            @submit.prevent="handleRegister"
          >
            <el-form-item prop="username">
              <el-input
                v-model="registerForm.username"
                placeholder="用户名（3-50字符）"
                :prefix-icon="User"
                size="large"
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="密码（至少6位）"
                :prefix-icon="Lock"
                show-password
                size="large"
              />
            </el-form-item>
            
            <el-form-item prop="confirmPassword">
              <el-input
                v-model="registerForm.confirmPassword"
                type="password"
                placeholder="确认密码"
                :prefix-icon="Lock"
                show-password
                size="large"
                @keyup.enter="handleRegister"
              />
            </el-form-item>
            
            <el-form-item prop="email">
              <el-input
                v-model="registerForm.email"
                placeholder="邮箱（用于找回/修改密码）"
                :prefix-icon="Message"
                size="large"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button
                type="success"
                :loading="registerLoading"
                style="width: 100%"
                @click="handleRegister"
              >
                注册
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <!-- 密码重置Dialog -->
    <el-dialog
      v-model="showResetDialog"
      :title="resetStep === 1 ? '重置密码 - 验证身份' : '重置密码 - 设置新密码'"
      width="450px"
      :close-on-click-modal="false"
      @close="resetResetForm"
    >
      <!-- 第一步：验证身份 -->
      <el-form
        v-if="resetStep === 1"
        ref="resetFormRef"
        :model="resetForm"
        :rules="resetRules"
      >
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 20px;"
        >
          请输入您的用户名和注册邮箱以验证身份
        </el-alert>
        
        <el-form-item prop="username">
          <el-input
            v-model="resetForm.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="email">
          <el-input
            v-model="resetForm.email"
            placeholder="注册邮箱"
            :prefix-icon="Message"
            size="large"
            @keyup.enter="handleResetPassword"
          />
        </el-form-item>
      </el-form>
      
      <!-- 第二步：设置新密码 -->
      <el-form
        v-else-if="resetStep === 2"
        ref="resetFormRef"
        :model="resetForm"
        :rules="resetRules"
      >
        <el-alert
          type="success"
          :closable="false"
          style="margin-bottom: 20px;"
        >
          身份验证成功！请设置新密码
        </el-alert>
        
        <el-form-item prop="newPassword">
          <el-input
            v-model="resetForm.newPassword"
            type="password"
            placeholder="新密码（至少6位）"
            :prefix-icon="Lock"
            show-password
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="resetForm.confirmPassword"
            type="password"
            placeholder="确认新密码"
            :prefix-icon="Lock"
            show-password
            size="large"
            @keyup.enter="handleResetPassword"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showResetDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="resetLoading"
          @click="handleResetPassword"
        >
          {{ resetStep === 1 ? '下一步' : '确认重置' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Message, UserFilled, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('login')
const rememberMe = ref(false)

// 语言切换相关
const currentLanguage = ref('zh-CN')
const languageOptions = [
  { value: 'zh-CN', label: '简体中文', icon: '🇨🇳' },
  { value: 'en-US', label: 'English', icon: '🇺🇸' }
]

// 语言切换处理函数
const handleLanguageChange = (value) => {
  currentLanguage.value = value
  console.log('语言切换:', value)
  const selectedLanguage = languageOptions.find(item => item.value === value)
  ElMessage.success(`${selectedLanguage?.icon} 语言已切换为: ${selectedLanguage?.label}`)
  // TODO: 集成i18n后实现真实的语言切换逻辑
}

// 密码重置相关状态
const showResetDialog = ref(false)
const resetStep = ref(1) // 1=验证身份, 2=设置新密码
const resetLoading = ref(false)
const resetFormRef = ref(null)
const resetForm = reactive({
  username: '',
  email: '',
  newPassword: '',
  confirmPassword: ''
})

// 监听Tab切换，自动聚焦第一个输入框
watch(activeTab, async (newTab) => {
  await nextTick()
  const firstInput = document.querySelector(`[name="${newTab}"] .el-input__inner`)
  if (firstInput) {
    firstInput.focus()
  }
})

// 组件挂载时，从localStorage加载保存的用户名
onMounted(() => {
  const savedUsername = localStorage.getItem('homalos_remember_username')
  if (savedUsername) {
    loginForm.username = savedUsername
    rememberMe.value = true
  }
})

// 检测设备类型（移动端 vs 桌面端）
const isMobile = computed(() => window.innerWidth < 768)

const loginFormRef = ref(null)
const registerFormRef = ref(null)
const loginLoading = ref(false)
const registerLoading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: ''
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
  ]
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50字符', trigger: 'blur' }
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
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

// 密码重置表单验证规则
const resetRules = computed(() => {
  if (resetStep.value === 1) {
    // 第一步：验证用户名和邮箱
    return {
      username: [
        { required: true, message: '请输入用户名', trigger: 'blur' }
      ],
      email: [
        { required: true, message: '请输入邮箱', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
      ]
    }
  } else {
    // 第二步：验证新密码
    return {
      newPassword: [
        { required: true, message: '请输入新密码', trigger: 'blur' },
        { min: 6, max: 50, message: '密码长度为6-50字符', trigger: 'blur' }
      ],
      confirmPassword: [
        { required: true, message: '请确认新密码', trigger: 'blur' },
        {
          validator: (rule, value, callback) => {
            if (value !== resetForm.newPassword) {
              callback(new Error('两次输入的密码不一致'))
            } else {
              callback()
            }
          },
          trigger: 'blur'
        }
      ]
    }
  }
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    loginLoading.value = true
    try {
      const success = await userStore.login(loginForm)
      if (success) {
        // 根据"记住我"选项，保存或清除用户名
        if (rememberMe.value) {
          localStorage.setItem('homalos_remember_username', loginForm.username)
        } else {
          localStorage.removeItem('homalos_remember_username')
        }
        
        ElMessage.success('登录成功')
        router.push('/')
      }
      // 失败的情况由响应拦截器处理错误消息，不需要再次显示
    } catch (error) {
      // 错误消息已由响应拦截器显示，这里不再重复显示
      console.error('登录异常:', error)
    } finally {
      loginLoading.value = false
    }
  })
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    registerLoading.value = true
    try {
      const result = await userStore.register(registerForm)
      if (result.success) {
        ElMessage.success('注册成功，请登录')
        
        // 清除引导完成标记，确保新用户能看到引导
        localStorage.removeItem('homalos_guide_completed')
        
        // 清空注册表单
        registerFormRef.value.resetFields()
        // 切换到登录Tab
        activeTab.value = 'login'
        // 自动填充用户名到登录表单
        loginForm.username = registerForm.username
      } else {
        ElMessage.error(result.message)
      }
    } catch (error) {
      console.error('注册异常:', error)
      ElMessage.error('注册失败，请稍后重试')
    } finally {
      registerLoading.value = false
    }
  })
}

// 重置密码处理函数
const handleResetPassword = async () => {
  if (!resetFormRef.value) return
  
  await resetFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    resetLoading.value = true
    try {
      if (resetStep.value === 1) {
        // 第一步：验证用户名和邮箱
        const response = await fetch('/api/auth/password-reset/verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: resetForm.username,
            email: resetForm.email
          })
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.detail || '验证失败')
        }
        
        ElMessage.success('验证成功！请设置新密码')
        resetStep.value = 2
        
      } else if (resetStep.value === 2) {
        // 第二步：确认重置密码
        const response = await fetch('/api/auth/password-reset/confirm', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: resetForm.username,
            email: resetForm.email,
            new_password: resetForm.newPassword
          })
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.detail || '重置失败')
        }
        
        ElMessage.success('密码重置成功！请使用新密码登录')
        
        // 关闭对话框
        showResetDialog.value = false
        
        // 切换到登录Tab并自动填充用户名
        activeTab.value = 'login'
        loginForm.username = resetForm.username
        loginForm.password = ''
        
        // 重置表单
        resetResetForm()
      }
      
    } catch (error) {
      console.error('密码重置异常:', error)
      ElMessage.error(error.message || '操作失败，请稍后重试')
    } finally {
      resetLoading.value = false
    }
  })
}

// 重置密码表单
const resetResetForm = () => {
  resetStep.value = 1
  resetForm.username = ''
  resetForm.email = ''
  resetForm.newPassword = ''
  resetForm.confirmPassword = ''
  if (resetFormRef.value) {
    resetFormRef.value.clearValidate()
  }
}
</script>

<style scoped>
.login-container {
  /* CSS变量定义 - 在组件根元素定义 */
  --primary-500: #007BFF;
  --primary-700: #0056B3;
  --primary-100: rgba(0, 123, 255, 0.15);
  --surface-glass: rgba(16, 22, 28, 0.65);
  --border-default: rgba(255, 255, 255, 0.15);
  --text-primary: #F0F2F5;
  --text-secondary: #A8B3C0;
  --text-placeholder: #6F7A87;
  --input-bg: rgba(255, 255, 255, 0.05);
  --success: #28A745;
  --error: #DC3545;
  
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #05080A; /* 深黑色背景 */
  overflow: hidden;
}

/* 深色主题动画背景 */
.video-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 0;
  background: linear-gradient(135deg, #05080A 0%, #0A0F14 50%, #05080A 100%);
  overflow: hidden;
  pointer-events: none; /* 允许点击穿透 */
}

.data-stream-container {
  position: relative;
  width: 100%;
  height: 100%;
  animation: backgroundShift 20s ease-in-out infinite;
}

@keyframes backgroundShift {
  0%, 100% { 
    background: linear-gradient(135deg, #05080A 0%, #0A0F14 50%, #05080A 100%); 
  }
  33% { 
    background: linear-gradient(135deg, #060A0F 0%, #0B1016 50%, #060A0F 100%); 
  }
  66% { 
    background: linear-gradient(135deg, #04070B 0%, #090E14 50%, #04070B 100%); 
  }
}

/* 垂直数据流动画 */
.data-stream {
  position: absolute;
  width: 2px;
  height: 200%;
  background: linear-gradient(to bottom, 
    transparent 0%, 
    rgba(0, 123, 255, 0.2) 10%, 
    #007BFF 50%, 
    rgba(0, 123, 255, 0.2) 90%, 
    transparent 100%);
  opacity: 0.6; /* 增加可见度 */
  animation: dataFlow 6s infinite linear;
}

.stream-1 { left: 10%; animation-delay: 0s; }
.stream-2 { left: 25%; animation-delay: 0.5s; }
.stream-3 { left: 50%; animation-delay: 1s; }
.stream-4 { left: 75%; animation-delay: 1.5s; }
.stream-5 { left: 90%; animation-delay: 2s; }
.stream-6 { left: 5%; animation-delay: 2.5s; width: 1px; }
.stream-7 { left: 35%; animation-delay: 3s; width: 3px; }
.stream-8 { left: 60%; animation-delay: 3.5s; width: 1px; }
.stream-9 { left: 80%; animation-delay: 4s; width: 2px; }
.stream-10 { left: 95%; animation-delay: 4.5s; width: 1px; }

@keyframes dataFlow {
  0% { 
    transform: translateY(-100vh) translateX(0) scaleY(1); 
    opacity: 0; 
  }
  5% { 
    opacity: 0.2; 
    transform: translateY(-90vh) translateX(2px) scaleY(1.2);
  }
  20% { 
    opacity: 0.4; 
    transform: translateY(-60vh) translateX(-1px) scaleY(0.8);
  }
  50% { 
    opacity: 0.6; 
    transform: translateY(0vh) translateX(1px) scaleY(1.1);
  }
  80% { 
    opacity: 0.4; 
    transform: translateY(60vh) translateX(-2px) scaleY(0.9);
  }
  95% { 
    opacity: 0.2; 
    transform: translateY(90vh) translateX(0) scaleY(1.2);
  }
  100% { 
    transform: translateY(100vh) translateX(0) scaleY(1); 
    opacity: 0; 
  }
}

/* 粒子效果 */
.particles {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  z-index: 1; /* 确保在数据流之上 */
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  opacity: 0;
  animation: particleFloat 8s infinite ease-in-out;
}

.particle:nth-child(1) { 
  left: 15%; top: 20%; 
  background: #28A745;
  animation-delay: 0s; 
  box-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
}
.particle:nth-child(2) { 
  left: 35%; top: 60%; 
  background: #DC3545;
  animation-delay: 1s; 
  box-shadow: 0 0 8px rgba(220, 53, 69, 0.6);
}
.particle:nth-child(3) { 
  left: 65%; top: 40%; 
  background: #28A745;
  animation-delay: 2s; 
  box-shadow: 0 0 6px rgba(40, 167, 69, 0.5);
}
.particle:nth-child(4) { 
  left: 80%; top: 80%; 
  background: #DC3545;
  animation-delay: 3s; 
  box-shadow: 0 0 10px rgba(220, 53, 69, 0.7);
}
.particle:nth-child(5) { 
  left: 45%; top: 10%; 
  background: #28A745;
  animation-delay: 4s; 
  box-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
}
.particle:nth-child(6) { 
  left: 25%; top: 30%; 
  background: #DC3545;
  animation-delay: 5s; 
  width: 3px; height: 3px;
  box-shadow: 0 0 6px rgba(220, 53, 69, 0.5);
}
.particle:nth-child(7) { 
  left: 70%; top: 70%; 
  background: #28A745;
  animation-delay: 6s; 
  width: 5px; height: 5px;
  box-shadow: 0 0 10px rgba(40, 167, 69, 0.8);
}
.particle:nth-child(8) { 
  left: 55%; top: 25%; 
  background: #DC3545;
  animation-delay: 7s; 
  width: 2px; height: 2px;
  box-shadow: 0 0 4px rgba(220, 53, 69, 0.4);
}

@keyframes particleFloat {
  0%, 100% { 
    transform: translateY(0) translateX(0) scale(0); 
    opacity: 0; 
  }
  10% { 
    transform: translateY(-10px) translateX(2px) scale(0.8); 
    opacity: 0.3; 
  }
  25% { 
    transform: translateY(-25px) translateX(-1px) scale(1.1); 
    opacity: 0.7; 
  }
  50% { 
    transform: translateY(-45px) translateX(3px) scale(1.3); 
    opacity: 1; 
  }
  75% { 
    transform: translateY(-60px) translateX(-2px) scale(1.1); 
    opacity: 0.8; 
  }
  90% { 
    transform: translateY(-70px) translateX(1px) scale(0.9); 
    opacity: 0.4; 
  }
}

/* 顶部导航栏 */
.top-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  background: transparent;
  z-index: 2;
}

/* 左侧Logo */
.nav-logo {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.nav-logo-icon {
  background: linear-gradient(135deg, #33eaff 40%, #5db0ff 80%, #fff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 2px 8px #22ffff) drop-shadow(0 0 16px #0af) drop-shadow(0 0 2px #fff); /* 多层亮色发光 */
}

@media (max-width: 768px) {
  .nav-logo-icon {
    font-size: 28px;
    filter: drop-shadow(0 4px 16px #55f6ff) drop-shadow(0 0 18px #66ccff) drop-shadow(0 0 4px #fff);
  }
}

/* 右侧语言切换 - 图标按钮式 */
.nav-language {
  display: flex;
  align-items: center;
}

/* 语言切换图标按钮 */
.language-icon-btn {
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.3s ease;
  padding: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
}

.language-icon-btn:hover {
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
  box-shadow: 0 0 12px rgba(64, 158, 255, 0.4);
  transform: scale(1.1);
}

/* 下拉菜单容器 - 深色玻璃拟物效果 */
.language-dropdown-menu {
  background: rgba(16, 22, 28, 0.85) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
  border-radius: 8px;
  padding: 8px 0;
  min-width: 160px;
}

/* 下拉菜单项样式 */
:deep(.language-dropdown-menu .el-dropdown-menu__item) {
  padding: 10px 20px;
  color: var(--text-primary);
  transition: all 0.3s ease;
  border-radius: 4px;
  margin: 0 6px;
}

:deep(.language-dropdown-menu .el-dropdown-menu__item:hover) {
  background: rgba(64, 158, 255, 0.15) !important;
  color: #409eff;
}

:deep(.language-dropdown-menu .el-dropdown-menu__item.is-active) {
  background: rgba(64, 158, 255, 0.2) !important;
  color: #409eff;
  font-weight: 600;
}

/* 下拉选项内容 */
.language-option-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.language-icon {
  font-size: 20px;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.language-text {
  font-size: 14px;
  font-weight: 500;
  color: inherit;
}

.login-card {
  position: relative;
  width: 500px;
  max-width: 95%;
  margin: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  z-index: 1;
  backdrop-filter: blur(20px); /* 强化毛玻璃效果 */
  -webkit-backdrop-filter: blur(20px);
  background: var(--surface-glass) !important; /* 深色半透明玻璃效果 */
  border: 1px solid var(--border-default);
}

@media (max-width: 768px) {
  /* 移动端隐藏数据流以优化性能 */
  .data-stream {
    display: none;
  }
  
  /* 移动端粒子动画减速 */
  .particle {
    animation-duration: 12s;
  }
  
  /* 移动端顶部导航栏 */
  .top-nav {
    height: 50px;
    padding: 0 15px;
  }
  
  .nav-logo-icon {
    font-size: 28px;
  }
  
  .nav-language :deep(.el-select) {
    width: 130px;
  }
  
  .nav-language :deep(.el-input__inner) {
    font-size: 13px;
  }
  
  /* 移动端登录卡片 */
  .login-card {
    width: 100%;
    max-width: 100%;
    margin: 10px;
  }
  
  .card-header {
    padding: 25px 25px 15px 25px;
  }
  
  .card-header h2 {
    font-size: 20px;
  }
  
  .login-tabs {
    padding: 0 25px 25px 25px;
  }
  
  .login-tabs :deep(.el-tabs__item) {
    font-size: 15px;
    padding: 0 15px;
  }
  
  .login-tabs :deep(.el-input--large .el-input__wrapper) {
    padding: 10px 12px;
  }
  
  .login-tabs :deep(.el-form-item) {
    margin-bottom: 16px;
  }
}

.card-header {
  text-align: center;
  padding: 30px 50px 20px 50px;
  border-bottom: 1px solid rgba(0, 191, 255, 0.1);
  margin-bottom: 10px;
}

.card-header h2 {
  margin: 0 0 10px 0;
  color: var(--text-primary); /* 亮白色 */
  font-size: 24px;
  font-weight: 600;
}

.card-header p {
  margin: 0;
  color: var(--text-secondary); /* 灰白色 */
  font-size: 14px;
  font-weight: 400;
}

.login-tabs {
  margin-top: 20px;
  padding: 0 50px 30px 50px;
}

/* Tab居中对齐 */
.login-tabs :deep(.el-tabs__nav-wrap) {
  display: flex;
  justify-content: center;
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.login-tabs :deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-secondary); /* 深色主题灰白色 */
  transition: all 0.3s ease;
}

.login-tabs :deep(.el-tabs__item.is-active) {
  color: var(--text-primary); /* 激活时亮白色 */
}

.login-tabs :deep(.el-tabs__item:hover) {
  color: #409eff;
}

.login-tabs :deep(.el-tab-pane) {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 优化按钮视觉反馈 */
.login-tabs :deep(.el-button) {
  font-weight: 500;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.login-tabs :deep(.el-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3);
}

.login-tabs :deep(.el-button:active) {
  transform: translateY(0);
}

.login-tabs :deep(.el-button.is-loading) {
  opacity: 0.8;
  transform: none;
}

/* 优化输入框聚焦效果 - 深色主题 */
.login-tabs :deep(.el-input__wrapper) {
  background: var(--input-bg); /* 深色半透明背景 */
  border: 1px solid var(--border-default);
  transition: all 0.3s ease;
  box-shadow: none;
}

.login-tabs :deep(.el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(0, 123, 255, 0.3);
}

.login-tabs :deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.1);
  border-color: #409eff;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.3);
}

/* 输入框文字颜色 */
.login-tabs :deep(.el-input__inner) {
  color: var(--text-primary); /* 亮白色文字 */
}

.login-tabs :deep(.el-input__inner::placeholder) {
  color: var(--text-placeholder); /* 深色主题占位符 */
}

/* 保留label样式以防未来需要 */
.login-tabs :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--text-primary); /* 深色主题亮白色 */
}

/* 优化无标签表单项间距 */
.login-tabs :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-tabs :deep(.el-form-item__content) {
  line-height: normal;
}

/* 优化大尺寸输入框样式 */
.login-tabs :deep(.el-input--large) {
  font-size: 15px;
}

.login-tabs :deep(.el-input--large .el-input__wrapper) {
  padding: 12px 15px;
  background: var(--input-bg);
  border: 1px solid var(--border-default);
}

.login-tabs :deep(.el-input--large .el-input__inner) {
  height: 24px;
  line-height: 24px;
  color: var(--text-primary); /* 深色主题亮白色 */
}

/* 优化"记住我"复选框样式 */
.login-tabs :deep(.el-checkbox) {
  font-size: 14px;
  user-select: none;
}

.login-tabs :deep(.el-checkbox__label) {
  color: var(--text-secondary); /* 深色主题灰白色 */
  transition: color 0.3s ease;
}

.login-tabs :deep(.el-checkbox:hover .el-checkbox__label) {
  color: #409eff;
}

/* 忘记密码链接样式 */
.login-tabs :deep(.el-link) {
  font-size: 14px;
  transition: opacity 0.3s ease;
}

.login-tabs :deep(.el-link:hover) {
  opacity: 0.8;
}

/* 密码重置Dialog样式 */
:deep(.el-dialog) {
  border-radius: 8px;
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(0, 191, 255, 0.1);
  padding: 20px 20px 15px;
}

:deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

:deep(.el-dialog__body) {
  padding: 20px;
}

:deep(.el-dialog__footer) {
  border-top: 1px solid rgba(0, 191, 255, 0.1);
  padding: 15px 20px;
}

/* Dialog中的表单项样式 */
:deep(.el-dialog .el-form-item) {
  margin-bottom: 18px;
}

:deep(.el-dialog .el-input--large .el-input__wrapper) {
  padding: 10px 12px;
}

/* 1. 输入框和密码icon间距 */
.login-tabs :deep(.el-input--large .el-input__wrapper) {
  padding-left: 18px;
  padding-right: 18px;
  background: var(--input-bg);
}
.login-tabs :deep(.el-input__suffix) {
  margin-right: 8px;
}

/* 2. 密码可见icon hover发光高亮 */
.login-tabs :deep(.el-input__suffix .el-icon) {
  transition: color 0.3s, filter 0.3s;
}
.login-tabs :deep(.el-input__suffix .el-icon:hover) {
  color: #40a9ff !important;
  filter: drop-shadow(0 0 8px #40a9ff) drop-shadow(0 0 12px #2cecfa);
}

/* 3. 玻璃卡片增强，层次发光和渐变框 */
.login-card {
  box-shadow: 0 10px 40px 0 rgba(10, 80, 200, 0.14), 0 0 0 8px rgba(64,158,255,0.06) inset;
  border: 1.5px solid;
  border-image: linear-gradient(135deg, #38b3ff 20%, #0050ff 100%) 1;
  background: rgba(24,28,36,0.85);
  backdrop-filter: blur(22px);
}

/* 4. 高对比/色弱主题变量结构（UI入口预留，不显示） */
:root {
  --theme-mode: normal;
}
.theme-high-contrast {
  --text-primary: #fff;
  --input-bg: #151f2b;
  --surface-glass: rgba(30,60,180,0.98);
  --border-default: #64fff7;
  --btn-main: #ffff17;
}
.theme-color-blind {
  --text-primary: #fff;
  --input-bg: #191930;
  --surface-glass: rgba(50,100,200,0.99);
  --border-default: #0044ff;
  --btn-main: #ffae1a;
  /* 色弱模式下按钮淡黄、大标题加下划线区分 */
}
/* 可用JS/按钮切换 .theme-high-contrast/.theme-color-blind 应用对应主题 */

/* 5. 动效节奏统一 */
.data-stream {
  animation: dataFlow 8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
@keyframes dataFlow {
  0%   { transform: translateY(-100vh) scaleY(1); opacity: 0; }
  5%   { opacity: 0.2; }
  15%  { opacity: 0.7; }
  70%  { opacity: 0.8; }
  100% { transform: translateY(100vh) scaleY(1); opacity: 0; }
}
.particles { z-index: 1; }
.particle {
  animation: particleFloat 8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
@keyframes particleFloat {
  0%, 100% { transform: translateY(0) scale(0); opacity: 0; }
  10% { transform: translateY(-10px) scale(0.8); opacity: 0.3; }
  25% { transform: translateY(-20px) scale(1); opacity: 1; }
  80% { opacity: 0.6; }
}
</style>



