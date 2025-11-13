<template>
  <div class="admin-register-page">
    <!-- 简洁背景 -->
    <div class="background-overlay">
      <!-- 粒子效果 -->
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
    
    <!-- 顶部导航 -->
    <div class="top-nav">
      <div class="nav-logo" @click="$router.push('/login')">
        <el-icon :size="28" class="nav-logo-icon">
          <TrendCharts />
        </el-icon>
        <span class="nav-logo-text">Homalos</span>
        <span class="nav-logo-subtitle">管理员注册</span>
      </div>
      
      <div class="nav-actions">
        <el-button 
          type="primary" 
          plain 
          @click="$router.push('/login')"
          class="back-btn"
        >
          <el-icon><ArrowLeft /></el-icon>
          返回登录
        </el-button>
      </div>
    </div>
    
    <!-- 注册卡片 -->
    <div class="register-container">
      <el-card class="register-card">
        <template #header>
          <div class="card-header">
            <el-icon class="header-icon" :size="32">
              <UserFilled />
            </el-icon>
            <h2>管理员注册</h2>
            <p class="card-subtitle">创建 Homalos 管理员账户</p>
          </div>
        </template>
        
        <AdminRegister 
          @success="handleRegisterSuccess" 
          @cancel="$router.push('/login')"
          @back-to-login="$router.push('/login')"
          :show-cancel="true"
        />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { TrendCharts, UserFilled, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AdminRegister from '@/components/AdminRegister.vue'

const router = useRouter()

// 注册成功处理
const handleRegisterSuccess = (adminInfo) => {
  ElMessage.success('管理员注册成功！请使用新账户登录')
  
  // 跳转到登录页面并自动填充用户名
  router.push({
    path: '/login',
    query: { username: adminInfo.username }
  })
}

</script>

<style scoped>
.admin-register-page {
  /* CSS变量定义 */
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
  min-height: 100vh;
  background: linear-gradient(135deg, #05090f 0%, #0b1120 58%, #101725 100%);
  overflow-x: hidden;
  overflow-y: auto;
}


/* 简洁背景 */
.background-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 0;
  background: linear-gradient(135deg, #05090f 0%, #0b1120 50%, #101725 100%);
  pointer-events: none;
}

.background-overlay::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at 30% 20%, rgba(64, 158, 255, 0.05) 0%, transparent 50%),
              radial-gradient(circle at 70% 80%, rgba(64, 158, 255, 0.03) 0%, transparent 50%);
  animation: backgroundPulse 8s ease-in-out infinite alternate;
}

/* 粒子效果 */
.particles {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  z-index: 1;
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
    transform: translateY(-15px) translateX(-5px) scale(0.5); 
    opacity: 0.3; 
  }
  25% { 
    transform: translateY(-30px) translateX(-10px) scale(1); 
    opacity: 1; 
  }
  50% { 
    transform: translateY(-45px) translateX(-15px) scale(1.2); 
    opacity: 0.8; 
  }
  75% { 
    transform: translateY(-60px) translateX(-20px) scale(0.8); 
    opacity: 0.4; 
  }
}

@keyframes backgroundPulse {
  0% { opacity: 0.3; }
  100% { opacity: 0.6; }
}

/* 顶部导航 */
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
  background: rgba(12, 18, 35, 0.8);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(64, 158, 255, 0.1);
  z-index: 10;
}

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
  color: rgba(255, 255, 255, 0.6);
  font-weight: 400;
  padding-left: 12px;
  border-left: 1px solid rgba(255, 255, 255, 0.15);
}

.back-btn {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(64, 158, 255, 0.3) !important;
  color: #ffffff !important;
  transition: all 0.3s ease !important;
}

.back-btn:hover {
  background: rgba(64, 158, 255, 0.15) !important;
  border-color: rgba(64, 158, 255, 0.5) !important;
  transform: translateY(-1px);
}

/* 注册容器 */
.register-container {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: calc(100vh - 70px);
  padding: 100px 20px 40px;
  position: relative;
  z-index: 5;
}

.register-card {
  position: relative;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  background: rgba(18, 28, 48, 0.98) !important;
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  z-index: 5;
  border: none !important;
  border-image: none !important;
  border-radius: 16px;
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(64, 158, 255, 0.1) inset,
    0 8px 32px rgba(64, 158, 255, 0.1);
  overflow: visible;
}

.card-header {
  text-align: center;
  padding: 20px 0;
}

.header-icon {
  background: linear-gradient(135deg, #4a9eff 0%, #67b5ff 50%, #409eff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 16px;
}

.card-header h2 {
  font-size: 28px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px 0;
  background: linear-gradient(135deg, #ffffff 0%, #b3d9ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.card-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
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
  
  .register-container {
    padding: 80px 15px 30px;
    min-height: calc(100vh - 60px);
  }
  
  .register-card {
    max-width: 100%;
    margin: 0;
    border-radius: 12px;
  }
  
  .card-header h2 {
    font-size: 24px;
  }
}
</style>
