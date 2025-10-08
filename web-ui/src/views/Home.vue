<template>
  <el-container class="home-container">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-left">
        <h2>Homalos 量化交易系统</h2>
      </div>
      <div class="header-right">
        <!-- 通知图标 -->
        <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="header-icon">
          <el-icon :size="20" @click="handleNotificationClick">
            <Bell />
          </el-icon>
        </el-badge>
        
        <!-- 设置图标 -->
        <el-icon :size="20" class="header-icon" @click="handleSettingsClick">
          <Setting />
        </el-icon>
        
        <!-- 用户信息 -->
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            <span>{{ userStore.userInfo?.username || '用户' }}</span>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="200px" class="sidebar">
        <el-menu
          :default-active="activeMenu"
          class="sidebar-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="dashboard">
            <el-icon><Monitor /></el-icon>
            <span>系统监控</span>
          </el-menu-item>
          <el-menu-item index="strategy">
            <el-icon><DataAnalysis /></el-icon>
            <span>策略管理</span>
          </el-menu-item>
          <el-menu-item index="notifications">
            <el-icon><Bell /></el-icon>
            <span>通知中心</span>
          </el-menu-item>
          <el-menu-item index="settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
          <el-menu-item index="about">
            <el-icon><InfoFilled /></el-icon>
            <span>关于</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <el-card v-if="activeMenu === 'dashboard'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>系统监控</span>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic title="系统状态" value="运行中">
                <template #prefix>
                  <el-icon color="#67C23A"><SuccessFilled /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="CPU使用率" :value="systemInfo.cpu" suffix="%">
                <template #prefix>
                  <el-icon><Cpu /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="内存使用率" :value="systemInfo.memory" suffix="%">
                <template #prefix>
                  <el-icon><Memo /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </el-card>

        <el-card v-if="activeMenu === 'strategy'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>策略管理</span>
              <el-button type="primary" size="small">添加策略</el-button>
            </div>
          </template>
          <!-- 策略统计 -->
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="8">
              <el-statistic title="活跃策略" :value="systemInfo.activeStrategies">
                <template #prefix>
                  <el-icon color="#409eff"><DataAnalysis /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="运行中" :value="runningStrategiesCount">
                <template #prefix>
                  <el-icon color="#67C23A"><SuccessFilled /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="已停止" :value="stoppedStrategiesCount">
                <template #prefix>
                  <el-icon color="#909399"><Setting /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
          <el-table :data="strategies" style="width: 100%">
            <el-table-column prop="id" label="策略ID" width="100" />
            <el-table-column prop="name" label="策略名称" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status === '运行中' ? 'success' : 'info'">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="startTime" label="启动时间" width="180" />
            <el-table-column prop="runningTime" label="运行时长" width="120" />
            <el-table-column label="操作" width="220">
              <template #default="scope">
                <el-button
                  size="small"
                  :type="scope.row.status === '运行中' ? 'warning' : 'success'"
                >
                  {{ scope.row.status === '运行中' ? '停止' : '启动' }}
                </el-button>
                <el-button size="small" type="primary" @click="handleShowDetail(scope.row)">详情</el-button>
                <el-button size="small" type="danger" @click="handleDeleteStrategy(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 通知中心 -->
        <el-card v-if="activeMenu === 'notifications'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>通知中心</span>
              <el-button v-if="unreadCount > 0" type="primary" size="small" @click="markAllAsRead">全部已读</el-button>
            </div>
          </template>
          
          <div v-if="notifications.length === 0" class="empty-notification">
            <el-empty description="暂无通知" />
          </div>
          
          <el-timeline v-else class="notification-timeline">
            <el-timeline-item
              v-for="notification in notifications"
              :key="notification.id"
              :timestamp="notification.time"
              placement="top"
              :type="notification.type"
              :hollow="notification.isRead"
            >
              <el-card
                :class="['notification-item', { 'unread': !notification.isRead }]"
                shadow="hover"
                @click="markAsRead(notification)"
              >
                <div class="notification-header">
                  <span class="notification-title">
                    <span v-if="!notification.isRead" class="unread-dot"></span>
                    {{ notification.title }}
                  </span>
                  <el-tag :type="getNotificationTagType(notification.level)" size="small">
                    {{ notification.level }}
                  </el-tag>
                </div>
                <div class="notification-content">{{ notification.content }}</div>
                <div class="notification-footer">
                  <span class="notification-time">{{ notification.time }}</span>
                  <el-button v-if="!notification.isRead" type="text" size="small" @click.stop="markAsRead(notification)">
                    标记已读
                  </el-button>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <el-card v-if="activeMenu === 'settings'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>系统设置</span>
            </div>
          </template>
          <el-form label-width="140px">
            <el-form-item label="自动启动">
              <el-switch v-model="settings.autoStart" />
            </el-form-item>
            <el-form-item label="日志级别">
              <el-select v-model="settings.logLevel">
                <el-option label="DEBUG" value="debug" />
                <el-option label="INFO" value="info" />
                <el-option label="WARNING" value="warning" />
                <el-option label="ERROR" value="error" />
              </el-select>
            </el-form-item>
            <el-form-item label="消息通知方式">
              <el-checkbox-group v-model="settings.notificationMethods">
                <el-checkbox label="dingtalk">钉钉</el-checkbox>
                <el-checkbox label="wecom">企业微信</el-checkbox>
                <el-checkbox label="email">邮箱</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card v-if="activeMenu === 'about'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>关于系统</span>
            </div>
          </template>
          <el-descriptions :column="1" border size="large">
            <el-descriptions-item label="系统名称">
              <span style="font-weight: 600; font-size: 16px;">Homalos 量化交易系统</span>
            </el-descriptions-item>
            <el-descriptions-item label="版本">
              <el-tag type="success">v1.0.0</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="作者">
              Homalos Team
            </el-descriptions-item>
            <el-descriptions-item label="版权">
              Copyright © 2025 Homalos. All rights reserved.
            </el-descriptions-item>
            <el-descriptions-item label="简介">
              Homalos 是一个专业的期货量化交易系统，提供策略开发、回测、实盘交易等功能，助力投资者实现量化交易目标。
            </el-descriptions-item>
            <el-descriptions-item label="技术栈">
              <div style="line-height: 1.8;">
                <div>后端：Python 3.10 + FastAPI + SQLite</div>
                <div>前端：Vue 3 + Element Plus + Vite</div>
                <div>数据：行情接口 + 数据中心</div>
              </div>
            </el-descriptions-item>
            <el-descriptions-item label="联系方式">
              <div>
                <el-link type="primary" href="https://github.com/homalos" target="_blank">GitHub</el-link>
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 策略详情面板 -->
        <el-drawer
          v-model="detailDrawerVisible"
          :title="`策略详情 - ${currentStrategy?.name || ''}`"
          size="70%"
          direction="rtl"
        >
          <div v-if="currentStrategy" class="strategy-detail">
            <!-- 1. 基础信息 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <span class="section-title">基础信息</span>
              </template>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="策略名称">{{ currentStrategy.name }}</el-descriptions-item>
                <el-descriptions-item label="策略ID">{{ currentStrategy.id }}</el-descriptions-item>
                <el-descriptions-item label="作者">{{ currentStrategy.author }}</el-descriptions-item>
                <el-descriptions-item label="创建时间">{{ currentStrategy.createTime }}</el-descriptions-item>
                <el-descriptions-item label="最后修改时间" :span="2">{{ currentStrategy.lastModifyTime }}</el-descriptions-item>
                <el-descriptions-item label="策略描述" :span="2">{{ currentStrategy.description }}</el-descriptions-item>
              </el-descriptions>
            </el-card>

            <!-- 2. 持仓信息 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <span class="section-title">持仓信息</span>
              </template>
              <el-table :data="currentStrategy.positions" border stripe>
                <el-table-column prop="contract" label="合约代码" width="100" />
                <el-table-column prop="volume" label="持仓量" width="80" />
                <el-table-column prop="direction" label="方向" width="60">
                  <template #default="scope">
                    <el-tag :type="scope.row.direction === '多' ? 'success' : 'danger'">
                      {{ scope.row.direction }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="holdPrice" label="成本价" width="100" />
                <el-table-column prop="latestPrice" label="最新价" width="100" />
                <el-table-column prop="tradeTime" label="成交时间" width="160" />
                <el-table-column prop="orderStatus" label="委托状态" width="100">
                  <template #default="scope">
                    <el-tag 
                      :type="scope.row.orderStatus === '全部成交' ? 'success' : scope.row.orderStatus === '部分成交' ? 'warning' : 'info'"
                    >
                      {{ scope.row.orderStatus }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="takeProfitPrice" label="止盈价" width="100" />
                <el-table-column prop="stopLossPrice" label="止损价" width="100" />
                <el-table-column prop="margin" label="保证金" width="120">
                  <template #default="scope">
                    {{ scope.row.margin.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="profitLoss" label="浮动盈亏" width="100">
                  <template #default="scope">
                    <span :style="{ color: scope.row.profitLoss >= 0 ? '#67C23A' : '#F56C6C' }">
                      {{ scope.row.profitLoss >= 0 ? '+' : '' }}{{ scope.row.profitLoss.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="profitLossRatio" label="盈亏比" width="80">
                  <template #default="scope">
                    <span :style="{ color: scope.row.profitLossRatio >= 0 ? '#67C23A' : '#F56C6C' }">
                      {{ scope.row.profitLossRatio >= 0 ? '+' : '' }}{{ scope.row.profitLossRatio.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="returnRate" label="收益率" width="100">
                  <template #default="scope">
                    <span :style="{ color: scope.row.returnRate >= 0 ? '#67C23A' : '#F56C6C' }">
                      {{ scope.row.returnRate >= 0 ? '+' : '' }}{{ scope.row.returnRate.toFixed(2) }}%
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <!-- 3. 风险控制 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <span class="section-title">风险控制</span>
              </template>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="最大仓位">{{ currentStrategy.riskControl.maxPosition }} 手</el-descriptions-item>
                <el-descriptions-item label="止损比例">{{ currentStrategy.riskControl.stopLossRatio }}%</el-descriptions-item>
                <el-descriptions-item label="止盈比例">{{ currentStrategy.riskControl.takeProfitRatio }}%</el-descriptions-item>
                <el-descriptions-item label="最大回撤">{{ currentStrategy.riskControl.maxDrawdown }}%</el-descriptions-item>
              </el-descriptions>
            </el-card>

            <!-- 4. 风险控制参数配置 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <div class="section-header">
                  <span class="section-title">风险控制参数配置</span>
                  <div>
                    <el-button size="small" @click="handleCancelEdit">取消</el-button>
                    <el-button size="small" type="primary" @click="handleSaveParameters">保存</el-button>
                  </div>
                </div>
              </template>
              
              <el-form :model="editableParameters" label-width="140px">
                <!-- 风险参数 -->
                <el-divider content-position="left">风险参数</el-divider>
                <el-form-item label="最大仓位（手）">
                  <el-input-number v-model="editableParameters.riskControl.maxPosition" :min="1" :max="200" />
                </el-form-item>
                <el-form-item label="止损比例（%）">
                  <el-input-number v-model="editableParameters.riskControl.stopLossRatio" :min="0.1" :max="10" :step="0.1" :precision="1" />
                </el-form-item>
                <el-form-item label="止盈比例（%）">
                  <el-input-number v-model="editableParameters.riskControl.takeProfitRatio" :min="0.1" :max="20" :step="0.1" :precision="1" />
                </el-form-item>
                <el-form-item label="最大回撤（%）">
                  <el-input-number v-model="editableParameters.riskControl.maxDrawdown" :min="1" :max="50" :step="1" :precision="1" />
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </el-drawer>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  User,
  ArrowDown,
  Monitor,
  DataAnalysis,
  Setting,
  SuccessFilled,
  Cpu,
  Memo,
  InfoFilled,
  Bell
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getSystemStats } from '@/api/monitor'

const router = useRouter()
const userStore = useUserStore()

const activeMenu = ref('dashboard')

// 通知列表（硬编码数据）
const notifications = ref([
  {
    id: 1,
    title: '策略运行异常',
    content: '趋势跟踪策略在AU2406合约上出现异常，已自动停止运行，请检查策略参数。',
    time: '2025-10-08 22:30:15',
    level: '紧急',
    type: 'danger',
    isRead: false
  },
  {
    id: 2,
    title: '持仓盈利提醒',
    content: '均值回归策略在CU2406合约上盈利已达到止盈价，建议关注市场行情及时调整。',
    time: '2025-10-08 21:45:30',
    level: '重要',
    type: 'warning',
    isRead: false
  },
  {
    id: 3,
    title: '系统更新通知',
    content: '系统将于今晚23:00进行例行维护，预计维护时间30分钟，期间系统将暂停交易。',
    time: '2025-10-08 20:15:00',
    level: '通知',
    type: 'primary',
    isRead: false
  },
  {
    id: 4,
    title: '风险控制提醒',
    content: '当前账户总持仓占比已达70%，接近风控阈值，建议适当降低仓位。',
    time: '2025-10-08 18:20:45',
    level: '重要',
    type: 'warning',
    isRead: true
  },
  {
    id: 5,
    title: '策略启动成功',
    content: '套利策略已成功启动，当前运行状态正常，开始执行交易逻辑。',
    time: '2025-10-08 15:30:00',
    level: '通知',
    type: 'success',
    isRead: true
  }
])

// 未读通知数量（计算属性）
const unreadCount = computed(() => {
  return notifications.value.filter(n => !n.isRead).length
})

// 定时器引用
let monitorTimer = null

// 系统监控信息
const systemInfo = reactive({
  cpu: 0,
  memory: 0,
  activeStrategies: 3,  // 硬编码值
  lastUpdate: null,
  loading: false,
  error: null
})

const strategies = ref([
  { 
    // === 基础字段 ===
    id: 'STR001', 
    name: '趋势跟踪策略', 
    status: '运行中', 
    startTime: '2025-10-08 09:30:00',
    runningTime: '12h15m',
    
    // === 基础信息 ===
    description: '基于趋势线和移动平均线的跟踪策略，适用于趋势明显的市场环境，通过识别市场趋势方向进行交易',
    author: '张三',
    createTime: '2025-10-01 14:20:00',
    lastModifyTime: '2025-10-07 16:45:00',
    
    // === 持仓信息 ===
    positions: [
      {
        contract: 'AU2406',
        volume: 10,
        direction: '多',
        holdPrice: 450.5,
        latestPrice: 462.3,
        tradeTime: '2025-10-08 09:15:32',
        orderStatus: '全部成交',
        takeProfitPrice: 460.0,
        stopLossPrice: 445.0,
        margin: 45050.0,
        profitLoss: 1200.5,
        profitLossRatio: 2.67,
        returnRate: 2.67
      },
      {
        contract: 'AG2406',
        volume: 20,
        direction: '空',
        holdPrice: 5200.0,
        latestPrice: 5175.0,
        tradeTime: '2025-10-08 10:20:15',
        orderStatus: '部分成交',
        takeProfitPrice: 5100.0,
        stopLossPrice: 5250.0,
        margin: 104000.0,
        profitLoss: -500.0,
        profitLossRatio: -0.48,
        returnRate: -0.48
      }
    ],
    
    // === 参数配置 ===
    parameters: {
      trading: {
        lotSize: 1,
        maxOrders: 5,
        orderInterval: 60,
        enableCompound: true
      },
      risk: {
        stopLossPercent: 2.0,
        takeProfitPercent: 3.0,
        maxDrawdown: 10.0,
        riskRewardRatio: 1.5
      },
      indicator: {
        maPeriod: 20,
        maType: 'SMA',
        rsiPeriod: 14,
        enableMACD: true
      }
    },
    
    // === 风险控制 ===
    riskControl: {
      maxPosition: 50,
      stopLossRatio: 2.0,
      takeProfitRatio: 3.0,
      maxDrawdown: 10.0,
      maxLeverage: 3.0,
      riskLevel: '中'
    }
  },
  { 
    // === 基础字段 ===
    id: 'STR002', 
    name: '均值回归策略', 
    status: '已停止', 
    startTime: '2025-10-07 14:20:00',
    runningTime: '-',
    
    // === 基础信息 ===
    description: '当价格偏离均值时进行反向交易，预期价格会回归均值，适用于震荡市场',
    author: '李四',
    createTime: '2025-09-25 10:30:00',
    lastModifyTime: '2025-10-06 09:15:00',
    
    // === 持仓信息 ===
    positions: [
      {
        contract: 'CU2406',
        volume: 15,
        direction: '多',
        holdPrice: 68500.0,
        latestPrice: 69065.0,
        tradeTime: '2025-10-07 14:30:28',
        orderStatus: '全部成交',
        takeProfitPrice: 70000.0,
        stopLossPrice: 67500.0,
        margin: 102750.0,
        profitLoss: 850.0,
        profitLossRatio: 0.83,
        returnRate: 0.83
      }
    ],
    
    // === 参数配置 ===
    parameters: {
      trading: {
        lotSize: 2,
        maxOrders: 3,
        orderInterval: 120,
        enableCompound: false
      },
      risk: {
        stopLossPercent: 1.5,
        takeProfitPercent: 2.5,
        maxDrawdown: 8.0,
        riskRewardRatio: 1.8
      },
      indicator: {
        maPeriod: 30,
        maType: 'EMA',
        rsiPeriod: 10,
        enableMACD: false
      }
    },
    
    // === 风险控制 ===
    riskControl: {
      maxPosition: 30,
      stopLossRatio: 1.5,
      takeProfitRatio: 2.5,
      maxDrawdown: 8.0,
      maxLeverage: 2.0,
      riskLevel: '低'
    }
  },
  { 
    // === 基础字段 ===
    id: 'STR003', 
    name: '套利策略', 
    status: '运行中', 
    startTime: '2025-10-08 10:45:00',
    runningTime: '10h50m',
    
    // === 基础信息 ===
    description: '利用不同合约或市场间的价差进行套利交易，风险相对较低，收益稳定',
    author: '王五',
    createTime: '2025-10-03 11:00:00',
    lastModifyTime: '2025-10-08 08:30:00',
    
    // === 持仓信息 ===
    positions: [
      {
        contract: 'RB2406',
        volume: 25,
        direction: '多',
        holdPrice: 3850.0,
        latestPrice: 3875.0,
        tradeTime: '2025-10-08 11:05:45',
        orderStatus: '待成交',
        takeProfitPrice: 3900.0,
        stopLossPrice: 3820.0,
        margin: 96250.0,
        profitLoss: 625.0,
        profitLossRatio: 0.65,
        returnRate: 0.65
      },
      {
        contract: 'RB2409',
        volume: 25,
        direction: '空',
        holdPrice: 3880.0,
        latestPrice: 3850.0,
        tradeTime: '2025-10-08 13:22:18',
        orderStatus: '全部成交',
        takeProfitPrice: 3830.0,
        stopLossPrice: 3910.0,
        margin: 97000.0,
        profitLoss: 750.0,
        profitLossRatio: 0.77,
        returnRate: 0.77
      }
    ],
    
    // === 参数配置 ===
    parameters: {
      trading: {
        lotSize: 3,
        maxOrders: 10,
        orderInterval: 30,
        enableCompound: true
      },
      risk: {
        stopLossPercent: 0.8,
        takeProfitPercent: 1.5,
        maxDrawdown: 5.0,
        riskRewardRatio: 2.0
      },
      indicator: {
        maPeriod: 15,
        maType: 'WMA',
        rsiPeriod: 12,
        enableMACD: true
      }
    },
    
    // === 风险控制 ===
    riskControl: {
      maxPosition: 100,
      stopLossRatio: 0.8,
      takeProfitRatio: 1.5,
      maxDrawdown: 5.0,
      maxLeverage: 5.0,
      riskLevel: '高'
    }
  }
])

// 计算运行中的策略数量
const runningStrategiesCount = computed(() => {
  return strategies.value.filter(s => s.status === '运行中').length
})

// 计算已停止的策略数量
const stoppedStrategiesCount = computed(() => {
  return strategies.value.filter(s => s.status === '已停止').length
})

// 详情面板状态
const detailDrawerVisible = ref(false)
const currentStrategy = ref(null)
const editableParameters = reactive({
  trading: {},
  risk: {},
  indicator: {},
  riskControl: {}
})

const settings = reactive({
  systemName: 'Homalos',
  autoStart: true,
  logLevel: 'info',
  notificationMethods: ['dingtalk', 'email']  // 默认启用钉钉和邮箱
})

/**
 * 获取系统监控数据
 */
const fetchSystemStats = async () => {
  try {
    systemInfo.loading = true
    const data = await getSystemStats()
    
    systemInfo.cpu = data.cpu_percent
    systemInfo.memory = data.memory_percent
    systemInfo.lastUpdate = data.timestamp
    systemInfo.error = null
  } catch (error) {
    console.error('获取监控数据失败:', error)
    systemInfo.error = '获取监控数据失败'
    // 保留上次的数据，不清空
  } finally {
    systemInfo.loading = false
  }
}

/**
 * 启动监控数据轮询
 */
const startMonitoring = () => {
  fetchSystemStats()  // 立即获取一次
  monitorTimer = setInterval(fetchSystemStats, 3000)  // 每3秒刷新
}

/**
 * 停止监控数据轮询
 */
const stopMonitoring = () => {
  if (monitorTimer) {
    clearInterval(monitorTimer)
    monitorTimer = null
  }
}

const handleMenuSelect = (index) => {
  activeMenu.value = index
}

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}

/**
 * 处理通知图标点击，跳转到通知中心
 */
const handleNotificationClick = () => {
  activeMenu.value = 'notifications'
}

/**
 * 处理设置图标点击，跳转到系统设置页面
 */
const handleSettingsClick = () => {
  activeMenu.value = 'settings'
}

/**
 * 标记单条通知为已读
 */
const markAsRead = (notification) => {
  if (!notification.isRead) {
    notification.isRead = true
    ElMessage.success('通知已标记为已读')
  }
}

/**
 * 全部标记为已读
 */
const markAllAsRead = () => {
  ElMessageBox.confirm('确定将所有通知标记为已读吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'info'
  }).then(() => {
    notifications.value.forEach(n => {
      n.isRead = true
    })
    ElMessage.success('所有通知已标记为已读')
  }).catch(() => {
    // 取消操作
  })
}

/**
 * 获取通知标签类型
 */
const getNotificationTagType = (level) => {
  const typeMap = {
    '紧急': 'danger',
    '重要': 'warning',
    '通知': 'info'
  }
  return typeMap[level] || 'info'
}

/**
 * 显示策略详情
 */
const handleShowDetail = (strategy) => {
  currentStrategy.value = strategy
  // 深拷贝参数到可编辑对象
  editableParameters.trading = { ...strategy.parameters.trading }
  editableParameters.risk = { ...strategy.parameters.risk }
  editableParameters.indicator = { ...strategy.parameters.indicator }
  editableParameters.riskControl = { ...strategy.riskControl }
  detailDrawerVisible.value = true
}

/**
 * 保存参数配置
 */
const handleSaveParameters = () => {
  if (!currentStrategy.value) return
  
  // 更新策略参数
  currentStrategy.value.parameters.trading = { ...editableParameters.trading }
  currentStrategy.value.parameters.risk = { ...editableParameters.risk }
  currentStrategy.value.parameters.indicator = { ...editableParameters.indicator }
  currentStrategy.value.riskControl = { ...editableParameters.riskControl }
  
  // 更新最后修改时间
  const now = new Date()
  currentStrategy.value.lastModifyTime = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).replace(/\//g, '-')
  
  ElMessage.success('参数保存成功')
}

/**
 * 取消编辑
 */
const handleCancelEdit = () => {
  if (!currentStrategy.value) return
  
  // 恢复原始参数
  editableParameters.trading = { ...currentStrategy.value.parameters.trading }
  editableParameters.risk = { ...currentStrategy.value.parameters.risk }
  editableParameters.indicator = { ...currentStrategy.value.parameters.indicator }
  editableParameters.riskControl = { ...currentStrategy.value.riskControl }
  
  ElMessage.info('已取消编辑')
}

/**
 * 获取风险等级标签类型
 */
const getRiskLevelType = (level) => {
  const typeMap = {
    '低': 'success',
    '中': 'warning',
    '高': 'danger'
  }
  return typeMap[level] || 'info'
}

/**
 * 删除策略
 */
const handleDeleteStrategy = (strategy) => {
  ElMessageBox.confirm(
    `确定要删除策略 "${strategy.name}" (ID: ${strategy.id}) 吗？`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    // 从策略列表中移除
    const index = strategies.value.findIndex(s => s.id === strategy.id)
    if (index !== -1) {
      strategies.value.splice(index, 1)
      ElMessage.success(`策略 "${strategy.name}" 已删除`)
    }
  }).catch(() => {
    // 用户取消删除
  })
}

onMounted(async () => {
  // 获取用户信息
  if (!userStore.userInfo) {
    const success = await userStore.fetchUserInfo()
    if (!success) {
      ElMessage.error('获取用户信息失败，请重新登录')
      router.push('/login')
      return
    }
  }
  
  // 启动监控
  startMonitoring()
})

onUnmounted(() => {
  // 组件卸载时停止监控
  stopMonitoring()
})
</script>

<style scoped>
.home-container {
  height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #409eff;
  color: white;
  padding: 0 20px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-icon {
  cursor: pointer;
  transition: opacity 0.3s;
}

.header-icon:hover {
  opacity: 0.8;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: white;
}

.sidebar {
  background-color: #f5f7fa;
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.el-statistic) {
  text-align: center;
}

/* 策略详情面板样式 */
.strategy-detail {
  padding: 0 20px 20px;
}

.detail-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 持仓表格紧凑布局 */
.detail-section :deep(.el-table) {
  font-size: 13px;
}

/* 表单项间距 */
.detail-section :deep(.el-form-item) {
  margin-bottom: 18px;
}

/* 分割线样式 */
.detail-section :deep(.el-divider__text) {
  font-weight: 600;
  color: #606266;
}

/* 通知中心样式 */
.empty-notification {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.notification-timeline {
  margin-top: 20px;
  padding-left: 20px;
}

.notification-item {
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 0;
}

.notification-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.notification-item.unread {
  background-color: #f0f9ff;
  border-left: 3px solid #409eff;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.notification-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.unread-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  background-color: #409eff;
  border-radius: 50%;
  margin-right: 6px;
}

.notification-content {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
  word-break: break-word;
}

.notification-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
}

.notification-time {
  font-size: 12px;
  color: #909399;
}

</style>

