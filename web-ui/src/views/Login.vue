<template>
  <div class="login-container">
    <!-- 粒子背景效果 -->
    <vue-particles
      id="tsparticles"
      :options="particlesOptions"
    />
    
    <!-- 登录卡片 -->
    <el-card class="login-card">
      <!-- 标题 -->
      <div class="card-header">
        <!-- Logo图标 -->
        <div class="logo-container">
          <el-icon :size="48" class="logo-icon">
            <TrendCharts />
          </el-icon>
        </div>
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
            label-width="80px"
            @submit.prevent="handleLogin"
          >
            <el-form-item label="用户名" prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="请输入用户名"
                :prefix-icon="User"
              />
            </el-form-item>
            
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleLogin"
              />
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
            label-width="100px"
            @submit.prevent="handleRegister"
          >
            <el-form-item label="用户名" prop="username">
              <el-input
                v-model="registerForm.username"
                placeholder="请输入用户名（3-50字符）"
                :prefix-icon="User"
              />
            </el-form-item>
            
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="请输入密码（至少6位）"
                :prefix-icon="Lock"
                show-password
              />
            </el-form-item>
            
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="registerForm.confirmPassword"
                type="password"
                placeholder="请再次输入密码"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleRegister"
              />
            </el-form-item>
            
            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="registerForm.email"
                placeholder="请输入邮箱（可选）"
                :prefix-icon="Message"
              />
            </el-form-item>
            
            <el-form-item label="全名" prop="full_name">
              <el-input
                v-model="registerForm.full_name"
                placeholder="请输入全名（可选）"
                :prefix-icon="UserFilled"
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Message, UserFilled, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('login')

// 监听Tab切换，自动聚焦第一个输入框
watch(activeTab, async (newTab) => {
  await nextTick()
  const firstInput = document.querySelector(`[name="${newTab}"] .el-input__inner`)
  if (firstInput) {
    firstInput.focus()
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
      value: ['#00d4ff', '#0090ff', '#0066cc']
    },
    links: {
      enable: true,
      color: '#00bfff',
      distance: 150,
      opacity: 0.3,
      width: 1
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
      value: 0.5
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

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    loginLoading.value = true
    try {
      const success = await userStore.login(loginForm)
      if (success) {
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
  .login-card {
    width: 100%;
    max-width: 100%;
    margin: 10px;
  }
  
  .card-header h2 {
    font-size: 20px;
  }
  
  .login-tabs :deep(.el-form-item__label) {
    font-size: 14px;
  }
}

.card-header {
  text-align: center;
  padding: 30px 0 20px 0;
  border-bottom: 1px solid rgba(0, 191, 255, 0.1);
  margin-bottom: 10px;
}

/* Logo容器样式 */
.logo-container {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

/* Logo图标样式 */
.logo-icon {
  background: linear-gradient(135deg, #0066cc, #0090ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 4px 8px rgba(0, 102, 204, 0.4));
  animation: logoFloat 3s ease-in-out infinite;
}

/* Logo浮动动画 */
@keyframes logoFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

.card-header h2 {
  margin: 0 0 10px 0;
  color: #1a1a1a;
  font-size: 24px;
  font-weight: 600;
  background: linear-gradient(135deg, #0090ff, #00d4ff);
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

.login-tabs :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}
</style>

