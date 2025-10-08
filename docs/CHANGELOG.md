# Update History

## v0.1.0 (2025-10-08)

### 新增功能
- ✨ **Web管理界面**：基于FastAPI + Vue 3的现代化Web管理平台
  - 用户认证系统（JWT Token）
  - 管理员账户管理
  - 系统监控仪表盘
  - 策略管理界面
  - 系统设置面板

### 后端架构
- 🔐 **安全认证**
  - JWT (JSON Web Tokens) 身份验证
  - Argon2 密码哈希（替代bcrypt解决Windows兼容性）
  - OAuth2密码流
  
- 💾 **数据库**
  - SQLAlchemy 2.0 ORM
  - SQLite异步支持(aiosqlite)
  - 用户模型和权限管理

- 🚀 **API服务**
  - FastAPI异步框架
  - RESTful API设计
  - 自动生成API文档（Swagger UI + ReDoc）
  - CORS跨域支持

### 前端架构
- 🎨 **UI框架**
  - Vue 3 Composition API
  - Element Plus组件库
  - 响应式布局设计
  
- 🔄 **状态管理**
  - Pinia状态管理
  - Vue Router 4路由守卫
  - Axios HTTP客户端

- 📱 **页面功能**
  - 登录/登出
  - 用户信息展示
  - 系统状态监控
  - 策略启停控制

### 工具脚本
- `init_admin.bat` - 初始化管理员账户
- `start_web.bat` - 启动Web后端服务
- `start_web_ui.bat` - 启动Vue前端服务
- `start_all.bat` - 一键启动所有服务
- `test_web_api.py` - API功能测试脚本

### 文档更新
- 📚 新增《Web系统使用指南》
- 📝 更新README添加Web系统说明
- 🔧 完善安装和部署文档

### Bug修复
- 🐛 修复非整点启动时60分钟K线数据缺失问题
- 🐛 修复ThreadPool.submit参数填充警告
- 🐛 修复TaskScheduler类型提示问题
- 🐛 解决bcrypt在Windows环境的兼容性问题

### 技术债务
- ⚡ 优化数据库连接管理
- 🔒 增强密码安全策略
- 📊 改进错误处理和日志记录

## v0.0.1.202509

### 初始版本
- 基础框架搭建
- CTP接口集成
- 事件驱动架构
