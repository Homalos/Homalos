<template>
  <div class="login-container">
    <!-- 深色主题动画背景 -->
    <div class="video-background">
      <svg class="kline-draw-svg" width="100%" height="100%" viewBox="0 0 1440 900" preserveAspectRatio="none">
        <defs>
          <!-- K线上涨渐变 - 优化：增强对比度和科技感 -->
          <linearGradient id="klineUpGradient" x1="0" y1="900" x2="1440" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#1e88e5"/>
            <stop offset="50%" stop-color="#64b5f6"/>
            <stop offset="100%" stop-color="#2196f3"/>
          </linearGradient>
          <!-- 水平线渐变 - 优化：更明显的流动感 -->
          <linearGradient id="lineFlowGrad" x1="0" y1="0" x2="1440" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#42aaff"/>
            <stop offset="50%" stop-color="#90caf9"/>
            <stop offset="100%" stop-color="#2196f3"/>
          </linearGradient>
        </defs>
        <!-- 水平参考线 - 优化：增强透明度和发光效果 -->
        <rect x="170" y="90" width="1100" height="2.5" rx="1" fill="url(#lineFlowGrad)" style="filter:drop-shadow(0 0 4px #76c3fa);opacity:0.3" class="reference-line" />
        <rect x="170" y="445" width="1100" height="2.5" rx="1" fill="url(#lineFlowGrad)" style="filter:drop-shadow(0 0 4px #76c3fa);opacity:0.3" class="reference-line" />
        <rect x="170" y="800" width="1100" height="2.5" rx="1" fill="url(#lineFlowGrad)" style="filter:drop-shadow(0 0 4px #76c3fa);opacity:0.3" class="reference-line" />
        <!-- 起点标记（红色下跌箭头） - 优化：增强发光效果 -->
        <polygon v-if="klineDrawPoints.length" :points="`${klineDrawPoints[0].x},${klineDrawPoints[0].y-15} ${klineDrawPoints[0].x-7},${klineDrawPoints[0].y-3} ${klineDrawPoints[0].x+7},${klineDrawPoints[0].y-3}`"
          fill="#ff2c55" style="filter:drop-shadow(0 0 5px #f87b88) drop-shadow(0 0 10px rgba(255, 44, 85, 0.4));" class="start-marker" />
        <!-- 终点标记（绿色上涨箭头） - 优化：增强发光效果 -->
        <polygon v-if="klineDrawPoints.length && revealCount===klineDrawPoints.length"
          :points="`${klineDrawPoints[revealCount-1].x},${klineDrawPoints[revealCount-1].y+15} ${klineDrawPoints[revealCount-1].x-7},${klineDrawPoints[revealCount-1].y+3} ${klineDrawPoints[revealCount-1].x+7},${klineDrawPoints[revealCount-1].y+3}`"
          fill="#00e349" style="filter:drop-shadow(0 0 5px #47ff8c) drop-shadow(0 0 10px rgba(0, 227, 73, 0.4));" class="end-marker" />
        <polyline
          :points="drawLinePS"
          class="kline-draw-polyline"
          stroke="url(#klineUpGradient)"
          stroke-width="6"
          fill="none"
        />
      </svg>
    </div>
    
    <!-- 顶部导航栏 -->
    <div class="top-nav">
      <!-- 左侧Logo -->
      <div class="nav-logo">
        <el-icon :size="28" class="nav-logo-icon">
          <TrendCharts />
        </el-icon>
        <span class="nav-logo-text">Homalos</span>
        <span class="nav-logo-subtitle">量化交易系统</span>
      </div>
      
      <!-- 右侧操作区 -->
      <div class="nav-actions">
        <!-- 管理员注册按钮 -->
        <el-tooltip content="管理员注册" placement="bottom">
          <el-button
            type="primary"
            plain
            size="small"
            @click="$router.push('/admin/register')"
            class="admin-register-btn"
          >
            <el-icon>
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M12,7C13.4,7 14.8,8.6 14.8,10V11.4C14.8,12.8 13.4,14.4 12,14.4C10.6,14.4 9.2,12.8 9.2,11.4V10C9.2,8.6 10.6,7 12,7M18,11C18,15.1 15.1,18 12,18C8.9,18 6,15.1 6,11V6.3L12,3.7L18,6.3V11Z"/>
              </svg>
            </el-icon>
            管理员注册
          </el-button>
        </el-tooltip>
        
        <!-- 语言切换 -->
        <div class="nav-language">
          <el-dropdown @command="handleLanguageChange" trigger="hover" placement="bottom-end">
          <div class="language-selector">
            <svg class="language-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <line x1="2" y1="12" x2="22" y2="12"/>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
            <span class="language-text">{{ languageOptions.find(item => item.value === currentLanguage)?.label || '简体中文' }}</span>
            <svg class="arrow-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"/>
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
                  <span class="language-emoji">{{ item.icon }}</span>
                  <span class="language-label">{{ item.label }}</span>
                  <svg v-if="currentLanguage === item.value" class="check-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                </span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        </div>
      </div>
    </div>
    
    <!-- 登录卡片 -->
    <el-card class="login-card">
      <!-- 标题 -->
      <div class="card-header">
        <h2>{{ activeTab === 'login' ? '欢迎登录' : '创建账户' }}</h2>
        <p class="card-subtitle">{{ activeTab === 'login' ? '登录您的 Homalos 账户' : '注册新的 Homalos 账户' }}</p>
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
import { useRouter, useRoute } from 'vue-router'
import { User, Lock, Message, UserFilled, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
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

// 组件挂载时，从URL参数或localStorage加载用户名
onMounted(() => {
  // 优先检查URL参数中的username
  const urlUsername = route.query.username
  if (urlUsername) {
    loginForm.username = urlUsername
    ElMessage.success('已为您自动填充用户名，请输入密码登录')
  } else {
    // 如果URL中没有username，则从localStorage加载保存的用户名
    const savedUsername = localStorage.getItem('homalos_remember_username')
    if (savedUsername) {
      loginForm.username = savedUsername
      rememberMe.value = true
    }
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


// 登录K线动态延展折线 - 上升趋势、延展动画
const KLINE_PCOUNT = 38
const SVG_WIDTH = 1440
const SVG_HEIGHT = 900
const BASE_START_Y = SVG_HEIGHT * 0.7
const BASE_END_Y = SVG_HEIGHT * 0.22
// 常量区调整：
const BASE_START_X = 200
const BASE_END_X = SVG_WIDTH - BASE_START_X
function makeBigVolatileKLinePoints() {
  const arr = []
  let lastX = BASE_START_X, lastY = BASE_START_Y
  for (let i = 0; i < KLINE_PCOUNT; i++) {
    const frac = i / (KLINE_PCOUNT - 1)
    const x = BASE_START_X + frac * (BASE_END_X - BASE_START_X) + Math.random() * 16 * Math.pow(frac, 2)
    let yBase = BASE_START_Y + frac * (BASE_END_Y - BASE_START_Y)
    // 波动更大：拉升与回调加倍
    if (i && (i % 10 === 5 || i % 17 === 3)) yBase += 45 + Math.random() * 40  // 回调放大
    if (i && (i % 7 === 2 || i % 11 === 6)) yBase -= 60 + Math.random() * 30   // 拉升放大
    // y扰动放大
    const y = yBase + (Math.random() - 0.5) * 40
    // x范围绝不越界
    arr.push({ x: Math.max(BASE_START_X, Math.min(BASE_END_X, x)), y })
    lastX = x; lastY = y
  }
  return arr
}
const klineDrawPoints = ref(makeBigVolatileKLinePoints())
const revealCount = ref(1)
const drawLinePS = computed(() => klineDrawPoints.value.slice(0,revealCount.value).map(p=>`${p.x},${p.y}`).join(' '))
let drawTimer = null
onMounted(() => {
  const drawNext = () => {
    revealCount.value = 1
    klineDrawPoints.value = makeBigVolatileKLinePoints()
    drawTimer = setInterval(() => {
      if (revealCount.value < klineDrawPoints.value.length) {
        revealCount.value++
      } else if (drawTimer) {
        clearInterval(drawTimer)
        drawTimer = null
        // 动画停留5秒再循环（优化：让用户更好地欣赏完整动画）
        setTimeout(() => {
          drawNext()
        }, 5000)
      }
    }, 300)
  }
  drawNext()
})

const drawLineMinY = computed(() => Math.max(...klineDrawPoints.value.map(p => p.y)) + 40)
const drawLineMaxY = computed(() => Math.min(...klineDrawPoints.value.map(p => p.y)) - 40)
const drawLineMinX = computed(() => Math.min(...klineDrawPoints.value.map(p => p.x)))
const drawLineMaxX = computed(() => Math.max(...klineDrawPoints.value.map(p => p.x)))
const lineRectX = computed(() => Math.max(0, drawLineMinX.value-30))
const lineRectW = computed(() => Math.max(drawLineMaxX.value-drawLineMinX.value+60, 50))
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
  background: linear-gradient(135deg, #05090f 0%, #0b1120 58%, #101725 100%);
  overflow: hidden;
  height: 100vh; width: 100vw; position: relative;
}
.login-container::before {
  content: '';
  position: absolute; left: 0; top:0; width: 100vw; height: 100vh;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(circle at 70% 60%, rgba(120,145,240,0.14) 0%, rgba(100,220,245,0.05) 49%, rgba(40,30,80,0.18) 100%),
    radial-gradient(circle at 30% 40%, rgba(22,28,120,0.11) 0%, rgba(100,120,180,0.09) 57%, rgba(0,0,0,0.14) 100%);
  filter: blur(6px);
}
.video-background{
  height:100vh; width:100vw; position:relative;
  background: linear-gradient(120deg, #070a12 0%, #0c1422 95%, #0f1523 100%);
  background: transparent !important;
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


/* 顶部导航栏 */
.top-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 70px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  background: rgba(12, 18, 35, 0.6);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(64, 158, 255, 0.1);
  z-index: 10;
}

/* 左侧Logo */
.nav-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
  transition: all 0.3s ease;
}

.nav-logo:hover {
  transform: translateX(2px);
}

.nav-logo-icon {
  background: linear-gradient(135deg, #4a9eff 0%, #67b5ff 50%, #409eff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  transition: all 0.3s ease;
}

.nav-logo-icon svg {
  filter: drop-shadow(0 0 8px rgba(64, 158, 255, 0.4));
}

.nav-logo:hover .nav-logo-icon svg {
  filter: drop-shadow(0 0 12px rgba(64, 158, 255, 0.6));
}

.nav-logo-text {
  font-size: 22px;
  font-weight: 600;
  background: linear-gradient(135deg, #ffffff 0%, #b3d9ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.5px;
}

.nav-logo-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 400;
  padding-left: 12px;
  border-left: 1px solid rgba(255, 255, 255, 0.15);
}

@media (max-width: 768px) {
  .nav-logo-icon {
    font-size: 24px;
  }
  
  .nav-logo-subtitle {
    display: none;
  }
}

/* 右侧操作区 */
.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 管理员注册按钮 */
.admin-register-btn {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(64, 158, 255, 0.3) !important;
  color: #ffffff !important;
  transition: all 0.3s ease !important;
  backdrop-filter: blur(8px);
}

.admin-register-btn:hover {
  background: rgba(64, 158, 255, 0.15) !important;
  border-color: rgba(64, 158, 255, 0.5) !important;
  box-shadow: 0 0 16px rgba(64, 158, 255, 0.3) !important;
  transform: translateY(-1px);
}

.admin-register-btn .el-icon {
  margin-right: 6px;
}

/* 右侧语言切换 */
.nav-language {
  display: flex;
  align-items: center;
}

/* 语言切换选择器 */
.language-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(8px);
}

.language-selector:hover {
  background: rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.4);
  box-shadow: 0 0 16px rgba(64, 158, 255, 0.2);
}

.language-selector .language-icon {
  color: rgba(255, 255, 255, 0.7);
  transition: color 0.3s ease;
}

.language-selector:hover .language-icon {
  color: #409eff;
}

.language-selector .language-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
  font-weight: 500;
  min-width: 70px;
}

.language-selector .arrow-icon {
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.3s ease;
}

.language-selector:hover .arrow-icon {
  color: #409eff;
  transform: translateY(1px);
}

/* 下拉菜单容器 */
.language-dropdown-menu {
  background: rgba(18, 28, 48, 0.96) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(64, 158, 255, 0.25) !important;
  border-radius: 8px !important;
  padding: 6px !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(64, 158, 255, 0.1) inset !important;
  min-width: 160px !important;
}

/* 下拉菜单项 - 增强选择器优先级 */
.el-dropdown-menu.language-dropdown-menu .el-dropdown-menu__item,
.language-dropdown-menu.el-dropdown-menu .el-dropdown-menu__item {
  color: #f0f2f5 !important; /* 亮白色 */
  padding: 10px 14px !important;
  border-radius: 6px !important;
  margin: 2px 0 !important;
  transition: all 0.2s ease !important;
}

.el-dropdown-menu.language-dropdown-menu .el-dropdown-menu__item:hover,
.language-dropdown-menu.el-dropdown-menu .el-dropdown-menu__item:hover {
  background: rgba(64, 158, 255, 0.15) !important;
  color: #ffffff !important;
}

.el-dropdown-menu.language-dropdown-menu .el-dropdown-menu__item.is-active,
.language-dropdown-menu.el-dropdown-menu .el-dropdown-menu__item.is-active {
  background: rgba(64, 158, 255, 0.25) !important;
  color: #ffffff !important;
  font-weight: 600; /* 更醒目 */
}

/* 下拉选项内容 */
.language-option-content {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: space-between;
  width: 100%;
}

.language-emoji {
  font-size: 18px;
  line-height: 1;
}

/* 语言标签文字 - 确保亮白色 */
.language-dropdown-menu .language-label,
.el-dropdown-menu.language-dropdown-menu .language-label {
  flex: 1;
  font-size: 14px;
  color: #f0f2f5 !important; /* 强制亮白色 */
  font-weight: 500; /* 增加字重，更清晰 */
}

/* Hover和激活状态下的文字颜色 */
.language-dropdown-menu .el-dropdown-menu__item:hover .language-label,
.language-dropdown-menu .el-dropdown-menu__item.is-active .language-label {
  color: #ffffff !important; /* 纯白色 */
  font-weight: 600 !important;
}

.check-icon {
  color: #409eff;
  flex-shrink: 0;
}

.login-card {
  position: relative;
  width: 500px;
  max-width: 95%;
  margin: 20px;
  /* box-shadow、background等保持不变 */
  background: rgba(18, 28, 48, 0.98) !important;
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  z-index: 5;
  /* 完全无边框、无渐变描边 */
  border: none !important;
  border-image: none !important;
}
.kline-draw-svg, .video-background {
  z-index: 0 !important;
  background: transparent !important;
  pointer-events: none !important;
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
    height: 60px;
    padding: 0 20px;
  }
  
  .nav-logo-text {
    font-size: 18px;
  }
  
  .nav-logo-subtitle {
    display: none;
  }
  
  .language-selector {
    padding: 6px 12px;
  }
  
  .language-selector .language-text {
    min-width: 50px;
    font-size: 13px;
  }
  
  /* 移动端登录卡片 */
  .login-card {
    width: 100%;
    max-width: 100%;
    margin: 10px;
  }
  
  .card-header {
    padding: 25px 25px 18px 25px;
  }
  
  .card-header h2 {
    font-size: 22px;
  }
  
  .card-subtitle {
    font-size: 13px;
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
    margin-bottom: 20px; /* 从16px增加到20px，避免误触 */
  }
  
  /* 移动端输入框触摸优化 */
  .login-tabs :deep(.el-input--large .el-input__wrapper) {
    min-height: 48px; /* 符合移动端最小触摸区域标准 */
    padding: 14px 15px; /* 增加内边距，触摸更舒适 */
  }
  
  /* 移动端禁用输入框hover效果（触摸设备不需要） */
  .login-tabs :deep(.el-input__wrapper:hover) {
    transform: none;
  }
  
  /* 移动端focus状态不上浮（避免内容跳动） */
  .login-tabs :deep(.el-input__wrapper.is-focus) {
    transform: none;
  }
  
  /* 移动端按钮触摸优化 */
  .login-tabs :deep(.el-button) {
    min-height: 48px; /* 符合移动端最小触摸区域标准 */
    font-size: 16px; /* 防止iOS自动缩放 */
  }
}

.card-header {
  text-align: center;
  padding: 30px 50px 20px 50px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.08);
  margin-bottom: 10px;
}

.card-header h2 {
  margin: 0 0 8px 0;
  color: var(--text-primary);
  font-size: 26px;
  font-weight: 600;
  background: linear-gradient(135deg, #ffffff 0%, #b3d9ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.card-subtitle {
  margin: 0;
  color: rgba(255, 255, 255, 0.5);
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

/* 优化按钮视觉反馈 - 渐变背景增强 */
.login-tabs :deep(.el-button) {
  font-weight: 500;
  letter-spacing: 0.5px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

/* 主要按钮（登录）- 蓝色科技渐变 */
.login-tabs :deep(.el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
}

.login-tabs :deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%) !important;
  transform: translateY(-3px) !important;
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.45) !important;
}

.login-tabs :deep(.el-button--primary:active) {
  transform: translateY(-1px) !important;
  box-shadow: 0 3px 10px rgba(64, 158, 255, 0.4) !important;
}

.login-tabs :deep(.el-button--primary.is-loading) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
  opacity: 0.9 !important;
  transform: none !important;
}

/* 成功按钮（注册）- 绿色渐变 */
.login-tabs :deep(.el-button--success) {
  background: linear-gradient(135deg, #67c23a 0%, #4a9e2b 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.35) !important;
}

.login-tabs :deep(.el-button--success:hover) {
  background: linear-gradient(135deg, #85ce61 0%, #67c23a 100%) !important;
  transform: translateY(-3px) !important;
  box-shadow: 0 6px 20px rgba(103, 194, 58, 0.45) !important;
}

.login-tabs :deep(.el-button--success:active) {
  transform: translateY(-1px) !important;
  box-shadow: 0 3px 10px rgba(103, 194, 58, 0.4) !important;
}

.login-tabs :deep(.el-button--success.is-loading) {
  background: linear-gradient(135deg, #67c23a 0%, #4a9e2b 100%) !important;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.35) !important;
  opacity: 0.9 !important;
  transform: none !important;
}

/* 默认按钮（取消等）- 深色玻璃质感 */
.login-tabs :deep(.el-button--default) {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.05) 100%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.login-tabs :deep(.el-button--default:hover) {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0.08) 100%);
  border-color: rgba(64, 158, 255, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.login-tabs :deep(.el-button--default:active) {
  transform: translateY(0);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

/* 优化输入框聚焦效果 - 深色主题增强版 */
.login-tabs :deep(.el-input__wrapper) {
  background: var(--input-bg); /* 深色半透明背景 */
  border: 1px solid var(--border-default);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  position: relative;
}

.login-tabs :deep(.el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(64, 158, 255, 0.4);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.login-tabs :deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.12);
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15),
              0 0 12px rgba(64, 158, 255, 0.4),
              0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

/* Focus状态下的脉冲动画 */
.login-tabs :deep(.el-input__wrapper.is-focus)::before {
  content: '';
  position: absolute;
  top: -1px;
  left: -1px;
  right: -1px;
  bottom: -1px;
  border-radius: inherit;
  border: 1px solid #409eff;
  opacity: 0;
  animation: focusPulse 2s ease-in-out infinite;
  pointer-events: none;
}

@keyframes focusPulse {
  0%, 100% {
    opacity: 0;
    transform: scale(1);
  }
  50% {
    opacity: 0.3;
    transform: scale(1.02);
  }
}

/* 前缀图标（用户名、密码、邮箱图标）增强 */
.login-tabs :deep(.el-input__prefix) {
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Hover状态时前缀图标变亮 */
.login-tabs :deep(.el-input__wrapper:hover .el-input__prefix) {
  color: rgba(255, 255, 255, 0.7);
}

/* Focus状态时前缀图标高亮并发光 */
.login-tabs :deep(.el-input__wrapper.is-focus .el-input__prefix) {
  color: #409eff;
  filter: drop-shadow(0 0 4px rgba(64, 158, 255, 0.6));
  transform: scale(1.1);
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

/* Dialog中输入框的focus状态增强 */
:deep(.el-dialog .el-input__wrapper) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

:deep(.el-dialog .el-input__wrapper:hover) {
  border-color: rgba(64, 158, 255, 0.4);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

:deep(.el-dialog .el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15),
              0 0 12px rgba(64, 158, 255, 0.3),
              0 4px 12px rgba(0, 0, 0, 0.1);
}

/* Dialog中前缀图标的focus状态 */
:deep(.el-dialog .el-input__wrapper.is-focus .el-input__prefix) {
  color: #409eff;
  filter: drop-shadow(0 0 4px rgba(64, 158, 255, 0.6));
}

/* Dialog中的按钮渐变优化 */
:deep(.el-dialog .el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-dialog .el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45) !important;
}

:deep(.el-dialog .el-button--default) {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.05) 100%);
  border: 1px solid rgba(0, 0, 0, 0.1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-dialog .el-button--default:hover) {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0.08) 100%);
  border-color: rgba(64, 158, 255, 0.2);
  transform: translateY(-2px);
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

/* 2. 密码可见icon hover发光高亮 - 增强版 */
.login-tabs :deep(.el-input__suffix .el-icon) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  border-radius: 4px;
  padding: 2px;
}
.login-tabs :deep(.el-input__suffix .el-icon:hover) {
  color: #40a9ff !important;
  filter: drop-shadow(0 0 8px #40a9ff) drop-shadow(0 0 12px #2cecfa);
  transform: scale(1.15);
  background: rgba(64, 158, 255, 0.1);
}
.login-tabs :deep(.el-input__suffix .el-icon:active) {
  transform: scale(1.05);
  filter: drop-shadow(0 0 6px #40a9ff);
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
.kline-draw-polyline {
  stroke-width:6; /* 从8减少到6，线条更精致 */
  filter:drop-shadow(0 0 6px #307efd) drop-shadow(0 0 12px rgba(48, 126, 253, 0.4)); /* 双层发光，科技感更强 */
  opacity:0.5; /* 从0.3提升到0.5，更清晰可见 */
  animation: klineGlow 3s ease-in-out infinite; /* 添加呼吸灯效果 */
}

/* K线呼吸灯动画 - 微妙的明暗变化 */
@keyframes klineGlow {
  0%, 100% {
    opacity: 0.5;
    filter: drop-shadow(0 0 6px #307efd) drop-shadow(0 0 12px rgba(48, 126, 253, 0.4));
  }
  50% {
    opacity: 0.65;
    filter: drop-shadow(0 0 8px #307efd) drop-shadow(0 0 16px rgba(48, 126, 253, 0.5));
  }
}

/* 水平参考线呼吸效果 */
.reference-line {
  animation: referenceGlow 4s ease-in-out infinite;
}

@keyframes referenceGlow {
  0%, 100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.45;
  }
}

/* 起点标记动画 - 红色下跌箭头从上往下移动 */
.start-marker {
  animation: startMarkerMove 2s ease-in-out infinite;
  transform-origin: center;
}

@keyframes startMarkerMove {
  0%, 100% {
    opacity: 0.9;
    transform: translateY(-3px);
  }
  50% {
    opacity: 1;
    transform: translateY(3px); /* 向下移动 */
  }
}

/* 终点标记动画 - 绿色上涨箭头从下往上移动 */
.end-marker {
  animation: endMarkerMove 2s ease-in-out infinite;
  transform-origin: center;
}

@keyframes endMarkerMove {
  0%, 100% {
    opacity: 0.9;
    transform: translateY(3px);
  }
  50% {
    opacity: 1;
    transform: translateY(-3px); /* 向上移动 */
  }
}
.login-card {
  position:relative;
  z-index:2;
}
</style>



