<template>
  <div class="login-container">
    <!-- 粒子背景效果 -->
    <vue-particles
      id="tsparticles"
      :options="particlesOptions"
    />
    
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
        <el-select
          v-model="currentLanguage"
          placeholder="语言"
          size="default"
          @change="handleLanguageChange"
        >
          <el-option
            v-for="item in languageOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          >
            <span class="language-option-content">
              <span class="language-icon">{{ item.icon }}</span>
              <span class="language-text">{{ item.label }}</span>
            </span>
          </el-option>
        </el-select>
      </div>
    </div>
    
    <!-- 登录卡片 -->
    <el-card class="login-card">
      <!-- 标题 -->
      <div class="card-header">
        <h2>Homalos 量化交易系统</h2>
        <p>{{ activeTab === 'login' ? '欢迎登录' : '注册新账号' }}</p>
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
                placeholder="邮箱（可选，用于找回密码）"
                :prefix-icon="Message"
                size="large"
              />
            </el-form-item>
            
            <el-form-item prop="full_name">
              <el-input
                v-model="registerForm.full_name"
                placeholder="全名（可选）"
                :prefix-icon="UserFilled"
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
  console.log('语言切换:', value)
  ElMessage.success(`语言已切换为: ${languageOptions.find(item => item.value === value)?.label}`)
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

// 根据设备类型动态设置粒子数量
const particleCount = computed(() => isMobile.value ? 40 : 70)

// 粒子效果配置（经典连线效果 + 性能优化）
const particlesOptions = computed(() => ({
  background: {
    color: {
      value: 'transparent'
    }
  },
  fpsLimit: 60,
  pauseOnBlur: true, // 页面失焦时暂停动画，节省资源
  particles: {
    number: {
      value: particleCount.value, // 响应式粒子数量
      density: {
        enable: true,
        area: 800
      }
    },
    color: {
      value: ['#00ff00', '#ff0000']
    },
    shadow: {
      enable: true,
      color: '#00ff00',
      blur: 20
    },
    stroke: {
      width: 0,
      color: '#ffffff',
      opacity: 0.2
    },
    links: {
      enable: true,
      color: '#666666',
      distance: 150,
      opacity: 0.6,
      width: 1.5
    },
    move: {
      enable: true,
      speed: 2,
      direction: 'none',
      random: false,
      straight: false,
      outModes: {
        default: 'bounce'
      }
    },
    opacity: {
      value: { min: 0.1, max: 0.9 },
      animation: {
        enable: true,
        speed: 1.5,
        sync: false
      }
    },
    shape: {
      type: 'circle'
    },
    size: {
      value: { min: 2, max: 6 }
    }
  },
  interactivity: {
    detectsOn: 'canvas',
    events: {
      onHover: {
        enable: !isMobile.value, // 移动端禁用鼠标交互以节省资源
        mode: 'grab'
      },
      resize: true
    },
    modes: {
      grab: {
        distance: 140,
        links: {
          opacity: 0.5
        }
      }
    }
  },
  detectRetina: true
}))

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
  email: '',
  full_name: ''
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
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #f5f5f7;
  overflow: hidden;
}

/* 粒子背景层 */
#tsparticles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  filter: brightness(1.1) contrast(1.05);
}

/* 粒子发光增强效果 */
#tsparticles canvas {
  filter: blur(0.5px) brightness(1.1);
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
  background: linear-gradient(135deg, #0066cc, #0090ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 2px 4px rgba(0, 102, 204, 0.3));
}

/* 右侧语言切换 */
.nav-language {
  display: flex;
  align-items: center;
}

.nav-language :deep(.el-select) {
  width: 160px;
}

.nav-language :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: none;
  transition: all 0.3s ease;
}

.nav-language :deep(.el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 4px 12px rgba(0, 102, 204, 0.15);
}

.nav-language :deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 0 1px rgba(0, 102, 204, 0.3) inset, 0 4px 12px rgba(0, 102, 204, 0.15);
}

/* 下拉选项内容 */
.language-option-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.language-icon {
  font-size: 18px;
  line-height: 1;
}

.language-text {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.login-card {
  position: relative;
  width: 500px;
  max-width: 95%;
  margin: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  z-index: 1;
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

@media (max-width: 768px) {
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
  color: #1a1a1a;
  font-size: 24px;
  font-weight: 600;
  background: linear-gradient(135deg, #0066cc, #0090ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.card-header p {
  margin: 0;
  color: #606266;
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
  transition: all 0.3s ease;
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

/* 优化输入框聚焦效果 */
.login-tabs :deep(.el-input__wrapper) {
  transition: all 0.3s ease;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

.login-tabs :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

.login-tabs :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset, 0 0 8px rgba(64, 158, 255, 0.2);
}

/* 保留label样式以防未来需要 */
.login-tabs :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
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
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

.login-tabs :deep(.el-input--large .el-input__inner) {
  height: 24px;
  line-height: 24px;
}

/* 优化"记住我"复选框样式 */
.login-tabs :deep(.el-checkbox) {
  font-size: 14px;
  user-select: none;
}

.login-tabs :deep(.el-checkbox__label) {
  color: #606266;
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
</style>



