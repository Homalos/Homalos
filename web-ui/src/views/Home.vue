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
        
        <!-- 控制台图标 -->
        <el-icon :size="20" class="header-icon" @click="handleConsoleClick">
          <Operation />
        </el-icon>
        
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
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="console">
            <el-icon><Operation /></el-icon>
            <span>控制台</span>
          </el-menu-item>
          <el-menu-item index="strategy">
            <el-icon><DataAnalysis /></el-icon>
            <span>策略管理</span>
          </el-menu-item>
          <el-menu-item index="task-scheduler">
            <el-icon><Timer /></el-icon>
            <span>任务调度器</span>
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
        <!-- 仪表盘 -->
        <div v-if="activeMenu === 'dashboard'">
          <!-- 1. 账户总览 -->
          <el-card shadow="hover" style="margin-bottom: 20px;">
            <template #header>
              <div class="card-header">
                <span>账户总览</span>
              </div>
            </template>
            <el-row :gutter="20">
              <el-col :span="6">
                <el-statistic title="总资产" :value="dashboardData.account.totalAssets" precision="2" prefix="¥">
                  <template #prefix>
                    <el-icon color="#409EFF"><Wallet /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="6">
                <el-statistic title="可用资金" :value="dashboardData.account.availableFunds" precision="2" prefix="¥">
                  <template #prefix>
                    <el-icon color="#67C23A"><Money /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="6">
                <el-statistic title="保证金占用" :value="dashboardData.account.marginUsed" precision="2" prefix="¥">
                  <template #prefix>
                    <el-icon color="#E6A23C"><Lock /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="6">
                <el-statistic 
                  title="浮动盈亏" 
                  :value="dashboardData.account.floatingProfitLoss" 
                  precision="2" 
                  prefix="¥"
                  :value-style="{ color: dashboardData.account.floatingProfitLoss > 0 ? '#F56C6C' : dashboardData.account.floatingProfitLoss < 0 ? '#67C23A' : '#000000' }"
                >
                  <template #prefix>
                    <el-icon :color="dashboardData.account.floatingProfitLoss > 0 ? '#F56C6C' : dashboardData.account.floatingProfitLoss < 0 ? '#67C23A' : '#000000'">
                      <TrendCharts />
                    </el-icon>
                  </template>
                </el-statistic>
              </el-col>
            </el-row>
          </el-card>

          <!-- 2. 今日表现 & 策略运行状态 -->
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>今日表现（{{ todayDate }}）</span>
                  </div>
                </template>
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-statistic 
                      title="当日收益率" 
                      :value="dashboardData.todayPerformance.returnRate" 
                      precision="2" 
                      suffix="%"
                      :value-style="{ color: dashboardData.todayPerformance.returnRate > 0 ? '#F56C6C' : dashboardData.todayPerformance.returnRate < 0 ? '#67C23A' : '#000000' }"
                    >
                      <template #prefix>
                        <el-icon :color="dashboardData.todayPerformance.returnRate > 0 ? '#F56C6C' : dashboardData.todayPerformance.returnRate < 0 ? '#67C23A' : '#000000'">
                          <DataLine />
                        </el-icon>
                      </template>
                    </el-statistic>
                  </el-col>
                  <el-col :span="8">
                    <el-statistic 
                      title="盈亏金额" 
                      :value="dashboardData.todayPerformance.profitLoss" 
                      precision="2" 
                      prefix="¥"
                      :value-style="{ color: dashboardData.todayPerformance.profitLoss > 0 ? '#F56C6C' : dashboardData.todayPerformance.profitLoss < 0 ? '#67C23A' : '#000000' }"
                    >
                      <template #prefix>
                        <el-icon :color="dashboardData.todayPerformance.profitLoss > 0 ? '#F56C6C' : dashboardData.todayPerformance.profitLoss < 0 ? '#67C23A' : '#000000'">
                          <Coin />
                        </el-icon>
                      </template>
                    </el-statistic>
                  </el-col>
                  <el-col :span="8">
                    <el-statistic title="交易次数" :value="dashboardData.todayPerformance.tradeCount">
                      <template #prefix>
                        <el-icon color="#409EFF"><Operation /></el-icon>
                      </template>
                    </el-statistic>
                  </el-col>
                </el-row>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>策略运行状态</span>
                  </div>
                </template>
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-statistic title="运行中" :value="dashboardData.strategyStatus.running">
                      <template #prefix>
                        <el-icon color="#67C23A"><VideoPlay /></el-icon>
                      </template>
                    </el-statistic>
                  </el-col>
                  <el-col :span="8">
                    <el-statistic title="已停止" :value="dashboardData.strategyStatus.stopped">
                      <template #prefix>
                        <el-icon color="#909399"><VideoPause /></el-icon>
                      </template>
                    </el-statistic>
                  </el-col>
                  <el-col :span="8">
                    <el-statistic title="异常" :value="dashboardData.strategyStatus.error">
                      <template #prefix>
                        <el-icon color="#F56C6C"><Warning /></el-icon>
                      </template>
                    </el-statistic>
                  </el-col>
                </el-row>
              </el-card>
            </el-col>
          </el-row>

          <!-- 3. 系统监控 & 持仓概览 -->
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="12">
              <el-card shadow="hover">
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
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>持仓概览</span>
                  </div>
                </template>
                <div style="padding: 10px 0;">
                  <div v-for="(item, index) in dashboardData.positions" :key="index" style="margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                      <span>{{ item.name }}</span>
                      <span>{{ item.ratio }}%</span>
                    </div>
                    <el-progress :percentage="item.ratio" :color="item.color" :show-text="false" />
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 4. 关键指标图表 -->
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>关键指标图表</span>
              </div>
            </template>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="chart-placeholder">
                  <el-icon size="60" color="#909399"><DataLine /></el-icon>
                  <div style="margin-top: 10px; color: #909399;">资产曲线图表（待开发）</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="chart-placeholder">
                  <el-icon size="60" color="#909399"><DataAnalysis /></el-icon>
                  <div style="margin-top: 10px; color: #909399;">每日盈亏图表（待开发）</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="chart-placeholder">
                  <el-icon size="60" color="#909399"><TrendCharts /></el-icon>
                  <div style="margin-top: 10px; color: #909399;">夏普比率图表（待开发）</div>
                </div>
              </el-col>
            </el-row>
          </el-card>
        </div>

        <!-- 控制台 -->
        <Console v-if="activeMenu === 'console'" />

        <el-card v-if="activeMenu === 'strategy'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>策略管理</span>
              <el-button type="primary" size="small" @click="addStrategyDialogVisible = true">添加策略</el-button>
            </div>
          </template>
          <!-- 策略统计 -->
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="8">
              <el-statistic title="活跃策略" :value="activeStrategiesCount">
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
            <el-table-column label="浮动盈亏" width="120">
              <template #default="scope">
                <span :style="{ color: getTotalProfitLoss(scope.row) > 0 ? '#F56C6C' : getTotalProfitLoss(scope.row) < 0 ? '#67C23A' : '#000000' }">
                  {{ getTotalProfitLoss(scope.row) > 0 ? '+' : '' }}{{ getTotalProfitLoss(scope.row).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="交易次数" width="100">
              <template #default="scope">
                {{ scope.row.positions.length }}
              </template>
            </el-table-column>
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
                  v-if="scope.row.status === '已停止'"
                  size="small"
                  type="success"
                  @click="handleStartStrategy(scope.row)"
                >
                  启动
                </el-button>
                <el-button
                  v-if="scope.row.status === '运行中'"
                  size="small"
                  type="warning"
                  @click="handleStopStrategy(scope.row)"
                >
                  停止
                </el-button>
                <el-button size="small" type="primary" @click="handleShowDetail(scope.row)">详情</el-button>
                <el-button size="small" type="danger" @click="handleDeleteStrategy(scope.row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 操作日志 -->
        <el-card v-if="activeMenu === 'strategy'" shadow="hover" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <span>操作日志</span>
              <el-select 
                v-model="selectedLogLevel" 
                placeholder="选择日志级别" 
                size="small" 
                style="width: 150px;"
              >
                <el-option label="全部" value="all" />
                <el-option label="信息" value="info" />
                <el-option label="成功" value="success" />
                <el-option label="警告" value="warning" />
                <el-option label="错误" value="error" />
              </el-select>
            </div>
          </template>
          <div class="log-container">
            <el-timeline v-if="filteredStrategyLogs.length > 0">
              <el-timeline-item 
                v-for="log in filteredStrategyLogs" 
                :key="log.id"
                :timestamp="log.timestamp"
                placement="top"
              >
                <div class="log-item">
                  <el-tag 
                    :type="logLevelMap[log.level].color" 
                    size="small" 
                    style="margin-right: 8px;"
                  >
                    {{ log.category }}
                  </el-tag>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无日志记录" />
          </div>
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

        <!-- 任务调度器 -->
        <TaskScheduler v-if="activeMenu === 'task-scheduler'" />

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
            
            <!-- 钉钉通知配置 -->
            <el-divider content-position="left">
              <span style="font-weight: 600;">钉钉通知配置</span>
            </el-divider>
            <el-card shadow="never" style="margin-bottom: 20px; background-color: #fafafa;">
              <el-form-item label="启用钉钉通知">
                <el-switch v-model="settings.notificationConfig.dingtalk.enabled" />
              </el-form-item>
              <template v-if="settings.notificationConfig.dingtalk.enabled">
                <el-form-item label="机器人名称">
                  <el-input 
                    v-model="settings.notificationConfig.dingtalk.name" 
                    placeholder="请输入钉钉机器人名称"
                    style="width: 400px;"
                  />
                </el-form-item>
                <el-form-item label="机器人ID">
                  <el-input 
                    v-model="settings.notificationConfig.dingtalk.id" 
                    placeholder="请输入钉钉机器人ID"
                    style="width: 400px;"
                  />
                </el-form-item>
                <el-form-item label="Webhook地址">
                  <el-input 
                    v-model="settings.notificationConfig.dingtalk.webhookUrl" 
                    placeholder="请输入钉钉Webhook地址"
                    style="width: 400px;"
                  />
                </el-form-item>
              </template>
            </el-card>
            
            <!-- 企业微信通知配置 -->
            <el-divider content-position="left">
              <span style="font-weight: 600;">企业微信通知配置</span>
            </el-divider>
            <el-card shadow="never" style="margin-bottom: 20px; background-color: #fafafa;">
              <el-form-item label="启用企业微信通知">
                <el-switch v-model="settings.notificationConfig.wecom.enabled" />
              </el-form-item>
              <template v-if="settings.notificationConfig.wecom.enabled">
                <el-form-item label="机器人名称">
                  <el-input 
                    v-model="settings.notificationConfig.wecom.name" 
                    placeholder="请输入企业微信机器人名称"
                    style="width: 400px;"
                  />
                </el-form-item>
                <el-form-item label="企业微信ID">
                  <el-input 
                    v-model="settings.notificationConfig.wecom.corpId" 
                    placeholder="请输入企业微信ID"
                    style="width: 400px;"
                  />
                </el-form-item>
                <el-form-item label="应用密钥">
                  <el-input 
                    v-model="settings.notificationConfig.wecom.appSecret" 
                    :type="settings.notificationConfig.wecom.showSecret ? 'text' : 'password'"
                    placeholder="请输入企业微信应用密钥"
                    style="width: 400px;"
                  >
                    <template #append>
                      <el-checkbox v-model="settings.notificationConfig.wecom.showSecret">
                        显示明文
                      </el-checkbox>
                    </template>
                  </el-input>
                </el-form-item>
              </template>
            </el-card>
            
            <!-- 邮箱通知配置 -->
            <el-divider content-position="left">
              <span style="font-weight: 600;">邮箱通知配置</span>
            </el-divider>
            <el-card shadow="never" style="margin-bottom: 20px; background-color: #fafafa;">
              <el-form-item label="启用邮箱通知">
                <el-switch v-model="settings.notificationConfig.email.enabled" />
              </el-form-item>
              <template v-if="settings.notificationConfig.email.enabled">
                <el-form-item label="邮箱地址">
                  <el-input 
                    v-model="settings.notificationConfig.email.address" 
                    placeholder="请输入邮箱地址"
                    style="width: 400px;"
                  />
                </el-form-item>
                <el-form-item label="SMTP服务器">
                  <el-input 
                    v-model="settings.notificationConfig.email.smtpServer" 
                    placeholder="请输入SMTP服务器"
                    style="width: 400px;"
                  />
                </el-form-item>
              </template>
            </el-card>
            
            <el-form-item>
              <el-button type="primary" @click="saveSettings">保存设置</el-button>
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
                <el-table-column prop="direction" label="买卖方向" width="90">
                  <template #default="scope">
                    <el-tag :type="scope.row.direction === '多' ? 'danger' : 'success'">
                      {{ scope.row.direction }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="volume" label="持仓量" width="80" />
                <el-table-column prop="holdPrice" label="开仓均价" width="100">
                  <template #default="scope">
                    {{ scope.row.holdPrice.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="latestPrice" label="当前价格" width="100">
                  <template #default="scope">
                    {{ scope.row.latestPrice.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="profitLoss" label="浮动盈亏" width="100">
                  <template #default="scope">
                    <span :style="{ color: scope.row.profitLoss > 0 ? '#F56C6C' : scope.row.profitLoss < 0 ? '#67C23A' : '#000000' }">
                      {{ scope.row.profitLoss > 0 ? '+' : '' }}{{ scope.row.profitLoss.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="returnRate" label="持仓盈亏比例" width="120">
                  <template #default="scope">
                    <span :style="{ color: scope.row.returnRate > 0 ? '#F56C6C' : scope.row.returnRate < 0 ? '#67C23A' : '#000000' }">
                      {{ scope.row.returnRate > 0 ? '+' : '' }}{{ scope.row.returnRate.toFixed(2) }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="margin" label="保证金占用" width="120">
                  <template #default="scope">
                    {{ scope.row.margin.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="takeProfitPrice" label="止盈价" width="100">
                  <template #default="scope">
                    {{ scope.row.takeProfitPrice.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="stopLossPrice" label="止损价" width="100">
                  <template #default="scope">
                    {{ scope.row.stopLossPrice.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="280" fixed="right">
                  <template #default="scope">
                    <el-button size="small" type="danger" @click="handleClosePosition(scope.row)">
                      一键平仓
                    </el-button>
                    <el-button size="small" type="warning" @click="handlePartialClose(scope.row)">
                      部分平仓
                    </el-button>
                    <el-button size="small" type="primary" @click="handleReversePosition(scope.row)">
                      反手开仓
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <!-- 3. 委托列表 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <span class="section-title">委托列表</span>
              </template>
              <el-table :data="currentStrategy.orders" border stripe>
                <el-table-column prop="orderTime" label="委托时间" width="160" />
                <el-table-column prop="contract" label="合约代码" width="100" />
                <el-table-column prop="direction" label="买卖方向" width="80">
                  <template #default="scope">
                    <el-tag :type="scope.row.direction === '买' ? 'danger' : 'success'">
                      {{ scope.row.direction }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="offset" label="开平仓" width="80">
                  <template #default="scope">
                    <el-tag :type="scope.row.offset === '开仓' ? 'warning' : 'info'">
                      {{ scope.row.offset }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="orderPrice" label="委托价格" width="100">
                  <template #default="scope">
                    {{ scope.row.orderPrice.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="orderVolume" label="委托数量" width="80" />
                <el-table-column prop="filledVolume" label="已成交数量" width="100" />
                <el-table-column prop="status" label="委托状态" width="100">
                  <template #default="scope">
                    <el-tag :type="orderStatusMap[scope.row.status].color">
                      {{ orderStatusMap[scope.row.status].name }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="orderType" label="委托类型" width="100">
                  <template #default="scope">
                    <el-tag :type="orderTypeMap[scope.row.orderType].color">
                      {{ orderTypeMap[scope.row.orderType].name }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="180" fixed="right">
                  <template #default="scope">
                    <el-button 
                      v-if="scope.row.status === 'submitted' || scope.row.status === 'partiallyFilled'"
                      size="small" 
                      type="warning"
                      @click="handleCancelOrder(scope.row)"
                    >
                      撤单
                    </el-button>
                    <el-button 
                      v-if="scope.row.status === 'submitted' || scope.row.status === 'partiallyFilled'"
                      size="small" 
                      type="primary"
                      @click="handleModifyOrder(scope.row)"
                    >
                      修改
                    </el-button>
                    <span v-if="scope.row.status === 'filled' || scope.row.status === 'cancelled' || scope.row.status === 'rejected'">
                      -
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <!-- 4. 成交明细 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <span class="section-title">成交明细</span>
              </template>
              <el-table :data="currentStrategy.trades" border stripe>
                <el-table-column prop="tradeTime" label="成交时间" width="160" />
                <el-table-column prop="contract" label="合约代码" width="100" />
                <el-table-column prop="direction" label="买卖方向" width="80">
                  <template #default="scope">
                    <el-tag :type="scope.row.direction === '买' ? 'danger' : 'success'">
                      {{ scope.row.direction }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="offset" label="开平仓" width="80">
                  <template #default="scope">
                    <el-tag :type="scope.row.offset === '开仓' ? 'warning' : 'info'">
                      {{ scope.row.offset }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="tradePrice" label="成交价格" width="100">
                  <template #default="scope">
                    {{ scope.row.tradePrice.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="tradeVolume" label="成交数量" width="80" />
                <el-table-column prop="tradeId" label="成交编号" width="180" />
                <el-table-column prop="commission" label="手续费" width="100">
                  <template #default="scope">
                    {{ scope.row.commission.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="tradeType" label="成交类型" width="120">
                  <template #default="scope">
                    <el-tag :type="tradeTypeMap[scope.row.tradeType].color">
                      {{ tradeTypeMap[scope.row.tradeType].name }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <!-- 5. 风险控制 -->
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

            <!-- 6. 风险控制参数配置 -->
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

        <!-- 添加策略对话框 -->
        <el-dialog
          v-model="addStrategyDialogVisible"
          title="选择要添加的策略"
          width="80%"
          :close-on-click-modal="false"
        >
          <el-row :gutter="20">
            <el-col :span="24" v-for="template in strategyTemplates" :key="template.fileName" style="margin-bottom: 20px;">
              <el-card class="strategy-card" shadow="hover">
                <!-- 文件名 -->
                <div class="strategy-file-name">
                  <el-icon :size="18" color="#409eff"><Document /></el-icon>
                  <span style="margin-left: 8px; font-family: 'Courier New', monospace; color: #606266;">{{ template.fileName }}</span>
                </div>
                
                <!-- 策略名称 -->
                <h3 style="margin: 15px 0 10px 0; font-size: 18px; color: #303133;">{{ template.name }}</h3>
                
                <!-- 策略描述 -->
                <p class="strategy-description">{{ template.description }}</p>
                
                <!-- 默认参数预览 -->
                <div class="strategy-params">
                  <el-tag size="small" style="margin-right: 8px;">最大仓位: {{ template.defaultRiskControl.maxPosition }}</el-tag>
                  <el-tag size="small" type="warning" style="margin-right: 8px;">止损: {{ template.defaultRiskControl.stopLossRatio }}%</el-tag>
                  <el-tag size="small" type="success" style="margin-right: 8px;">止盈: {{ template.defaultRiskControl.takeProfitRatio }}%</el-tag>
                  <el-tag size="small" type="info">回撤: {{ template.defaultRiskControl.maxDrawdown }}%</el-tag>
                </div>
                
                <!-- 添加按钮 -->
                <el-button type="primary" style="width: 100%; margin-top: 15px;" @click="handleAddStrategy(template)">
                  <el-icon style="margin-right: 5px;"><Plus /></el-icon>
                  添加此策略
                </el-button>
              </el-card>
            </el-col>
          </el-row>
        </el-dialog>

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
  InfoFilled,
  Bell,
  Wallet,
  Money,
  Lock,
  TrendCharts,
  DataLine,
  Coin,
  Operation,
  Warning,
  Plus,
  Timer,
  Delete,
  Edit
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getSystemStats } from '@/api/monitor'
// Mock 数据导入
import {
  strategyTemplates,
  strategyLogsData,
  scheduledTasksData,
  notificationsData,
  consoleLogsData,
  strategiesData,
  dashboardData as dashboardDataImport
} from '@/mock'
// 常量导入
import { logLevelMap, taskTypeMap, weekDayMap, orderStatusMap, orderTypeMap, tradeTypeMap } from '@/constants'
// 工具函数导入
import {
  getCurrentTime,
  getRelativeTime,
  calculateNextRunTime,
  formatTaskConfig,
  generateTaskId,
  generateStrategyId,
  getTotalProfitLoss,
  getRiskLevelType,
  getNotificationTagType,
  addLog
} from '@/utils'
// Composables 导入
import {
  useSystemMonitor,
  useStrategyManagement,
  useNotifications
} from '@/composables'
// 组件导入
import Console from '@/components/Console.vue'
import TaskScheduler from '@/components/TaskScheduler.vue'

const router = useRouter()
const userStore = useUserStore()

const activeMenu = ref('dashboard')

// ===== 使用 Composables =====
const {
  systemInfo,
  startMonitoring,
  stopMonitoring
} = useSystemMonitor()

const {
  strategies,
  strategyLogs,
  selectedLogLevel,
  detailDrawerVisible,
  currentStrategy,
  addStrategyDialogVisible,
  editableParameters,
  activeStrategiesCount,
  runningStrategiesCount,
  stoppedStrategiesCount,
  filteredStrategyLogs,
  handleAddStrategy,
  handleStartStrategy,
  handleStopStrategy,
  handleDeleteStrategy,
  handleShowDetail,
  handleSaveParameters,
  handleCancelEdit
} = useStrategyManagement()

const {
  notifications,
  unreadCount,
  markAsRead,
  markAllAsRead
} = useNotifications()

// 使用导入的仪表盘数据初始化
const dashboardData = reactive(dashboardDataImport)

// 今日日期显示
const todayDate = computed(() => {
  const date = new Date()
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
})

const settings = reactive({
  systemName: 'Homalos',
  autoStart: true,
  logLevel: 'info',
  notificationConfig: {
    dingtalk: {
      enabled: false,        // 独立启用开关
      name: '',              // 钉钉机器人名称
      id: '',                // 钉钉机器人ID
      webhookUrl: ''         // 钉钉Webhook地址
    },
    wecom: {
      enabled: false,        // 独立启用开关
      name: '',              // 企业微信机器人名称
      corpId: '',            // 企业微信ID
      appSecret: '',         // 应用密钥
      showSecret: false      // 是否显示密钥明文
    },
    email: {
      enabled: false,        // 独立启用开关
      address: '',           // 邮箱地址
      smtpServer: ''         // SMTP服务器
    }
  }
})


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
 * 控制台图标点击
 */
const handleConsoleClick = () => {
  activeMenu.value = 'console'
}

/**
 * 保存系统设置
 */
const saveSettings = () => {
  // 验证已启用的通知方式是否都已配置
  const errors = []
  
  // 钉钉配置验证
  if (settings.notificationConfig.dingtalk.enabled) {
    if (!settings.notificationConfig.dingtalk.name) {
      errors.push('钉钉机器人名称')
    }
    if (!settings.notificationConfig.dingtalk.id) {
      errors.push('钉钉机器人ID')
    }
    if (!settings.notificationConfig.dingtalk.webhookUrl) {
      errors.push('钉钉Webhook地址')
    }
  }
  
  // 企业微信配置验证
  if (settings.notificationConfig.wecom.enabled) {
    if (!settings.notificationConfig.wecom.name) {
      errors.push('企业微信机器人名称')
    }
    if (!settings.notificationConfig.wecom.corpId) {
      errors.push('企业微信ID')
    }
    if (!settings.notificationConfig.wecom.appSecret) {
      errors.push('企业微信应用密钥')
    }
  }
  
  // 邮箱配置验证
  if (settings.notificationConfig.email.enabled) {
    if (!settings.notificationConfig.email.address) {
      errors.push('邮箱地址')
    }
    if (!settings.notificationConfig.email.smtpServer) {
      errors.push('SMTP服务器')
    }
  }
  
  // 如果有未填写的配置，显示警告
  if (errors.length > 0) {
    ElMessage.warning(`请填写以下配置项：${errors.join('、')}`)
    return
  }
  
  // TODO: 这里应该调用API保存配置到后端
  console.log('保存系统设置:', settings)
  
  ElMessage.success('系统设置保存成功')
}

/**
 * 撤单处理
 */
const handleCancelOrder = (order) => {
  ElMessageBox.confirm(
    `确认撤销委托？合约：${order.contract}，方向：${order.direction}，数量：${order.orderVolume}`,
    '撤单确认',
    {
      confirmButtonText: '确认撤单',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // TODO: 调用API撤销委托
    console.log('撤销委托:', order)
    ElMessage.success('委托已撤销')
    
    // 更新委托状态为已撤单
    order.status = 'cancelled'
  }).catch(() => {
    ElMessage.info('已取消操作')
  })
}

/**
 * 修改委托处理
 */
const handleModifyOrder = (order) => {
  ElMessageBox.prompt(
    `当前委托价格：${order.orderPrice}，委托数量：${order.orderVolume}`,
    '修改委托',
    {
      confirmButtonText: '确认修改',
      cancelButtonText: '取消',
      inputPattern: /^\d+(\.\d+)?$/,
      inputErrorMessage: '请输入有效的数字',
      inputPlaceholder: '请输入新的委托价格'
    }
  ).then(({ value }) => {
    // TODO: 调用API修改委托
    console.log('修改委托:', order, '新价格:', value)
    ElMessage.success(`委托价格已修改为 ${value}`)
    
    // 更新委托价格
    order.orderPrice = parseFloat(value)
  }).catch(() => {
    ElMessage.info('已取消操作')
  })
}

/**
 * 一键平仓处理
 */
const handleClosePosition = (position) => {
  ElMessageBox.confirm(
    `确认平仓？\n合约：${position.contract}\n方向：${position.direction}\n持仓量：${position.volume} 手\n当前价格：${position.latestPrice.toFixed(2)}\n预计盈亏：${position.profitLoss > 0 ? '+' : ''}${position.profitLoss.toFixed(2)}`,
    '一键平仓确认',
    {
      confirmButtonText: '确认平仓',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: false
    }
  ).then(() => {
    // TODO: 调用API执行平仓操作
    console.log('一键平仓:', position)
    ElMessage.success('平仓指令已提交')
    
    // 模拟平仓后移除持仓
    // 实际应用中应该等待后端返回确认
  }).catch(() => {
    ElMessage.info('已取消平仓操作')
  })
}

/**
 * 部分平仓处理
 */
const handlePartialClose = (position) => {
  ElMessageBox.prompt(
    `当前持仓量：${position.volume} 手\n请输入平仓数量（1-${position.volume}）`,
    '部分平仓',
    {
      confirmButtonText: '确认平仓',
      cancelButtonText: '取消',
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入有效的整数',
      inputPlaceholder: '请输入平仓数量',
      inputValidator: (value) => {
        const num = parseInt(value)
        if (num < 1 || num > position.volume) {
          return `平仓数量必须在 1 到 ${position.volume} 之间`
        }
        return true
      }
    }
  ).then(({ value }) => {
    // TODO: 调用API执行部分平仓操作
    console.log('部分平仓:', position, '数量:', value)
    ElMessage.success(`已提交平仓 ${value} 手的指令`)
    
    // 模拟部分平仓后更新持仓量
    // 实际应用中应该等待后端返回确认
  }).catch(() => {
    ElMessage.info('已取消平仓操作')
  })
}

/**
 * 反手开仓处理
 */
const handleReversePosition = (position) => {
  const reverseDirection = position.direction === '多' ? '空' : '多'
  ElMessageBox.confirm(
    `确认反手开仓？\n当前持仓：${position.contract} ${position.direction} ${position.volume} 手\n操作说明：\n1. 平掉当前 ${position.direction} 仓 ${position.volume} 手\n2. 开立 ${reverseDirection} 仓 ${position.volume} 手`,
    '反手开仓确认',
    {
      confirmButtonText: '确认反手',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: false
    }
  ).then(() => {
    // TODO: 调用API执行反手操作
    console.log('反手开仓:', position, '新方向:', reverseDirection)
    ElMessage.success('反手操作指令已提交')
    
    // 模拟反手后更新持仓方向
    // 实际应用中应该等待后端返回确认
  }).catch(() => {
    ElMessage.info('已取消反手操作')
  })
}

// ===== 所有业务逻辑已提取到 Composables =====
// 策略管理逻辑 -> useStrategyManagement.js
// 任务调度逻辑 -> useTaskScheduler.js
// 通知管理逻辑 -> useNotifications.js
// 控制台逻辑 -> useConsole.js
// 系统监控逻辑 -> useSystemMonitor.js


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

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  background-color: #f5f7fa;
  border-radius: 4px;
  text-align: center;
}

.strategy-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.strategy-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.strategy-file-name {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 10px;
}

.strategy-description {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  margin: 10px 0;
  min-height: 44px;
}

.strategy-params {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}
</style>

