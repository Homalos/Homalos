# Homalos Web系统使用指南

## 后端架构

### 目录结构

```
src/web/
├── __init__.py
├── main.py                    # FastAPI应用入口
├── api/                       # API路由
│   ├── __init__.py
│   └── auth.py               # 认证API
├── core/                      # 核心功能
│   ├── __init__.py
│   ├── database.py           # 数据库连接
│   └── security.py           # JWT认证
├── models/                    # 数据模型
│   ├── __init__.py
│   ├── base.py               # 基础模型
│   └── user.py               # 用户模型
├── schemas/                   # Pydantic模式
│   ├── __init__.py
│   ├── user.py
│   ├── token.py
│   └── response.py
└── services/                  # 业务逻辑
    ├── __init__.py
    └── auth_service.py       # 认证服务
```

## 启动后端服务

### 方式1：使用批处理文件（Windows）

```bash
start_web.bat
```

### 方式2：使用Python脚本

```bash
.venv\Scripts\activate
python start_web.py
```

### 方式3：直接运行

```bash
.venv\Scripts\activate
uvicorn src.web.main:app --reload --port 8000
```

## API文档

启动服务后访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API接口说明

### 认证接口

#### 1. 用户注册

- **URL**: `POST /api/auth/register`
- **请求体**:
  ```json
  {
    "username": "admin",
    "password": "123456",
    "email": "admin@example.com",
    "full_name": "管理员"
  }
  ```
- **响应**:
  ```json
  {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "管理员",
    "role": "user",
    "is_active": true,
    "created_at": "2025-10-08T10:00:00",
    "last_login": null
  }
  ```

#### 2. 用户登录

- **URL**: `POST /api/auth/login`
- **请求体** (表单格式):
  ```
  username=admin
  password=123456
  ```
- **响应**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
  ```

#### 3. 获取当前用户信息

- **URL**: `GET /api/auth/me`
- **请求头**: 
  ```
  Authorization: Bearer <access_token>
  ```
- **响应**: 用户信息对象

## 前端架构

### 目录结构

```
web-ui/
├── public/                     # 静态资源
├── src/
│   ├── api/                   # API请求
│   │   ├── request.js        # Axios配置
│   │   └── auth.js           # 认证API
│   ├── assets/                # 资源文件
│   ├── components/            # 通用组件
│   ├── router/                # 路由配置
│   │   └── index.js
│   ├── stores/                # Pinia状态管理
│   │   └── user.js           # 用户状态
│   ├── utils/                 # 工具函数
│   ├── views/                 # 页面组件
│   │   ├── Login.vue         # 登录页
│   │   └── Home.vue          # 主页
│   ├── App.vue                # 根组件
│   └── main.js                # 入口文件
├── index.html
├── package.json
└── vite.config.js             # Vite配置
```

## 初始化管理员账户

在首次使用Web系统前，需要创建管理员账户：

### 方式1：使用批处理文件（Windows）

```bash
init_admin.bat
```

### 方式2：使用Python脚本

```bash
.venv\Scripts\activate
python -m src.web.scripts.init_admin
```

这将创建默认管理员账户：
- **用户名**: admin
- **密码**: admin123
- **角色**: 管理员

**重要提示**：首次登录后请立即修改默认密码！

## 前端开发

### 创建Vue 3项目

在项目根目录执行：

```bash
# 创建Vue 3项目
npm create vite@latest web-ui -- --template vue

# 进入目录
cd web-ui

# 安装依赖
npm install

# 安装必要的包
npm install vue-router@4 pinia element-plus @element-plus/icons-vue axios
```

### 配置Element Plus

编辑 `web-ui/src/main.js`:

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
```

### 配置Axios

创建 `web-ui/src/utils/request.js`:

```javascript
import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 5000
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    ElMessage.error(error.response?.data?.detail || '请求失败')
    return Promise.reject(error)
  }
)

export default service
```

### 登录页面示例

创建 `web-ui/src/views/Login.vue`:

```vue
<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>Homalos量化交易系统</h2>
        </div>
      </template>
      
      <el-form :model="loginForm" :rules="rules" ref="loginFormRef">
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            @click="handleLogin"
            :loading="loading"
            style="width: 100%"
            size="large"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const router = useRouter()
const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = ref({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const formData = new FormData()
      formData.append('username', loginForm.value.username)
      formData.append('password', loginForm.value.password)
      
      const response = await request.post('/auth/login', formData)
      localStorage.setItem('token', response.access_token)
      ElMessage.success('登录成功')
      router.push('/')
    } catch (error) {
      console.error('登录失败:', error)
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  color: #303133;
}
</style>
```

## 启动前端开发服务器

```bash
cd web-ui
npm run dev
```

访问 http://localhost:5173

## 完整使用流程

### 第一步：初始化环境

1. **安装后端依赖**：
   ```bash
   .venv\Scripts\activate
   uv pip install fastapi uvicorn sqlalchemy aiosqlite python-jose passlib bcrypt email-validator
   ```

2. **安装前端依赖**（已在`web-ui`目录创建项目）：
   ```bash
   cd web-ui
   npm install
   cd ..
   ```

### 第二步：初始化管理员账户

```bash
init_admin.bat
```

或

```bash
.venv\Scripts\activate
python -m src.web.scripts.init_admin
```

### 第三步：启动后端服务

```bash
start_web.bat
```

后端服务将运行在 http://localhost:8000

### 第四步：启动前端服务

在新的终端窗口：

```bash
cd web-ui
npm run dev
```

前端服务将运行在 http://localhost:5173

### 第五步：访问系统

1. 浏览器访问：http://localhost:5173
2. 使用管理员账户登录：
   - 用户名：`admin`
   - 密码：`admin123`
3. 登录成功后将看到系统主界面

### 快速测试

也可以通过API文档直接测试后端接口：

1. 访问 http://localhost:8000/docs
2. 测试注册、登录接口
3. 使用返回的token进行认证

## 数据库

- **类型**: SQLite
- **位置**: `data/homalos_web.db`
- **管理工具**: DB Browser for SQLite

## 下一步开发

- [ ] 系统监控页面
- [ ] 策略管理页面
- [ ] 用户管理页面
- [ ] WebSocket实时数据
- [ ] 权限管理系统

## 常见问题

### 1. CORS错误

确保后端 `main.py` 中的CORS配置包含前端地址：

```python
allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

### 2. 数据库初始化失败

检查 `data/` 目录是否存在，如不存在则创建：

```bash
mkdir data
```

### 3. JWT Token过期

默认过期时间为24小时，可在 `src/web/core/security.py` 中修改：

```python
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时
```

## 安全建议

### 生产环境配置

1. 修改SECRET_KEY（`src/web/core/security.py`）
2. 启用HTTPS
3. 配置严格的CORS策略
4. 使用环境变量管理敏感信息
5. 启用API限流
6. 配置日志监控

## 技术栈

### 后端
- FastAPI 0.115+
- SQLAlchemy 2.0+
- SQLite + aiosqlite
- Python-JOSE (JWT)
- Passlib (密码加密)

### 前端
- Vue 3
- Vite
- Element Plus
- Vue Router 4
- Pinia
- Axios

## 联系方式

如有问题，请联系：donnymoving@gmail.com

