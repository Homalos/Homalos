## Home.vue 布局优化

#### 目标文件结构
```
web-ui/src/
├── mock/
│   ├── strategyTemplates.js      # 策略模板数据
│   ├── strategyLogs.js            # 策略日志数据
│   ├── scheduledTasks.js          # 任务调度数据
│   ├── notifications.js           # 通知数据
│   ├── consoleLogs.js             # 控制台日志
│   ├── strategies.js              # 策略数据
│   └── dashboardData.js           # 仪表盘数据
```

#### 目标文件结构
```
web-ui/src/
├── views/
│   ├── Home.vue                   # 主容器（保留）
│   └── home/                      # Home 子页面目录
│       ├── Dashboard.vue          # 仪表盘页面
│       ├── Console.vue            # 控制台页面
│       ├── StrategyManagement.vue # 策略管理页面
│       ├── TaskScheduler.vue      # 任务调度器页面
│       ├── NotificationCenter.vue # 通知中心页面
│       ├── Settings.vue           # 系统设置页面
│       └── About.vue              # 关于页面
```

#### 目标组件
```
web-ui/src/
├── components/
│   ├── StrategyDetailDrawer.vue   # 策略详情抽屉
│   ├── AddStrategyDialog.vue      # 添加策略对话框
│   └── TaskFormDialog.vue         # 任务表单对话框
```

#### 目标文件结构
```
web-ui/src/
├── composables/
│   ├── useStrategies.js           # 策略管理逻辑
│   ├── useTasks.js                # 任务调度逻辑
│   ├── useNotifications.js        # 通知管理逻辑
│   ├── useConsole.js              # 控制台逻辑
│   └── useSystemMonitor.js        # 系统监控逻辑
```

---

## 重构后的最终文件结构

```
web-ui/src/
├── views/
│   ├── Home.vue                   # 主容器 (~200 行)
│   └── home/
│       ├── Dashboard.vue          # ~150 行
│       ├── Console.vue            # ~120 行
│       ├── StrategyManagement.vue # ~180 行
│       ├── TaskScheduler.vue      # ~150 行
│       ├── NotificationCenter.vue # ~80 行
│       ├── Settings.vue           # ~100 行
│       └── About.vue              # ~50 行
├── components/
│   ├── StrategyDetailDrawer.vue   # ~120 行
│   ├── AddStrategyDialog.vue      # ~60 行
│   └── TaskFormDialog.vue         # ~120 行
├── composables/
│   ├── useStrategies.js           # ~200 行
│   ├── useTasks.js                # ~250 行
│   ├── useNotifications.js        # ~50 行
│   ├── useConsole.js              # ~120 行
│   └── useSystemMonitor.js        # ~80 行
├── mock/
│   ├── index.js                   # 统一导出
│   ├── strategyTemplates.js       # ~70 行
│   ├── strategyLogs.js            # ~90 行
│   ├── scheduledTasks.js          # ~65 行
│   ├── notifications.js           # ~55 行
│   ├── consoleLogs.js             # ~65 行
│   ├── strategies.js              # ~230 行
│   └── dashboardData.js           # ~35 行
└── constants/
    ├── taskTypeMap.js             # 任务类型映射
    └── logLevelMap.js             # 日志级别映射
```

### 📁 创建的文件结构

```
web-ui/src/
├── mock/                          # Mock 数据目录
│   ├── index.js                   # 统一导出文件
│   ├── strategyTemplates.js       # 策略模板数据
│   ├── strategyLogs.js            # 策略日志数据
│   ├── scheduledTasks.js          # 任务调度数据
│   ├── notifications.js           # 通知数据
│   ├── consoleLogs.js             # 控制台日志数据
│   ├── strategies.js              # 策略数据
│   └── dashboardData.js           # 仪表盘数据
└── constants/                     # 常量目录
    └── index.js                   # 常量定义（logLevelMap, taskTypeMap, weekDayMap）
```

### 📁 创建的文件结构

```
web-ui/src/utils/
├── index.js                 # 统一导出文件
├── timeUtils.js             # 时间处理工具函数
├── taskUtils.js             # 任务调度相关工具函数
├── strategyUtils.js         # 策略相关工具函数
└── commonUtils.js           # 通用工具函数
```

```
web-ui/src/
├── composables/                  # 新增：业务逻辑组合式函数
│   ├── index.js                  # 统一导出
│   ├── useSystemMonitor.js       # 系统监控逻辑
│   ├── useStrategyManagement.js  # 策略管理逻辑（最复杂）
│   ├── useTaskScheduler.js       # 任务调度逻辑
│   ├── useNotifications.js       # 通知管理逻辑
│   └── useConsole.js             # 控制台逻辑
├── mock/                         # 已有：模拟数据
├── constants/                    # 已有：常量定义
├── utils/                        # 已有：工具函数
└── views/
    └── Home.vue                  # 优化后：只保留UI和基础逻辑
```

### **新增文件架构**

```
web-ui/src/
├── composables/              # 业务逻辑 Composables (7个文件)
│   ├── index.js
│   ├── useSystemMonitor.js
│   ├── useStrategyManagement.js
│   ├── useTaskScheduler.js
│   ├── useNotifications.js
│   ├── useConsole.js
│   ├── useDashboard.js
│   └── useSettings.js
│
├── components/home/          # UI 组件 (9个文件)
│   ├── HeaderNav.vue
│   ├── Sidebar.vue
│   ├── DashboardPanel.vue
│   ├── ConsolePanel.vue
│   ├── StrategyPanel.vue
│   ├── TaskSchedulerPanel.vue
│   ├── NotificationsPanel.vue
│   ├── SettingsPanel.vue
│   └── AboutPanel.vue
│
├── mock/                     # 模拟数据 (8个文件)
│   ├── index.js
│   ├── strategyTemplates.js
│   ├── strategyLogs.js
│   ├── scheduledTasks.js
│   ├── notifications.js
│   ├── consoleLogs.js
│   ├── strategies.js
│   └── dashboardData.js
│
├── constants/                # 常量定义 (1个文件)
│   └── index.js
│
├── utils/                    # 工具函数 (5个文件)
│   ├── index.js
│   ├── timeUtils.js
│   ├── taskUtils.js
│   ├── strategyUtils.js
│   └── commonUtils.js
│
└── views/
    └── Home.vue              # ⭐ 主文件 (112行)
```

现在的布局结构：
```
┌─────────────────────────────────────┐
│     顶部导航栏 (HeaderNav)           │  ← 在最上方
├──────────┬──────────────────────────┤
│  侧边栏  │    主内容区               │
│ Sidebar  │   (各种Panel)            │  ← 水平排列
│          │                          │
│          │                          │
└──────────┴──────────────────────────┘
```
