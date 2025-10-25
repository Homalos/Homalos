# Update History

## v0.0.7.20251026

### 🔴 重大变更（BREAKING CHANGES）

#### 移除策略热重载功能

**变更说明**：

- 完全移除 Watchdog 文件监控功能
- 移除 `reload_strategy()` 方法
- 移除相关 Web API 端点（`POST /{sid}/reload`、`GET /debug/reloading`、`POST /debug/clear-lock/{sid}`）
- 从依赖包中移除 `watchdog>=6.0.0`

**变更原因**：

经过深入的安全风险评估，运行中策略的热重载存在以下不可接受的风险：

1. **持仓状态丢失**：reload 时策略虚拟持仓重置，但实际持仓不变，可能导致重复开仓
2. **订单状态丢失**：已发送但未成交的订单在 reload 后无法感知，可能重复下单
3. **交易逻辑中断**：多步交易流程（如"先平后开"）被打断，策略意图无法完整执行
4. **缺少基础设施**：
   - 策略虚拟持仓与交易系统实际持仓不同步
   - 订单回报无法路由到新的策略进程
   - 状态持久化不包含交易信息（持仓、订单）
   - reload 后不从交易系统查询实际状态

**风险与收益对比**：

- 收益：节省 5-10 秒重启时间
- 风险：可能造成重大经济损失
- 结论：风险不可接受，收益微不足道

**影响范围**：

- 用户无法在策略运行时自动重载代码
- 需要使用"停止-修改-启动"流程修改策略

**迁移指南**：

**安全的策略修改流程：**
1. 在策略管理页面停止策略
2. 确认策略状态为"已停止"
3. 编辑策略代码（位于 `src/strategy/strategies/` 目录）
4. 保存文件（策略不会自动启动）
5. （可选）运行单元测试验证代码
6. 点击"启动"按钮运行修改后的策略

**行业最佳实践**：

专业量化交易平台（如 vnpy、Zipline）均不支持运行中策略的代码热更新：

- 代码变更需经过严格审查
- 策略修改通过参数配置而非代码变更
- 强调系统的稳定性和可预测性

**未来改进方向**：

如果将来需要恢复热重载，需要先实现：

1. 策略持仓与交易系统持仓的实时同步
2. 订单回报到策略进程的完整路由
3. 完整的状态持久化（包含持仓、订单）
4. reload 后的状态校验和恢复机制
5. 事务性 reload（支持回滚）

**参考文档**：

- `BUGFIX_策略热更新保持停止状态.md`
- `README.md` - Strategy Management 章节
- `README_CN.md` - 策略管理章节

---

### ✨ 改进

- **提升系统安全性**：消除状态不一致风险，避免可能的经济损失
- **简化代码结构**：移除约 200+ 行复杂的热重载逻辑
- **符合工程规范**：遵循专业量化交易系统的最佳实践
- **明确操作流程**：为用户提供清晰、安全的策略修改流程

---

## v0.0.6.20251024

### 🚀 关键性能与稳定性修复

#### on_bar回调未触发问题修复
- **问题**：策略无法接收K线数据，`on_bar`回调从未触发
- **根本原因**：事件payload键名不匹配
  - `BarGenerator`发布事件使用payload键名`"bar"`
  - `TradingCoreService`尝试获取payload键名`"data"`
  - 键名不匹配导致`bar_data`为`None`
  - ZeroMQ广播从未执行
- **数据流程**：
  ```
  BarGenerator → Event.bar(payload={"bar": kline})
  ↓ EventBus
  TradingCoreService._handle_bar_data()
  ↓ bar_data = event.payload.get("data")  # ← 错误！
  ↓ bar_data = None
  ↓ ZeroMQ广播 ← 从未执行 ❌
  ↓ 策略进程 ← 永远收不到bar ❌
  ```
- **解决方案**：
  - 修正`_handle_bar_data`方法中的键名：`"data"` → `"bar"`
  - 添加队列模式调试日志：`[DISTRIBUTE_BAR_QUEUE]`、`[CLEAN_KLINE_QUEUE]`
  - 优化高频日志级别：`[VOLUME_UPDATE]` INFO → DEBUG
- **效果**：
  - ✅ 策略成功接收bar数据
  - ✅ `on_bar`回调正常触发
  - ✅ 数据内容准确（价格、成交量）
  - ✅ 日志输出清晰简洁

#### BarGenerator死锁问题修复
- **问题**：K线配置更新时系统卡死，策略无法启动
- **根本原因**：死锁（Deadlock）
  - `register_strategy_subscription`持有`self._lock`
  - 内部调用`_publish_kline_config_update`
  - 再调用`get_kline_subscription_map`尝试再次获取`self._lock`
  - Python的`threading.Lock`不是可重入锁，导致死锁
- **调用链**：
  ```python
  register_strategy_subscription (持有 self._lock)
    └─> _publish_kline_config_update
         └─> get_kline_subscription_map (尝试获取 self._lock ❌)
  ```
- **解决方案**：
  - 创建内部版本`_get_kline_subscription_map_unlocked()`（不加锁）
  - 保留公开版本`get_kline_subscription_map()`（带锁）
  - `_publish_kline_config_update`调用内部版本，避免重复加锁
- **效果**：
  - ✅ K线配置更新流程正常
  - ✅ 策略订阅成功注册
  - ✅ BarGenerator成功接收配置

#### FastAPI阻塞问题修复
- **问题**：HTTP请求超时，前端频繁出现`timeout of 10000ms exceeded`错误
- **根本原因**：`subscription_manager.get_subscription_stats()`方法使用同步锁(`with self._lock:`)
  - 当订阅管理器正在处理订阅请求（持有锁）时，HTTP请求线程调用此方法会被阻塞
  - 如果锁被长时间持有，HTTP请求就会超时
- **解决方案**：
  - 使用非阻塞锁（`lock.acquire(blocking=False)`）
  - 无法获取锁时立即返回默认值，避免阻塞HTTP请求
  - 使用`try-finally`确保锁一定被释放
- **效果**：
  - ✅ 所有HTTP请求响应时间 < 100ms
  - ✅ 前端无任何超时错误
  - ✅ 系统高可用性显著提升

#### ZeroMQ竞态条件修复
- **问题**：策略进程大量警告`ZMQ 收到异常消息: 3 个部分，期望2个`
- **根本原因**：多线程竞态条件
  - EventBus有多个消费线程（general thread, market thread）
  - 两个线程同时调用`broadcast_market_data()`时，`send_string() + send()`操作被交叉执行
  - 导致消息格式错误：`["tick:SA601", "tick:FG601", <payload>]`（3部分）
- **技术分析**：
  ```python
  # Thread 1 处理 SA601
  send_string("tick:SA601", SNDMORE)  # ← 第1部分
  
  # Thread 2 插入执行，处理 FG601
  send_string("tick:FG601", SNDMORE)  # ← 第2部分
  
  # Thread 1 继续
  send(payload_SA601)                  # ← 第3部分
  ```
- **解决方案**：
  - 添加`_zmq_send_lock = threading.Lock()`
  - 使用`with self._zmq_send_lock:`确保发送操作原子性
  - 保证`send_string`和`send`作为一个整体执行
- **效果**：
  - ✅ ZeroMQ消息格式100%正确（2部分：topic + payload）
  - ✅ 策略成功接收tick/bar数据
  - ✅ 无任何消息格式警告

### 🏗️ 架构改进

#### ZeroMQ IPC方案
- **背景**：`multiprocessing.Pipe`在高频场景下存在阻塞问题
- **新方案**：ZeroMQ PUB-SUB模式
  - ✅ 高性能：百万级消息/秒
  - ✅ 非阻塞：异步消息传递
  - ✅ 一对多：支持多个策略进程同时订阅
  - ✅ 解耦：生产者和消费者完全独立
- **实现**：
  - Publisher：`StrategyManager`在`tcp://127.0.0.1:5555`发布市场数据
  - Subscriber：每个策略进程订阅自己关心的合约
  - 序列化：使用`pickle`序列化`TickData`和`BarData`对象
- **线程安全**：
  - ZeroMQ订阅线程与主线程隔离
  - 使用`logging`模块（线程安全）替代`multiprocessing.Pipe`
  - 添加发送锁确保消息完整性

### 📊 性能验证

#### 测试环境
- Windows 10 + Python 3.13
- simnow7x24 CTP环境
- 订阅合约：SA601, FG601
- Tick频率：~10次/秒

#### 测试结果
- ✅ **HTTP响应时间**：平均 < 50ms，最大 < 100ms
- ✅ **ZeroMQ消息延迟**：< 1ms
- ✅ **策略回调**：正常接收tick/bar数据
- ✅ **消息格式**：100%正确，无异常
- ✅ **CPU占用**：Web进程 < 5%，策略进程 < 2%
- ✅ **系统稳定性**：长时间运行无错误

### 🔧 修改文件

**核心修复**：
- ✅ `src/core/subscription_manager.py` - 非阻塞锁、死锁修复
- ✅ `src/core/strategy_manager.py` - ZeroMQ发送锁、ZeroMQ Publisher
- ✅ `src/core/strategy_worker.py` - ZeroMQ Subscriber、线程安全修复
- ✅ `src/web/services/trading_core_service.py` - 修复bar数据payload键名
- ✅ `src/api/bar_generator/bar_generator.py` - 添加调试日志、优化日志级别

**支持文件**：
- ✅ `src/web/services/strategy_service.py` - 核心依赖更新

**文档**：
- ✅ `BUGFIX_FastAPI阻塞和ZeroMQ竞态条件修复总结.md` - FastAPI和ZeroMQ修复文档
- ✅ `BUGFIX_on_bar回调未触发问题修复.md` - on_bar回调修复文档

### 🎯 技术亮点

#### 1. 非阻塞锁模式
使用`trylock`模式，在无法获取锁时立即返回默认值，而不是阻塞等待。这是高可用系统的常用模式。

#### 2. 原子操作保证
通过锁确保ZeroMQ的多步发送操作作为一个整体执行，避免竞态条件。

#### 3. 线程安全设计
- 识别到ZeroMQ Publisher在多线程环境下的竞态风险
- 使用最小粒度的锁，只保护临界区
- 避免死锁（锁的持有时间极短，无嵌套锁）

#### 4. IPC架构升级
从`multiprocessing.Pipe`（同步、阻塞、单对单）升级到ZeroMQ（异步、非阻塞、一对多），为系统扩展打下基础。

---

## v0.0.5.20251022

### ✨ 核心架构优化

#### Event.py 代码重构
- **优化目标**：提升代码质量和可维护性
- **重构内容**：
  - 将10个模块级便捷函数转换为 `Event` 类方法
  - 使用 Python 3.10+ 联合类型语法（`|` 代替 `Optional`）
  - 新增 `Event.create()` 通用类方法
  - 简化 `subscription()` 方法的条件逻辑
- **API变更**（破坏性更改）：
  - 旧方式：`create_tick_event(payload, source)`
  - 新方式：`Event.tick(payload, source)`
- **代码统计**：
  - 删除 153 行重复代码
  - 新增 155 行类方法（含完整文档）
  - 代码结构更清晰，符合面向对象设计原则
- **优势**：
  - ✅ 更好的封装性（事件创建属于Event类）
  - ✅ 更简洁的API（`Event.tick()` vs `create_tick_event()`）
  - ✅ 完整的类型提示支持
  - ✅ 减少命名空间污染

#### EventBus 内置定时器机制
- **功能**：支持秒级定时任务，用于定期查询账户和持仓
- **实现**：
  - 新增 `timer_enabled` 参数（默认 `True`）
  - 新增 `_timer_thread` 定时器线程
  - 新增 `_timer_loop()` 方法，定期发布 `EventType.TIMER` 事件
  - 定时器间隔可配置（`interval` 参数，默认1秒）
- **特性**：
  - ⏱️ 秒级精度，支持任意间隔
  - 🔄 自动发布 TIMER 事件到 general 队列（优先级不高）
  - 🛡️ 线程安全的启动和停止机制
  - 📝 完整的异常处理和日志记录
  - 🔌 守护线程模式，主线程退出时自动结束
- **使用示例**：
  ```python
  # 每5秒发布一次TIMER事件
  event_bus = EventBus(interval=5, timer_enabled=True)
  
  # 订阅TIMER事件
  event_bus.subscribe(EventType.TIMER, timer_handler)
  ```
- **应用场景**：
  - 定期查询账户资金（如每5秒）
  - 定期查询持仓信息
  - 心跳保活机制
  - 定时数据同步

### 🐛 Bug修复

#### 修复 TraderGateway 定时器事件处理
- **问题**：`process_timer_event()` 方法签名不匹配
  - 错误信息：`TypeError: TraderGateway.process_timer_event() takes 1 positional argument but 2 were given`
- **原因**：EventBus 调用订阅者时会传递 `Event` 对象，但方法未接收此参数
- **解决**：
  - 修改方法签名：`def process_timer_event(self) -> None:` → `def process_timer_event(self, event: Event) -> None:`
  - 保持方法内部逻辑不变
- **效果**：
  - ✅ 定时器事件正常接收和处理
  - ✅ 每10秒轮流查询账户和持仓（2次TIMER事件触发一次查询）

#### 增加账户查询日志输出
- **问题**：账户查询成功但无日志输出，难以追踪
- **原因**：`onRspQryTradingAccount()` 回调中缺少日志记录
- **解决**：
  - 在账户查询回调中添加日志输出
  - 与持仓查询日志格式保持一致
  - 记录"查询资金账户成功"和账户详细数据
- **效果**：
  - ✅ 账户查询和持仓查询都有清晰的日志输出
  - ✅ 便于监控定时查询是否正常执行
  - ✅ 便于排查账户数据问题

### 📝 修改文件

**核心模块**：
- ✅ `src/core/event.py` - Event类重构，便捷函数转类方法
- ✅ `src/core/event_bus.py` - 新增内置定时器机制

**网关模块**：
- ✅ `src/modules/gateway/trader_gateway.py` - 修复定时器事件处理，添加账户查询日志

### 🔧 技术改进

- 🏗️ **架构优化**：面向对象设计，类方法替代模块函数
- 📦 **代码质量**：Python 3.10+ 类型提示，减少重复代码
- ⏱️ **定时任务**：EventBus 内置定时器，无需外部依赖
- 📊 **可观测性**：完善的日志输出，便于监控和调试

### 🎯 用户体验提升

- 🔄 **开箱即用**：定时器功能默认启用，自动查询账户和持仓
- 📝 **清晰日志**：所有查询操作都有日志记录
- ⚙️ **灵活配置**：定时器间隔可自定义，可独立开关
- 🛡️ **稳定可靠**：完善的异常处理，不影响主流程

---

## v0.0.4.20251013-patch14

### 🐛 Bug修复

#### 修复资金账户密码错误时误跳转问题
- **问题**：资金账户登录密码错误时，直接跳转到系统登录界面
- **原因**：响应拦截器将所有401错误都当作系统认证失效处理
- **解决**：
  - 修改响应拦截器，区分资金账户API和系统认证API的401错误
  - 资金账户API的401错误只显示提示，不跳转页面
  - 系统认证API的401错误保持原有跳转逻辑
- **效果**：
  - 资金账户密码错误时显示准确提示："密码错误或账户无权限"
  - 用户可以在对话框中重新输入密码
  - 不影响系统登录状态和用户会话

#### 修改文件
- ✅ `web-ui/src/api/request.js` - 优化401错误处理逻辑

---

## v0.0.4.20251013-patch13

### ✨ 添加资金账户界面优化

#### 功能改进
1. **券商选择优化**
   - 移除下拉选项中的`9999`等broker_id显示
   - 更新券商配置：`real` → `guofu`（国富期货-主席），新增`everbright`（光大期货-主席）
   - 修改TTS券商的broker_id：`tts`使用`0001`，`tts7x24`使用`0002`

2. **字段标签优化**
   - "资金账号" → "资金账户"
   - "账户密码" → "交易密码"
   - 占位符文本相应更新

3. **新增可选字段**
   - 添加"应用ID"输入框（可选）
   - 添加"授权码"输入框（可选）
   - 支持留空使用默认值

#### 技术实现
1. **后端数据模型**
   - `TradingAccount`模型添加`app_id`、`auth_code`字段
   - 更新相关Schema支持新字段
   - 数据库迁移添加新字段

2. **业务逻辑优化**
   - `TradingAuthService`支持`app_id`、`auth_code`参数
   - 未提供时自动从`BrokerService`获取默认值
   - API接口支持新字段传递

3. **前端界面更新**
   - `TradingAccountLogin.vue`添加新字段输入
   - `FirstTimeGuide.vue`同步更新
   - 表单数据和提交逻辑完整支持

#### 修改文件
- `config/brokers.yaml`
- `src/web/models/trading_account.py`
- `src/web/schemas/trading_account.py`
- `src/web/services/trading_auth_service.py`
- `src/web/services/broker_service.py`
- `src/web/api/trading_account.py`
- `src/web/migrations/add_app_id_auth_code_to_trading_accounts.py`
- `web-ui/src/components/TradingAccountLogin.vue`
- `web-ui/src/components/FirstTimeGuide.vue`

#### 用户体验提升
- 🎯 界面更加清晰直观
- 🔧 支持更灵活的账户配置
- 📝 字段标签更加准确
- ✨ 可选字段提供更多自定义选项

---

## v0.0.4.20251013-patch12

### 🐛 Bug修复 & ✨ 功能增强

#### 修复账户总览显示格式和数据结构优化
- **问题**：账户总览显示格式错误
  - **修复前**：`账户总览 - simnow7x24_789456 (simnow7x24 - **9456)`
  - **修复后**：`账户总览 - simnow7x24_9999 (**9456)`
- **根源**：
  - broker_key 和 broker_id 混淆，前端存储错误
  - display_name 生成格式错误（使用了broker_key_account_id，应为broker_key_broker_id）
  - Dashboard 显示格式冗余（重复显示了broker信息）
- **解决方案**：
  - 数据模型新增 `broker_key` 字段（账户类型标识）
  - 明确区分 `broker_key`（如 simnow7x24）和 `broker_id`（如 9999）
  - `display_name` 格式改为 `${broker_key}_${broker_id}`
  - Dashboard 显示格式简化为 `账户总览 - ${accountName} (${maskedAccount})`
  - 后端登录时自动从 BrokerService 查询 broker_id
- **字段说明**：
  - `broker_key`：券商配置标识（如 simnow7x24），用于识别账户类型和连接配置
  - `broker_id`：实际券商ID（如 9999），CTP标准券商代码
  - `account_id`：资金账号（如 789456）
  - `display_name`：UI显示名称，格式为 `${broker_key}_${broker_id}`（如 simnow7x24_9999）
- **改进**：
  - 数据结构更清晰，字段语义明确
  - 显示格式更简洁，信息更准确
  - 账户管理界面新增"账户类型"列
  - 切换对话框显示简化（只显示账户名和加密账号）

#### 修改文件

**后端**：
- ✅ `src/web/models/trading_account.py` - 添加 broker_key 字段
- ✅ `src/web/schemas/trading_account.py` - 更新 Schema 定义
- ✅ `src/web/services/trading_auth_service.py` - 更新服务逻辑，支持从BrokerService查询broker_id
- ✅ `src/web/api/trading_account.py` - 更新 API 路由
- ✅ `src/web/migrations/add_broker_key_to_trading_accounts.py` - 数据库迁移

**前端**：
- ✅ `web-ui/src/components/TradingAccountLogin.vue` - 修改提交逻辑（broker_id → broker_key）
- ✅ `web-ui/src/components/FirstTimeGuide.vue` - 修改提交逻辑（broker_id → broker_key）
- ✅ `web-ui/src/components/AccountManager.vue` - 添加账户类型列，简化切换对话框
- ✅ `web-ui/src/components/Dashboard.vue` - 简化显示格式

---

## v0.0.4.20251013-patch11

### 🐛 Bug修复

#### 修复切换按钮显示和账号加密问题
- **问题1**：切换到的资金账户在"管理资金账户"列表中仍显示"切换"按钮
  - **根源**：accountId类型不一致（有时是字符串，有时是数字）
  - **影响**：登录后立即打开管理界面，当前账户仍显示"切换"按钮
  - **修复**：统一accountId为字符串类型，确保类型一致性
- **问题2**：仪表盘账户总览可能暴露完整账号信息（不安全）
  - **根源**：account_id可能是数字类型，导致加密函数失效
  - **影响**：显示完整账号而非加密格式（如显示160219而非**0219）
  - **修复**：增强maskAccountId函数，确保接收任何类型都能正确转换并加密
- **改进**：
  - 统一所有地方的accountId为字符串类型
  - 增强类型转换的健壮性（防御性编程）
  - 简化比较逻辑，使用String()进行类型统一

#### 修改文件
- ✅ `web-ui/src/stores/tradingAccount.js` - 统一accountId类型为字符串
- ✅ `web-ui/src/components/AccountManager.vue` - 简化比较逻辑
- ✅ `web-ui/src/components/Dashboard.vue` - 增强加密函数健壮性

---

## v0.0.4.20251013-patch10

### ✨ 功能增强

#### 管理资金账户添加切换功能
- **新增**：在"管理资金账户"界面添加"切换"按钮
- **功能**：允许用户快速切换到其他资金账户
- **安全性**：切换时需要验证账户密码
- **显示逻辑**：
  - 当前登录的账户：不显示"切换"按钮
  - 其他已激活账户：显示"切换"按钮
  - 禁用的账户：不显示"切换"按钮
- **操作流程**：
  1. 点击"切换"按钮
  2. 弹出密码验证对话框，显示账户信息（名称 + 券商ID + 加密账号）
  3. 输入账户密码并确认
  4. 验证成功后切换到新账户
  5. 仪表盘账户总览自动更新显示新账户信息
- **用户体验**：
  - 密码错误时不关闭对话框，可重新输入
  - 切换成功后显示成功提示（含账户名称）
  - 支持回车键快速确认
  - 操作列宽度调整为320px以容纳新按钮
- **联动更新**：切换后仪表盘的账户总览自动显示新账户信息（响应式更新）

#### 修改文件
- ✅ `web-ui/src/components/AccountManager.vue` - 添加切换功能

---

## v0.0.4.20251013-patch9

### ✨ 功能增强

#### 账户总览显示券商ID和加密账号
- **新增**：账户总览标题中显示券商ID和加密的资金账号
- **格式**：`账户总览 - {账户名称} ({券商ID} - {加密账号})`
- **加密规则**：
  - 只显示资金账号后4位
  - 前面的位数全部用 `*` 替代
  - 账号长度≤4位时全部显示
- **示例**：
  - `123456789` → `*****6789`（9位账号）
  - `160219` → `**0219`（6位账号）
  - `1234` → `1234`（4位账号）
- **安全性**：符合敏感信息显示的行业惯例，防止信息泄漏
- **显示效果**：`账户总览 - SimNow日盘 (9999 - **0219)`

#### 修改文件
- ✅ `web-ui/src/components/Dashboard.vue` - 添加券商ID和加密账号显示

---

## v0.0.4.20251013-patch8

### ✨ 功能增强

#### 仪表盘账户总览显示资金账户名称
- **新增**：账户总览卡片标题中显示当前登录的资金账户名称
- **格式**：`账户总览 - {账户名称}`
- **逻辑**：
  - 未登录资金账户：仅显示"账户总览"
  - 已登录资金账户：显示"账户总览 - {账户名称}"
  - 多个账户时：显示当前登录账户名称（通常是默认账户）
- **效果**：用户可以清楚知道当前查看的是哪个账户的数据

#### 修改文件
- ✅ `web-ui/src/components/Dashboard.vue` - 添加账户名称显示

---

## v0.0.4.20251013-patch7

### ✨ 功能增强

#### 关于面板新增用户手册信息
- **新增**：在关于面板的"时区"下方新增"用户手册"字段
- **来源**：从 `config/system.yaml` 的 `user_guide` 配置读取
- **显示**：使用带图标的链接，点击跳转到快速开始文档
- **链接**：https://homalos.github.io/guide/quick_start
- **位置**：关于面板 → 时区下方

#### 修改文件
- ✅ `src/web/schemas/system_config.py` - 添加user_guide字段到SystemInfoResponse
- ✅ `src/web/services/system_config_service.py` - 读取user_guide配置
- ✅ `web-ui/src/components/About.vue` - 显示用户手册链接

#### 配置文件
- ✅ `config/system.yaml` - 已包含user_guide配置

---

## v0.0.4.20251013-patch6

### ✨ 优化

#### 更新引导界面文档链接
- **更新**：将首次使用引导界面的"查看使用文档"链接更新为官方文档地址
- **链接**：https://homalos.github.io/guide/quick_start
- **位置**：引导界面第三步"设置完成"页面

#### 修改文件
- ✅ `web-ui/src/components/FirstTimeGuide.vue` - 更新文档链接

---

## v0.0.4.20251013-patch5

### 🐛 Bug修复

#### 修复新注册用户首次引导不显示问题
- **问题**：新注册用户登录后，没有显示首次使用引导界面
- **原因**：localStorage中的 `homalos_guide_completed` 标记全局共享，新用户注册时未清除
- **解决**：注册成功后自动清除引导完成标记
- **效果**：新用户登录后正常显示引导界面

#### 优化
- **调试日志**：在首次使用检测中添加控制台日志，方便排查问题

#### 修改文件
- ✅ `web-ui/src/views/Login.vue` - 注册成功后清除引导标记
- ✅ `web-ui/src/views/Home.vue` - 添加首次使用检测日志

#### 测试验证
```bash
✅ 新用户注册后引导正常显示
✅ 旧用户登录不受影响
✅ 前端Lint检查：0错误
```

---

## v0.0.4.20251013-patch4

### ✨ 功能增强

#### 登录界面增加注册功能
- **功能**：在登录界面添加用户注册功能，支持注册管理员角色账号
- **实现**：
  - 使用Tab切换实现登录/注册界面切换
  - 注册表单包含：用户名、密码、确认密码、邮箱（可选）、全名（可选）
  - 默认注册管理员角色（admin）
  - 完善的表单验证规则
  - 注册成功后自动切换到登录Tab并填充用户名
- **验证规则**：
  - ✅ 用户名：3-50字符，必填，唯一性验证
  - ✅ 密码：6-50字符，必填
  - ✅ 确认密码：必须与密码一致
  - ✅ 邮箱：格式验证（可选），唯一性验证
  - ✅ 全名：可选
- **用户体验**：
  - 动态标题显示（登录/注册）
  - 注册成功后自动切换到登录Tab
  - 自动填充用户名到登录表单
  - 清晰的成功/失败提示
  - 美观的UI设计

#### 修改文件
- ✅ `src/web/schemas/user.py` - 添加role字段到UserCreate
- ✅ `src/web/services/auth_service.py` - 使用传入的role创建用户
- ✅ `web-ui/src/stores/user.js` - 添加register方法
- ✅ `web-ui/src/views/Login.vue` - 添加注册界面和逻辑

#### 测试验证
```bash
✅ 前端Lint检查：0错误
✅ 后端Lint检查：0错误
✅ 代码风格：符合规范
```

---

## v0.0.4.20251013-patch3

### 🐛 Bug修复

#### 账户列表刷新问题修复
- **问题**：登录成功后，"管理资金账户"列表不显示新添加的账户
- **原因**：登录成功后未刷新账户列表缓存
- **解决**：在 `tradingAccountStore.login()` 方法中添加 `await fetchAccountList()` 调用
- **效果**：登录后立即刷新账户列表，新账户实时显示

### ✨ 功能增强

#### 增加修改密码功能
- **功能**：在"管理资金账户"中为每个账户添加"修改密码"操作
- **实现**：
  - 添加"修改密码"按钮（操作列）
  - 创建修改密码对话框
  - 实现密码修改逻辑
  - 完善表单验证规则
- **验证规则**：
  - ✅ 旧密码必填
  - ✅ 新密码至少6位
  - ✅ 新密码不能与旧密码相同
  - ✅ 两次输入密码必须一致
- **用户体验**：
  - 显示账户信息（名称、券商ID、账号）
  - 密码输入框支持显示/隐藏
  - 支持回车键快速提交
  - 清晰的错误提示

#### 修改文件
- ✅ `web-ui/src/stores/tradingAccount.js` - 添加账户列表刷新
- ✅ `web-ui/src/components/AccountManager.vue` - 添加修改密码功能

#### 测试验证
```bash
✅ 账户列表刷新：登录后列表实时更新
✅ 修改密码功能：表单验证正确，API调用成功
✅ 前端Lint检查：0错误
```

---

## v0.0.4.20251013-patch2

### ✨ 功能增强

#### 自动创建账户功能
- **功能**：使用"输入新账户"方式登录时，如果账户不存在，自动创建并登录
- **使用场景**：
  - 首次添加新的资金账户
  - 快速添加模拟账户进行测试
  - 无需先到"账户管理"添加，直接登录即可
- **实现**：
  - 修改 `TradingAuthService.login()` 方法
  - 检测到账户不存在时自动调用 `add_account()`
  - 创建成功后继续执行登录流程
- **安全性**：
  - 处理并发创建相同账户的情况
  - 仅在"输入新账户"模式下自动创建
  - "使用已有账户"模式下保持原有错误提示

#### 修改文件
- ✅ `src/web/services/trading_auth_service.py` - 增加自动创建逻辑
- ✅ `src/web/api/trading_account.py` - 更新API文档
- ✅ `docs/两步登录功能说明.md` - 新增功能说明

#### 用户体验改进
**修复前**：
- ❌ "输入新账户"登录提示"账户不存在"
- ❌ 需要先去"账户管理"添加账户
- ❌ 需要两步操作才能完成

**修复后**：
- ✅ 自动创建账户并登录成功
- ✅ 一步完成添加和登录
- ✅ 显示名称自动生成（可后续修改）

---

## v0.0.4.20251013-patch1

### 🐛 Bug修复

#### 券商选择问题修复
- **问题**：首次使用引导和资金账户登录对话框中，开户机构选择框只显示"实盘账户"一个选项
- **原因**：所有券商的 `broker_id` 都是 "9999"，导致选择框选项重复
- **解决**：
  - 后端新增 `broker_key` 字段（simnow、tts等）作为唯一标识符
  - 前端使用 `broker_key` 作为选项值
  - 选择框右侧显示 `broker_id` 作为辅助信息
- **效果**：用户现在可以看到并选择所有5种券商账户类型
  - SimNow模拟（日盘）
  - SimNow模拟（7x24）
  - TTS模拟（日盘）
  - TTS模拟（7x24）
  - 实盘账户

#### 修改文件
- ✅ `src/web/services/broker_service.py` - 新增 broker_key 返回
- ✅ `src/web/schemas/trading_account.py` - BrokerInfo Schema更新
- ✅ `web-ui/src/components/FirstTimeGuide.vue` - 使用 broker_key
- ✅ `web-ui/src/components/TradingAccountLogin.vue` - 使用 broker_key

#### 测试验证
```bash
✅ 后端：券商列表加载成功（5个券商，每个都有唯一的 broker_key）
✅ 前端：Lint检查通过（0错误）
✅ 功能：选择框正常显示所有券商选项
```

### 📚 文档更新
- 📝 新增《券商选择问题修复说明.md》 - 详细修复文档

---

## v0.0.4.20251013

### 🔐 两步登录系统（安全性重大提升）

#### 核心功能
- ✨ **两步登录机制**：系统账号登录 + 资金账户登录
  - 第一步：系统账号登录（Web用户认证）
  - 第二步：资金账户登录（交易权限认证）
- 🎫 **精细权限控制**：
  - 仅系统登录：可访问"关于"和"系统设置"，其他页面显示权限蒙层
  - 资金账户登录：解除所有限制，可进行交易操作
- 🔄 **账户管理**：
  - 一个Web用户可绑定多个资金账户（1:N）
  - 支持设置默认账户
  - 快速切换账户
- 🔒 **安全机制**：
  - argon2 密码加密
  - 登录失败次数限制（5次）
  - 自动锁定机制（15分钟）
  - Token包含资金账户信息
- 🚪 **退出登录**：
  - 退出资金账户（保持系统登录）
  - 退出系统登录（同时退出资金账户）

#### 数据库设计
- 📊 **trading_accounts表**：
  - user_id（Web用户ID，外键）
  - broker_id（券商ID）
  - account_id（资金账号）
  - encrypted_password（加密密码）
  - display_name（显示名称）
  - is_active（是否激活）
  - is_default（是否默认）
  - failed_attempts（登录失败次数）
  - locked_until（锁定到期时间）
  - last_login（最后登录时间）
- 🔗 **关系模型**：User.trading_accounts (1:N)
- 🔐 **密码加密**：argon2算法，安全存储

#### API接口
- 🌐 **资金账户API**（`/api/trading-account/`）：
  - `POST /login` - 资金账户登录
  - `POST /logout` - 资金账户登出
  - `GET /status` - 获取登录状态
  - `GET /list` - 获取账户列表
  - `POST /` - 添加资金账户
  - `PUT /{id}` - 更新账户信息
  - `DELETE /{id}` - 删除账户
  - `POST /{id}/switch` - 切换默认账户
  - `PUT /{id}/password` - 修改密码
  - `GET /brokers` - 获取券商列表（从`config/brokers.yaml`读取）

#### 前端组件
- 🖥️ **4个新组件**：
  - `TradingAccountLogin.vue` - 资金账户登录对话框
  - `PageMask.vue` - 权限蒙层组件
  - `AccountManager.vue` - 账户管理对话框
  - `FirstTimeGuide.vue` - 首次使用引导
- 🎨 **用户体验优化**：
  - 半透明蒙层，内容可见但不可交互
  - 动态显示资金账户状态
  - 首次使用引导流程
  - 优雅的登录/退出确认对话框

#### 状态管理
- 📦 **tradingAccountStore**（Pinia）：
  - accountId - 当前登录的账户ID
  - isLoggedIn - 是否已登录
  - accountInfo - 当前账户信息
  - accountList - 账户列表
  - login() - 登录方法
  - logout() - 登出方法
  - fetchStatus() - 获取状态
  - fetchAccountList() - 获取列表
  - initialize() - 初始化
- 💾 **持久化存储**：localStorage保存登录状态

#### 路由守卫
- 🛡️ **增强路由守卫**（`web-ui/src/router/index.js`）：
  - 系统登录检查
  - 资金账户Store初始化
  - 自动重定向逻辑

#### Home.vue改造
- 🔄 **顶部导航栏**：
  - 添加"登录资金账户"按钮（未登录时显示）
  - 用户下拉菜单显示资金账户状态
  - "管理资金账户"、"退出资金账户"、"退出系统登录"选项
- 🔐 **权限蒙层**：
  - 仪表盘、控制台、策略管理、通知中心、任务调度器显示蒙层（未登录资金账户时）
  - 系统设置、关于页面无限制
- 🎯 **默认页面**：
  - 未登录资金账户：显示"关于"页面
  - 已登录资金账户：自动切换到"仪表盘"

#### 后端服务
- 🔧 **TradingAuthService**（`src/web/services/trading_auth_service.py`）：
  - 资金账户登录认证
  - 密码验证
  - 失败次数统计和锁定
  - 账户CRUD操作
  - 密码修改
- 🏦 **BrokerService**（`src/web/services/broker_service.py`）：
  - 从`config/brokers.yaml`读取券商配置
  - 返回可用券商列表

#### 配置文件
- 📄 **brokers.yaml**（`config/brokers.yaml`）：
  - simnow - SimNow模拟（日盘）
  - simnow7x24 - SimNow模拟（7x24）
  - tts - TTS模拟（日盘）
  - tts7x24 - TTS模拟（7x24）
  - real - 实盘账户

#### 安全特性
- 🔐 **密码加密**：argon2算法（OWASP推荐）
- 🚫 **登录限制**：5次失败自动锁定15分钟
- 🎫 **Token增强**：包含资金账户信息
- 📝 **审计日志**：记录所有登录/登出操作
- 🔄 **状态持久化**：页面刷新保持登录状态

### 📚 文档更新

- 📝 新增《两步登录功能说明.md》 - 详细功能文档（57KB）
  - 登录流程说明
  - 核心特性介绍
  - 页面权限控制
  - 首次使用引导
  - 账户管理
  - API接口文档
  - 数据库表结构
  - 安全建议
  - 常见问题
  - 未来计划

### 🔧 技术实现

- 🏗️ **后端技术栈**：
  - FastAPI + SQLAlchemy
  - argon2 密码加密
  - JWT Token + 资金账户信息
  - 异步数据库操作
- 🎨 **前端技术栈**：
  - Vue 3 + Composition API
  - Pinia 状态管理
  - Element Plus 组件库
  - 路由守卫 + 组件权限控制
  - localStorage 持久化

### 📊 代码统计

- ✨ **新增文件**：
  - 后端：6个文件（models, schemas, services, api, migrations）
  - 前端：5个文件（components, store, api）
  - 配置：1个文件（brokers.yaml）
  - 文档：1个文件（两步登录功能说明.md）
- 📝 **代码行数**：
  - 后端代码：~1200行
  - 前端代码：~800行
  - 文档：~550行

---

## v0.0.3.20251012

### 🎨 前端组件化重构（可维护性重大提升）

#### 核心优化
- ✨ **组件完全独立化**：将 `Home.vue`（945行）拆分为7个独立组件
  - `Dashboard.vue` - 仪表盘（290行）
  - `Console.vue` - 控制台（302行）
  - `StrategyManagement.vue` - 策略管理（677行）
  - `TaskScheduler.vue` - 任务调度器
  - `Notifications.vue` - 通知中心（145行）
  - `Settings.vue` - 系统设置（283行）
  - `About.vue` - 关于页面（102行）
- 🏗️ **Home.vue瘦身92%**：从945行优化至280行，仅保留布局和路由功能
- ♻️ **代码复用性提升**：每个组件职责单一，易于维护和复用
- 📦 **样式隔离**：所有组件使用 `<style scoped>`，避免样式冲突

#### 系统设置增强
- 🔧 **开发模式配置**：将"自动启动"改为"开发模式"，更符合实际用途
- ⏰ **交易时间检查**：新增"交易时间检查"选项，仅在开发模式启用时显示
  - 开启：检查是否在交易时间内
  - 关闭：跳过交易时间检查（方便开发调试）
- 💾 **配置文件同步**：系统设置与 `config/system.yaml` 双向同步
  - 页面加载时从配置文件读取
  - 修改后自动保存到配置文件
  - 自动生成备份文件（.yaml.bak）

#### 配置管理系统
- 📡 **系统配置API**：
  - `GET /api/system-config` - 获取系统配置（dev_mode, dev_trading_hours_check）
  - `PUT /api/system-config` - 更新系统配置
  - `GET /api/system-config/info` - 获取系统基础信息（公开访问）
- 🔐 **审计日志**：记录所有配置修改操作（用户、时间、修改内容）
- 💾 **自动备份**：每次修改前自动备份配置文件
- 🔄 **热加载支持**：利用 ConfigManager 的文件监听功能

#### 关于页面动态化
- 📄 **配置驱动显示**：从 `config/system.yaml` 动态加载系统信息
  - 系统名称、版本、作者、版权信息
  - 系统描述、技术栈、时区、联系方式
- 🚫 **消除硬编码**：所有系统信息统一在配置文件管理
- 🔄 **即时更新**：修改配置文件后刷新页面即可看到更新
- 📱 **公开访问**：系统信息接口无需登录认证

### 🐛 Bug修复

- 🐛 **修复系统配置保存失败问题**
  - 原因：通知配置验证在系统配置保存之前，验证失败导致提前返回
  - 解决：调整保存逻辑顺序，系统配置优先保存，通知配置独立验证
  - 效果：即使通知配置未填写，系统配置也能正常保存
- 🐛 **修复配置文件未更新问题**
  - 原因：前端验证逻辑阻止了API调用
  - 解决：分离系统配置和通知配置的保存流程
  - 效果：Network中可以看到API请求，配置文件正常更新

### 📚 文档更新

- 📝 新增《Home.vue 重构优化方案.md》 - 组件提取详细规划
- 📖 新增《系统配置同步功能测试指南.md》 - 配置同步测试流程
- 📋 新增《前端配置更新排查指南.md》 - 问题排查步骤
- 🔧 新增《系统配置保存功能修复说明.md》 - Bug修复详解
- 📄 新增《关于页面动态加载实现说明.md》 - 动态加载实现文档
- 🧪 新增 `tests/test_system_config_api.py` - 系统配置API自动化测试

### 🔧 技术改进

- 🏗️ **架构优化**：组件化、模块化、配置化
- 📦 **代码质量**：单一职责、高内聚低耦合
- 🔄 **用户体验**：分步提示、优雅降级、智能验证
- 📊 **可维护性**：文档完善、测试覆盖、清晰注释

---

## v0.0.2.20251010

### 🚀 SSE实时日志流（性能重大提升）

#### 核心功能
- ✨ **Server-Sent Events实时推送**：采用SSE技术替代轮询，实现日志实时推送
- 💾 **内存缓冲机制**：LogBuffer缓存最新500条日志，零磁盘I/O
- 🔄 **智能降级策略**：SSE不可用时自动降级到轮询模式
- 🔌 **自动重连**：浏览器原生支持，连接断开自动重连
- 💓 **心跳保活**：每30秒发送心跳，防止连接超时

#### 性能提升
- ⚡ **CPU使用率降低90%**：从2-5%降至<1%
- 📁 **零磁盘I/O**：日志直接从内存推送，完全消除文件读取
- ⏱️ **延迟降低99%**：从5秒降至<50ms
- 📊 **带宽节省70%**：无效轮询请求完全消除

#### 技术架构
- 🏗️ **LogBuffer**：线程安全的日志缓冲管理器（`src/web/services/log_buffer.py`）
  - 支持多客户端订阅（最多10个）
  - 使用deque实现高效队列
  - 提供统计信息API
- 🔌 **自定义Sink**：`sse_log_sink`拦截Loguru日志并推送到缓冲区
- 📡 **SSE端点**：`/api/datacenter/logs/stream`实现实时日志流
- 🌐 **前端EventSource**：浏览器原生API接收实时日志

#### API端点
- `GET /api/datacenter/logs/stream` - SSE实时日志流
- `GET /api/datacenter/logs` - 兼容模式（优先内存，回退文件）
- `GET /api/datacenter/logs/stats` - 获取日志缓冲统计

#### 配置
- 🔧 **环境变量**：`ENABLE_SSE_LOGS=true`（默认启用）
- 📝 **启动脚本**：`start_web.py`和`start_web.bat`已自动配置
- ⚙️ **可配置项**：缓冲区大小、订阅者数量、心跳间隔

#### 文档
- 📚 新增《SSE日志流使用指南.md》详细说明使用方法和故障排查

---

## v0.0.1.20251010

### 🎨 Web界面重大优化

#### 策略管理增强
- ✨ **策略详情面板**：抽屉式侧边栏展示完整策略信息
  - 基础信息：策略名称、描述、作者、创建/修改时间
  - 持仓信息：合约代码、持仓量、方向、成本价、最新价、委托状态、浮动盈亏等
  - 风险控制参数配置：最大仓位、止损/止盈比例、最大回撤（可编辑）
  - 风险控制展示：只读显示当前风险控制指标
- ✨ **添加策略功能**：支持从5个预定义策略模板中选择添加新策略
- ✨ **策略日志**：实时显示策略操作日志（添加、启动、停止、删除、持仓变动等）
- ✨ **新增列**：交易次数、总浮动盈亏
- 🎨 **颜色优化**：采用中国市场习惯（红涨绿跌）
  - 盈亏：正数红色、负数绿色、零值黑色
  - 方向：多头红色、空头绿色

#### 仪表盘扩展
- 📊 **系统监控**（原有功能）：系统状态、CPU使用率、内存使用率
- 💰 **账户总览**：总资产、可用资金、保证金占用、浮动盈亏
- 📈 **今日表现**：当日收益率、盈亏金额、交易次数
- 📊 **持仓概览**：各品种持仓比例、市值分布
- 🔄 **策略运行状态**：运行中/已停止/异常的策略数量
- 📉 **关键指标图表**：资产曲线、每日盈亏、夏普比率等

#### 任务调度器
- ⏰ **任务管理**：支持5种任务类型（每日、单次、分钟、周、月）
- ✅ **任务控制**：启用/禁用、编辑、删除任务
- 📋 **执行历史**：查看任务执行历史记录
- ⏱️ **下次执行时间**：自动计算并显示相对时间

#### 通知中心
- 🔔 **顶部通知图标**：显示未读消息数量徽章
- 📨 **通知中心页面**：统一管理所有系统通知
- ✓ **已读标记**：点击通知自动标记为已读

#### 系统设置优化
- 📧 **消息通知方式**：支持钉钉、企业微信、邮箱（支持多选）
  - 钉钉：配置钉钉ID
  - 企业微信：配置企业微信ID
  - 邮箱：配置邮箱地址和SMTP服务器
- 🗑️ 移除系统名称配置（简化设置）

#### 控制台面板
- 🎮 **量化交易系统控制**：启动/停止量化交易系统（硬编码，待后端实现）
- 🎮 **数据中心控制**：启动/停止/重启数据中心（已对接真实后端API）
- 📊 **实时状态监控**：显示PID、运行时长、CPU使用率、内存使用
- 📝 **独立日志显示**：量化交易系统和数据中心各自独立的日志面板
- 🔍 **日志级别过滤**：支持按日志级别过滤（全部/信息/成功/警告/错误）

#### 其他界面优化
- ℹ️ **关于页面**：展示系统名称、版本、作者、版权、技术栈等信息
- 🔧 **设置图标**：顶部导航栏新增设置快捷入口

### 🏗️ 前端架构优化

#### 代码重构
- 📦 **模块化拆分**：将 `Home.vue`（3060行）优化至 1663行
  - `mock/`：硬编码数据分离
  - `constants/`：常量提取
  - `utils/`：工具函数提取
  - `composables/`：业务逻辑组件化
    - `useSystemMonitor.js`：系统监控
    - `useStrategyManagement.js`：策略管理
    - `useTaskScheduler.js`：任务调度
    - `useNotifications.js`：通知管理
    - `useConsole.js`：控制台
    - `useDashboard.js`：仪表盘
    - `useSettings.js`：系统设置

#### 代码质量提升
- ♻️ **可维护性**：单一职责原则，每个模块专注一个功能
- 🔄 **可复用性**：工具函数和业务逻辑可跨组件复用
- 📖 **可读性**：清晰的文件结构和命名规范

### 🚀 后端功能实现

#### 数据中心Web控制
- 🎮 **进程管理**：通过Web API控制数据中心进程
  - 启动：`POST /api/datacenter/start`
  - 停止：`POST /api/datacenter/stop`（支持优雅停止和强制停止）
  - 重启：`POST /api/datacenter/restart`
  - 状态查询：`GET /api/datacenter/status`
  - 日志获取：`GET /api/datacenter/logs`
  - 配置管理：`GET/PUT /api/datacenter/config`

#### 进程监控
- 📊 **实时状态**：PID、CPU使用率、内存使用、运行时长
- 📁 **PID文件**：`runtime/datacenter.pid`
- 📄 **状态文件**：`runtime/datacenter_status.json`
- 🔄 **状态轮询**：前端每5秒自动刷新状态

#### 安全与审计
- 🔐 **权限控制**：所有数据中心API需要管理员权限
- 📝 **审计日志**：记录所有操作（启动/停止/重启/配置修改）
  - 数据库存储（`audit_log`表）
  - 日志文件记录

#### 服务架构
- 🏗️ **服务分层**：
  - `DataCenterService`：进程管理核心逻辑
  - `ConfigService`：配置文件管理
  - API层：RESTful接口
  - Schemas：请求/响应验证
- 🔧 **容错机制**：
  - 进程存活检查
  - 状态文件监控
  - 优雅停止超时处理

### 🐛 Bug修复

- 🐛 修复数据中心日志乱码问题
  - 原因：loguru彩色输出的ANSI转义码写入日志文件
  - 解决：检测stdout是否为TTY，自动禁用彩色输出
  - 环境变量：`NO_COLOR=1`、`TERM=dumb`
- 🐛 修复停止数据中心按钮错误（事件对象被当作布尔参数）
- 🐛 修复量化交易系统状态显示为"0"而非"已停止"
- 🐛 修复`RuntimeWarning: coroutine 'AsyncSession.commit' was never awaited`
  - 将同步方法改为async/await模式
- 🐛 修复数据中心日志初始硬编码问题
- 🐛 修复多个UI显示和交互问题
- 🐛 修复数据中心启动失败问题（AttributeError: '_LOG_FILE' not found）
  - 原因：将 `_LOG_FILE` 重构为 `_LOG_DIR` 后，遗漏更新 `_ensure_runtime_dir()` 方法中的引用
  - 解决：将 `cls._LOG_FILE.parent.mkdir()` 修改为 `cls._LOG_DIR.mkdir()`

### ⚡ 性能优化

#### 日志轮询性能优化（CPU使用率降低80%）
- 🚀 **后端优化**：
  - 增量读取：只读取新增日志行，不再全文件读取
  - 使用deque优化尾部日志读取
  - 快速行计数：不将内容加载到内存
  - 内存占用降低99%，处理行数降低99.9%
- 🚀 **前端优化**：
  - 状态轮询间隔：5秒 → 10秒
  - 日志轮询间隔：3秒 → 5秒
  - 减少HTTP请求数量：每分钟从20次降到12次
- 📊 **性能提升**：
  - CPU使用率：从15-25%降至2-5%
  - 磁盘I/O减少95%
  - 适应大日志文件（10000+行）

### 📚 文档更新
- 📝 完善中文README（README_CN.md）
- 📖 同步英文和中文README内容
- 📋 更新CHANGELOG记录所有改进
- 📊 新增《数据中心日志性能优化》文档

### 🔧 技术改进
- ⚡ 日志编码优化：UTF-8强制编码，解决Windows中文乱码
- 🎨 UI/UX改进：采用中国市场配色习惯
- 🔄 异步数据库操作：全面使用async/await
- 📦 代码模块化：提升代码可维护性和可扩展性

## v0.0.1.20251008

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

## v0.0.1.20250908

### 初始版本
- 基础框架搭建
- CTP接口集成
- 事件驱动架构
