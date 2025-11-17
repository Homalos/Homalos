<div align="center">
  <a href="https://homalos.github.io" target="blank"><img alt="Homalos Logo" src="../assets/logo.svg"/></a>
</div>
<p>&nbsp;</p>

<p align="center">
  <font size="5px">✨ 基于Python的期货量化交易系统 ✨</font>
</p>

<p align="center">
  <a href="https://img.shields.io/github/license/Homalos/Homalos"><img alt="GitHub License" title="GitHub License"
src="https://img.shields.io/github/license/Homalos/Homalos"/></a>
  <a href="https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FHomalos%2FHomalos%2Frefs%2Fheads%2Fmain%2Fpyproject.toml"><img alt="Python Version from PEP 621 TOML" title="Python Version from PEP 621 TOML"
src="https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FHomalos%2FHomalos%2Frefs%2Fheads%2Fmain%2Fpyproject.toml"/></a>
  <a href="https://deepwiki.com/Homalos/Homalos"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
  <a href="https://qun.qq.com/universal-share/share?ac=1&authKey=dzGDk%2F%2Bpy%2FwpVyR%2BTrt9%2B5cxLZrEHL793cZlFWvOXuV5I8szMnOU4Wf3ylap7Ph0&busi_data=eyJncm91cENvZGUiOiI0NDYwNDI3NzciLCJ0b2tlbiI6IlFrM0ZhZmRLd0xIaFdsZE9FWjlPcHFwSWxBRFFLY2xZbFhaTUh4K2RldisvcXlBckZ4NVIrQzVTdDNKUFpCNi8iLCJ1aW4iOiI4MjEzMDAwNzkifQ%3D%3D&data=O1Bf7_yhnvrrLsJxc3g5-p-ga6TWx6EExnG0S1kDNJTyK4sV_Nd9m4p-bkG4rhj_5TdtS5lMjVZRBv4amHyvEA&svctype=4&tempid=h5_group_info"><img alt="Group#1" title="Group#1"
src="https://img.shields.io/badge/Group%231-Join-blue"/></a>
</p>

<p align="center">
  简体中文 |
  <a href="../README.md">English</a>
</p>

## 概述

此项目是 Homalos 的新进展分支项目，Homalos 是一个基于 Python 的事件驱动型期货交易平台，旨在实现单机部署，并最大限度地减少外部依赖。

- **当前状态**: 开发中

## 功能特性

- ✅ 事件驱动架构
- ✅ CTP-API（综合交易平台API）集成
- ✅ 实时行情数据处理
- ✅ K线数据生成（1m、3m、5m、15m、30m、60m）
- ✅ **Web管理界面**（FastAPI + Vue 3）
  - 用户认证（JWT）
  - 系统监控仪表盘
  - 策略详情管理
  - 任务调度器
  - 通知中心
  - 数据中心Web控制
  - 实时数据可视化

### ✨ 最新更新 (v0.0.8.20251117)

- 🎨 **Web界面增强**：
  - **持仓展示**：实时持仓概览，显示持仓量、盈亏和市值占比
  - **网关状态**：修复实时网关状态更新（行情/交易/结算/合约）
  - **统一卡片风格**：所有管理界面采用一致的圆角卡片设计
  - **券商管理**：移除冗余的连接状态，简化账户管理
  - **用户管理**：完整的系统用户CRUD操作和管理员面板
- 🔧 **Bug修复**：
  - 修复WebSocket字段名不匹配问题（`gateway_status` → `gateway`）
  - 修复持仓数据重复显示问题，添加去重逻辑
  - 移除中文合约名称映射（直接使用合约代码保持一致性）
- 🏗️ **架构改进**：
  - 账户WebSocket集成，实时推送持仓和账户数据
  - 持仓数据转换，计算市值占比
  - 增强交易账户store，支持持仓跟踪
- ✅ **功能验证**：
  - 仪表盘：实时显示持仓量、价格和盈亏
  - 控制台：网关状态指示器连接后正确更新
  - 券商管理：简洁的账户管理界面，无连接状态
  - 用户管理：完整的管理员功能，基于角色的访问控制

### 之前的更新 (v0.0.6.20251024)

- 🚀 **关键性能与稳定性修复**：
  - 修复 `on_bar` 回调未触发问题（`TradingCoreService` 中 payload 键名不匹配）
  - 修复 BarGenerator 订阅配置更新时的死锁问题
  - 修复由于 `subscription_manager` 同步锁导致的 FastAPI 阻塞问题
  - 修复多线程竞态条件导致的 ZeroMQ 消息格式异常
  - 为 HTTP 请求处理器实现非阻塞锁（trylock）机制
  - 为 ZeroMQ 发送操作添加线程安全锁，确保原子性
  - 优化日志输出：将高频 `[VOLUME_UPDATE]` 日志从 INFO 改为 DEBUG 级别
  - 系统现可无阻塞处理高频行情数据
- 🏗️ **架构改进**：
  - 采用 ZeroMQ PUB-SUB 模式进行策略 IPC（替代 `multiprocessing.Pipe`）
  - 线程安全的消息广播，支持原子发送操作
  - 改进策略隔离机制，增强错误处理
  - 提升 EventBus 在并发负载下的性能
  - 修复 BarGenerator 锁管理，使用正确的 `try-finally` 模式
- ✅ **稳定性验证**：
  - Web 前端：无超时错误，所有 HTTP 请求 < 100ms
  - 策略回调：通过 ZeroMQ 成功接收 tick 和 bar 数据
  - 消息格式：100% 正确（2部分消息，无损坏）
  - K线生成：正常工作，成交量计算准确
  - 系统性能：CPU < 5%，开销极小

## Web界面

Homalos 现已包含基于 FastAPI 和 Vue 3 构建的现代化 Web 管理界面。

### 快速开始

1. **初始化管理员账户**
   ```bash
   init_admin.bat
   ```
   默认凭据：`admin` / `admin123`

2. **启动所有服务**
   ```bash
   start_all_web.bat
   ```
   这将启动后端（端口 8000）和前端（端口 5173）

3. **访问 Web 界面**
   - 前端：http://localhost:5173
   - API 文档：http://localhost:8000/docs

### 技术栈

**后端：**

- FastAPI
- SQLAlchemy 2.0 + SQLite
- JWT 认证
- Argon2 密码哈希

**前端：**

- Vue 3 + Vite
- Element Plus UI
- Vue Router 4
- Pinia 状态管理
- Axios

### 文档

详细文档请参见 [Web系统使用指南](../docs/Web系统使用指南.md)。

### 策略管理

**⚠️ 重要：策略热重载功能已禁用**

出于安全考虑，生产环境下已禁用策略热重载功能。修改运行中的策略可能导致：

- 持仓状态丢失
- 订单状态丢失
- 交易逻辑中断

**安全的策略修改流程：**

1. 在策略管理面板中停止策略
2. 确认策略状态为"已停止"
3. 编辑策略代码（位于 `src/strategy/strategies/` 目录）
4. 保存文件（策略不会自动启动）
5. （可选）运行单元测试验证修改
6. 点击"启动"按钮运行修改后的策略

**为什么禁用热重载？**

- 当前系统缺少与 CTP Gateway 的持仓/订单同步机制
- 缺少订单回报到策略进程的路由机制
- 状态持久化不包含交易信息
- 存在重复下单或持仓不一致的风险

这遵循了行业最佳实践（vnpy、Zipline），代码变更需要明确重启。

## 安装

```bash
# 克隆仓库
git clone https://github.com/Homalos/Homalos.git
cd Homalos

# 安装 Python 依赖
.venv\Scripts\activate
uv pip install -r requirements.txt

# 安装前端依赖
cd web-ui
npm install
cd ..
```

## 许可证

MIT License
