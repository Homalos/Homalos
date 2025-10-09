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
                    <span>今日表现</span>
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
        <div v-if="activeMenu === 'console'">
          <!-- 1. 系统控制 -->
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <!-- 量化交易系统 -->
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>量化交易系统</span>
                    <el-tag :type="consoleData.tradingSystem.status === 'running' ? 'success' : 'info'">
                      {{ consoleData.tradingSystem.status === 'running' ? '运行中' : '已停止' }}
                    </el-tag>
                  </div>
                </template>
                <div style="padding: 20px 0;">
                  <el-row :gutter="20" style="margin-bottom: 20px;">
                    <el-col :span="12">
                      <el-statistic title="系统状态">
                        <template #prefix>
                          <el-icon :color="consoleData.tradingSystem.status === 'running' ? '#67C23A' : '#909399'">
                            <SuccessFilled v-if="consoleData.tradingSystem.status === 'running'" />
                            <VideoPause v-else />
                          </el-icon>
                        </template>
                        <template #formatter>
                          {{ consoleData.tradingSystem.status === 'running' ? '运行中' : '已停止' }}
                        </template>
                      </el-statistic>
                    </el-col>
                    <el-col :span="12">
                      <el-statistic title="运行时长" :value="consoleData.tradingSystem.runningTime">
                        <template #prefix>
                          <el-icon color="#409EFF"><Clock /></el-icon>
                        </template>
                      </el-statistic>
                    </el-col>
                  </el-row>
                  <el-row :gutter="10">
                    <el-col :span="12">
                      <el-button 
                        type="success" 
                        style="width: 100%;"
                        :disabled="consoleData.tradingSystem.status === 'running'"
                        @click="handleStartTradingSystem"
                      >
                        <el-icon><VideoPlay /></el-icon>
                        启动系统
                      </el-button>
                    </el-col>
                    <el-col :span="12">
                      <el-button 
                        type="danger" 
                        style="width: 100%;"
                        :disabled="consoleData.tradingSystem.status === 'stopped'"
                        @click="handleStopTradingSystem"
                      >
                        <el-icon><VideoPause /></el-icon>
                        停止系统
                      </el-button>
                    </el-col>
                  </el-row>
                </div>
              </el-card>
            </el-col>

            <!-- 数据中心 -->
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>数据中心</span>
                    <el-tag :type="consoleData.dataCenter.status === 'running' ? 'success' : 'info'">
                      {{ consoleData.dataCenter.status === 'running' ? '运行中' : '已停止' }}
                    </el-tag>
                  </div>
                </template>
                <div style="padding: 20px 0;">
                  <el-row :gutter="20" style="margin-bottom: 20px;">
                    <el-col :span="12">
                      <el-statistic title="系统状态">
                        <template #prefix>
                          <el-icon :color="consoleData.dataCenter.status === 'running' ? '#67C23A' : '#909399'">
                            <SuccessFilled v-if="consoleData.dataCenter.status === 'running'" />
                            <VideoPause v-else />
                          </el-icon>
                        </template>
                        <template #formatter>
                          {{ consoleData.dataCenter.status === 'running' ? '运行中' : '已停止' }}
                        </template>
                      </el-statistic>
                    </el-col>
                    <el-col :span="12">
                      <el-statistic title="运行时长" :value="consoleData.dataCenter.runningTime">
                        <template #prefix>
                          <el-icon color="#409EFF"><Clock /></el-icon>
                        </template>
                      </el-statistic>
                    </el-col>
                  </el-row>
                  <el-row :gutter="10">
                    <el-col :span="12">
                      <el-button 
                        type="success" 
                        style="width: 100%;"
                        :disabled="consoleData.dataCenter.status === 'running'"
                        @click="handleStartDataCenter"
                      >
                        <el-icon><VideoPlay /></el-icon>
                        启动数据中心
                      </el-button>
                    </el-col>
                    <el-col :span="12">
                      <el-button 
                        type="danger" 
                        style="width: 100%;"
                        :disabled="consoleData.dataCenter.status === 'stopped'"
                        @click="handleStopDataCenter"
                      >
                        <el-icon><VideoPause /></el-icon>
                        停止数据中心
                      </el-button>
                    </el-col>
                  </el-row>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 2. 控制台日志 -->
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>控制台日志</span>
                <el-select 
                  v-model="selectedConsoleLogLevel" 
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
              <el-timeline v-if="filteredConsoleLogs.length > 0">
                <el-timeline-item 
                  v-for="log in filteredConsoleLogs" 
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
        </div>

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
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status === '运行中' ? 'success' : 'info'">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="startTime" label="启动时间" width="180" />
            <el-table-column prop="runningTime" label="运行时长" width="120" />
            <el-table-column label="交易次数" width="100">
              <template #default="scope">
                {{ scope.row.positions.length }}
              </template>
            </el-table-column>
            <el-table-column label="盈亏" width="120">
              <template #default="scope">
                <span :style="{ color: getTotalProfitLoss(scope.row) > 0 ? '#F56C6C' : getTotalProfitLoss(scope.row) < 0 ? '#67C23A' : '#000000' }">
                  {{ getTotalProfitLoss(scope.row) > 0 ? '+' : '' }}{{ getTotalProfitLoss(scope.row).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
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

        <!-- 任务调度器面板 -->
        <el-card v-if="activeMenu === 'task-scheduler'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>任务调度器</span>
              <el-button type="primary" size="small" @click="addTaskDialogVisible = true">
                <el-icon style="margin-right: 5px;"><Plus /></el-icon>
                添加任务
              </el-button>
            </div>
          </template>
          
          <!-- 任务统计 -->
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="8">
              <el-statistic title="总任务数" :value="totalTasksCount">
                <template #prefix>
                  <el-icon color="#409eff"><Timer /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="已启用" :value="enabledTasksCount">
                <template #prefix>
                  <el-icon color="#67C23A"><VideoPlay /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="已禁用" :value="disabledTasksCount">
                <template #prefix>
                  <el-icon color="#909399"><VideoPause /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
          
          <!-- 任务列表表格 -->
          <el-table :data="scheduledTasks" stripe style="width: 100%">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="任务名称" width="150" />
            <el-table-column label="任务类型" width="120">
              <template #default="{ row }">
                <el-tag :color="taskTypeMap[row.type].color" style="color: white;">
                  {{ taskTypeMap[row.type].name }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="执行配置" width="200">
              <template #default="{ row }">
                {{ formatTaskConfig(row) }}
              </template>
            </el-table-column>
            <el-table-column label="下次执行" width="180">
              <template #default="{ row }">
                {{ getRelativeTime(calculateNextRunTime(row)) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'enabled' ? 'success' : 'info'">
                  {{ row.status === 'enabled' ? '已启用' : '已禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="300">
              <template #default="{ row }">
                <el-button 
                  size="small" 
                  :type="row.status === 'enabled' ? 'warning' : 'success'"
                  @click="handleToggleTaskStatus(row)"
                >
                  {{ row.status === 'enabled' ? '禁用' : '启用' }}
                </el-button>
                <el-button size="small" @click="handleEditTask(row)">
                  <el-icon style="margin-right: 3px;"><Edit /></el-icon>
                  编辑
                </el-button>
                <el-button size="small" @click="handleShowHistory(row)">
                  <el-icon style="margin-right: 3px;"><Clock /></el-icon>
                  历史
                </el-button>
                <el-button size="small" type="danger" @click="handleDeleteTask(row.id)">
                  <el-icon style="margin-right: 3px;"><Delete /></el-icon>
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
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
                <div style="margin-bottom: 15px;">
                  <el-checkbox label="dingtalk">钉钉</el-checkbox>
                  <!-- 钉钉配置展开区域 -->
                  <div v-if="settings.notificationMethods.includes('dingtalk')" style="margin-left: 24px; margin-top: 10px;">
                    <el-input 
                      v-model="settings.notificationConfig.dingtalk.id" 
                      placeholder="请输入钉钉机器人ID"
                      style="width: 400px;"
                    />
                  </div>
                </div>
                
                <div style="margin-bottom: 15px;">
                  <el-checkbox label="wecom">企业微信</el-checkbox>
                  <!-- 企业微信配置展开区域 -->
                  <div v-if="settings.notificationMethods.includes('wecom')" style="margin-left: 24px; margin-top: 10px;">
                    <el-input 
                      v-model="settings.notificationConfig.wecom.id" 
                      placeholder="请输入企业微信机器人ID"
                      style="width: 400px;"
                    />
                  </div>
                </div>
                
                <div>
                  <el-checkbox label="email">邮箱</el-checkbox>
                  <!-- 邮箱配置展开区域 -->
                  <div v-if="settings.notificationMethods.includes('email')" style="margin-left: 24px; margin-top: 10px;">
                    <div style="margin-bottom: 10px;">
                      <el-input 
                        v-model="settings.notificationConfig.email.address" 
                        placeholder="请输入邮箱地址"
                        style="width: 400px;"
                      />
                    </div>
                    <div>
                      <el-input 
                        v-model="settings.notificationConfig.email.smtpServer" 
                        placeholder="请输入SMTP服务器"
                        style="width: 400px;"
                      />
                    </div>
                  </div>
                </div>
              </el-checkbox-group>
            </el-form-item>
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
                <el-table-column prop="volume" label="持仓量" width="80" />
                <el-table-column prop="direction" label="方向" width="60">
                  <template #default="scope">
                    <el-tag :type="scope.row.direction === '多' ? 'danger' : 'success'">
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
                    <span :style="{ color: scope.row.profitLoss > 0 ? '#F56C6C' : scope.row.profitLoss < 0 ? '#67C23A' : '#000000' }">
                      {{ scope.row.profitLoss > 0 ? '+' : '' }}{{ scope.row.profitLoss.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="returnRate" label="收益率" width="100">
                  <template #default="scope">
                    <span :style="{ color: scope.row.returnRate > 0 ? '#F56C6C' : scope.row.returnRate < 0 ? '#67C23A' : '#000000' }">
                      {{ scope.row.returnRate > 0 ? '+' : '' }}{{ scope.row.returnRate.toFixed(2) }}%
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

        <!-- 添加/编辑任务对话框 -->
        <el-dialog 
          v-model="addTaskDialogVisible" 
          title="添加任务" 
          width="600px"
          :close-on-click-modal="false"
        >
          <el-form :model="newTaskForm" label-width="120px">
            <el-form-item label="任务名称" required>
              <el-input v-model="newTaskForm.name" placeholder="请输入任务名称" />
            </el-form-item>
            
            <el-form-item label="任务类型" required>
              <el-select v-model="newTaskForm.type" style="width: 100%;">
                <el-option label="每日任务" value="daily" />
                <el-option label="一次性任务" value="once" />
                <el-option label="每分钟任务" value="minute" />
                <el-option label="每周任务" value="weekday" />
                <el-option label="每月任务" value="monthly" />
              </el-select>
            </el-form-item>
            
            <!-- 每日任务配置 -->
            <el-form-item v-if="newTaskForm.type === 'daily'" label="执行时间" required>
              <el-time-picker 
                v-model="newTaskForm.config.time" 
                format="HH:mm" 
                value-format="HH:mm"
                placeholder="选择时间"
              />
            </el-form-item>
            
            <!-- 一次性任务配置 -->
            <el-form-item v-if="newTaskForm.type === 'once'" label="执行时间" required>
              <el-date-picker 
                v-model="newTaskForm.config.dateTime" 
                type="datetime" 
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm:00"
                placeholder="选择日期时间"
              />
            </el-form-item>
            
            <!-- 每周任务配置 -->
            <template v-if="newTaskForm.type === 'weekday'">
              <el-form-item label="执行时间" required>
                <el-time-picker 
                  v-model="newTaskForm.config.time" 
                  format="HH:mm" 
                  value-format="HH:mm"
                  placeholder="选择时间"
                />
              </el-form-item>
              <el-form-item label="星期" required>
                <el-checkbox-group v-model="newTaskForm.config.dayOfWeek">
                  <el-checkbox label="周一" />
                  <el-checkbox label="周二" />
                  <el-checkbox label="周三" />
                  <el-checkbox label="周四" />
                  <el-checkbox label="周五" />
                  <el-checkbox label="周六" />
                  <el-checkbox label="周日" />
                </el-checkbox-group>
              </el-form-item>
            </template>
            
            <!-- 每月任务配置 -->
            <template v-if="newTaskForm.type === 'monthly'">
              <el-form-item label="执行时间" required>
                <el-time-picker 
                  v-model="newTaskForm.config.time" 
                  format="HH:mm" 
                  value-format="HH:mm"
                  placeholder="选择时间"
                />
              </el-form-item>
              <el-form-item label="日期" required>
                <el-select v-model="newTaskForm.config.monthDay" multiple placeholder="选择日期" style="width: 100%;">
                  <el-option v-for="day in 31" :key="day" 
                             :label="`${day}号`" 
                             :value="String(day).padStart(2, '0')" />
                </el-select>
              </el-form-item>
            </template>
            
            <el-form-item v-if="newTaskForm.type === 'minute'" label="说明">
              <el-alert 
                type="info" 
                :closable="false"
                show-icon
              >
                此任务将每分钟执行一次
              </el-alert>
            </el-form-item>
          </el-form>
          
          <template #footer>
            <el-button @click="addTaskDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleSaveTask">保存</el-button>
          </template>
        </el-dialog>

        <!-- 编辑任务对话框 -->
        <el-dialog 
          v-model="editTaskDialogVisible" 
          title="编辑任务" 
          width="600px"
          :close-on-click-modal="false"
        >
          <el-form :model="newTaskForm" label-width="120px">
            <el-form-item label="任务名称" required>
              <el-input v-model="newTaskForm.name" placeholder="请输入任务名称" />
            </el-form-item>
            
            <el-form-item label="任务类型" required>
              <el-select v-model="newTaskForm.type" style="width: 100%;">
                <el-option label="每日任务" value="daily" />
                <el-option label="一次性任务" value="once" />
                <el-option label="每分钟任务" value="minute" />
                <el-option label="每周任务" value="weekday" />
                <el-option label="每月任务" value="monthly" />
              </el-select>
            </el-form-item>
            
            <!-- 每日任务配置 -->
            <el-form-item v-if="newTaskForm.type === 'daily'" label="执行时间" required>
              <el-time-picker 
                v-model="newTaskForm.config.time" 
                format="HH:mm" 
                value-format="HH:mm"
                placeholder="选择时间"
              />
            </el-form-item>
            
            <!-- 一次性任务配置 -->
            <el-form-item v-if="newTaskForm.type === 'once'" label="执行时间" required>
              <el-date-picker 
                v-model="newTaskForm.config.dateTime" 
                type="datetime" 
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm:00"
                placeholder="选择日期时间"
              />
            </el-form-item>
            
            <!-- 每周任务配置 -->
            <template v-if="newTaskForm.type === 'weekday'">
              <el-form-item label="执行时间" required>
                <el-time-picker 
                  v-model="newTaskForm.config.time" 
                  format="HH:mm" 
                  value-format="HH:mm"
                  placeholder="选择时间"
                />
              </el-form-item>
              <el-form-item label="星期" required>
                <el-checkbox-group v-model="newTaskForm.config.dayOfWeek">
                  <el-checkbox label="周一" />
                  <el-checkbox label="周二" />
                  <el-checkbox label="周三" />
                  <el-checkbox label="周四" />
                  <el-checkbox label="周五" />
                  <el-checkbox label="周六" />
                  <el-checkbox label="周日" />
                </el-checkbox-group>
              </el-form-item>
            </template>
            
            <!-- 每月任务配置 -->
            <template v-if="newTaskForm.type === 'monthly'">
              <el-form-item label="执行时间" required>
                <el-time-picker 
                  v-model="newTaskForm.config.time" 
                  format="HH:mm" 
                  value-format="HH:mm"
                  placeholder="选择时间"
                />
              </el-form-item>
              <el-form-item label="日期" required>
                <el-select v-model="newTaskForm.config.monthDay" multiple placeholder="选择日期" style="width: 100%;">
                  <el-option v-for="day in 31" :key="day" 
                             :label="`${day}号`" 
                             :value="String(day).padStart(2, '0')" />
                </el-select>
              </el-form-item>
            </template>
            
            <el-form-item v-if="newTaskForm.type === 'minute'" label="说明">
              <el-alert 
                type="info" 
                :closable="false"
                show-icon
              >
                此任务将每分钟执行一次
              </el-alert>
            </el-form-item>
          </el-form>
          
          <template #footer>
            <el-button @click="editTaskDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleUpdateTask">保存</el-button>
          </template>
        </el-dialog>

        <!-- 执行历史对话框 -->
        <el-dialog 
          v-model="historyDialogVisible" 
          :title="`执行历史 - ${currentTask?.name}`" 
          width="700px"
        >
          <el-timeline v-if="currentTask?.executionHistory && currentTask.executionHistory.length > 0">
            <el-timeline-item 
              v-for="(record, index) in currentTask.executionHistory" 
              :key="index"
              :type="record.status === 'success' ? 'success' : 'danger'"
              :icon="record.status === 'success' ? SuccessFilled : Warning"
            >
              <el-card>
                <div style="margin-bottom: 8px;">
                  <strong style="font-size: 14px;">{{ record.time }}</strong>
                </div>
                <div style="margin-bottom: 5px;">
                  状态: 
                  <el-tag :type="record.status === 'success' ? 'success' : 'danger'" size="small">
                    {{ record.status === 'success' ? '成功' : '失败' }}
                  </el-tag>
                </div>
                <div style="margin-bottom: 5px;">耗时: <el-tag size="small">{{ record.duration }}</el-tag></div>
                <div v-if="record.error" style="color: #F56C6C; margin-top: 8px; padding: 8px; background-color: #FEF0F0; border-radius: 4px;">
                  <el-icon style="margin-right: 5px;"><Warning /></el-icon>
                  错误: {{ record.error }}
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无执行历史" />
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
  SuccessFilled,
  Cpu,
  Memo,
  InfoFilled,
  Bell,
  Wallet,
  Money,
  Lock,
  TrendCharts,
  DataLine,
  Coin,
  Operation,
  VideoPlay,
  VideoPause,
  Warning,
  Document,
  Plus,
  Timer,
  Clock,
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
import { logLevelMap, taskTypeMap, weekDayMap } from '@/constants'
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

const router = useRouter()
const userStore = useUserStore()

const activeMenu = ref('dashboard')

// 使用导入的策略日志数据初始化
const strategyLogs = ref(strategyLogsData)

// 当前选择的日志级别
const selectedLogLevel = ref('all')

// 使用导入的任务调度器数据初始化
const scheduledTasks = ref(scheduledTasksData)

// 使用导入的通知列表数据初始化
const notifications = ref(notificationsData)

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
  lastUpdate: null,
  loading: false,
  error: null
})

// 使用导入的仪表盘数据初始化
const dashboardData = reactive(dashboardDataImport)

// 控制台数据
const consoleData = reactive({
  tradingSystem: {
    status: 'stopped',  // running | stopped
    runningTime: '-'
  },
  dataCenter: {
    status: 'stopped',  // running | stopped
    runningTime: '-'
  }
})

// 使用导入的控制台日志数据初始化
const consoleLogs = ref(consoleLogsData)

// 当前选择的控制台日志级别
const selectedConsoleLogLevel = ref('all')

// 使用导入的策略数据初始化
const strategies = ref(strategiesData)

// 计算活跃策略数量（策略总数）
const activeStrategiesCount = computed(() => {
  return strategies.value.length
})

// 计算运行中的策略数量
const runningStrategiesCount = computed(() => {
  return strategies.value.filter(s => s.status === '运行中').length
})

// 计算已停止的策略数量
const stoppedStrategiesCount = computed(() => {
  return strategies.value.filter(s => s.status === '已停止').length
})

// 计算任务总数
const totalTasksCount = computed(() => scheduledTasks.value.length)

// 计算启用的任务数
const enabledTasksCount = computed(() => 
  scheduledTasks.value.filter(t => t.status === 'enabled').length
)

// 计算禁用的任务数
const disabledTasksCount = computed(() => 
  scheduledTasks.value.filter(t => t.status === 'disabled').length
)

// 过滤后的策略日志
const filteredStrategyLogs = computed(() => {
  if (selectedLogLevel.value === 'all') {
    return strategyLogs.value
  }
  return strategyLogs.value.filter(log => log.level === selectedLogLevel.value)
})

// 过滤后的控制台日志
const filteredConsoleLogs = computed(() => {
  if (selectedConsoleLogLevel.value === 'all') {
    return consoleLogs.value
  }
  return consoleLogs.value.filter(log => log.level === selectedConsoleLogLevel.value)
})

// 详情面板状态
const detailDrawerVisible = ref(false)
const currentStrategy = ref(null)

// 添加策略对话框状态
const addStrategyDialogVisible = ref(false)

// 任务调度器对话框状态
const addTaskDialogVisible = ref(false)
const editTaskDialogVisible = ref(false)
const historyDialogVisible = ref(false)
const currentTask = ref(null)

// 新任务表单数据
const newTaskForm = reactive({
  name: '',
  type: 'daily',
  config: {
    time: '09:00',
    dateTime: '',
    dayOfWeek: [],
    monthDay: []
  }
})
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
  notificationMethods: ['dingtalk', 'email'],  // 默认启用钉钉和邮箱
  notificationConfig: {
    dingtalk: {
      id: ''  // 钉钉机器人ID
    },
    wecom: {
      id: ''  // 企业微信机器人ID
    },
    email: {
      address: '',      // 邮箱地址
      smtpServer: ''   // SMTP服务器
    }
  }
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
 * 控制台图标点击
 */
const handleConsoleClick = () => {
  activeMenu.value = 'console'
}

/**
 * 添加控制台日志（包装函数）
 */
const addConsoleLog = (level, category, message, details = {}) => {
  addLog(consoleLogs, level, category, message, details, getCurrentTime)
}

/**
 * 启动量化交易系统
 */
const handleStartTradingSystem = () => {
  consoleData.tradingSystem.status = 'running'
  consoleData.tradingSystem.runningTime = '0m'
  
  // 添加日志
  addConsoleLog(
    'success',
    '系统启动',
    '量化交易系统启动成功',
    { component: 'tradingSystem' }
  )
  
  ElMessage.success('量化交易系统已启动')
}

/**
 * 停止量化交易系统
 */
const handleStopTradingSystem = () => {
  consoleData.tradingSystem.status = 'stopped'
  consoleData.tradingSystem.runningTime = '-'
  
  // 添加日志
  addConsoleLog(
    'warning',
    '系统停止',
    '量化交易系统已停止',
    { component: 'tradingSystem' }
  )
  
  ElMessage.warning('量化交易系统已停止')
}

/**
 * 启动数据中心
 */
const handleStartDataCenter = () => {
  consoleData.dataCenter.status = 'running'
  consoleData.dataCenter.runningTime = '0m'
  
  // 添加日志
  addConsoleLog(
    'success',
    '系统启动',
    '数据中心启动成功',
    { component: 'dataCenter' }
  )
  
  ElMessage.success('数据中心已启动')
}

/**
 * 停止数据中心
 */
const handleStopDataCenter = () => {
  consoleData.dataCenter.status = 'stopped'
  consoleData.dataCenter.runningTime = '-'
  
  // 添加日志
  addConsoleLog(
    'warning',
    '系统停止',
    '数据中心已停止',
    { component: 'dataCenter' }
  )
  
  ElMessage.warning('数据中心已停止')
}

/**
 * 启用/禁用任务
 */
const handleToggleTaskStatus = (task) => {
  task.status = task.status === 'enabled' ? 'disabled' : 'enabled'
  const statusText = task.status === 'enabled' ? '启用' : '禁用'
  ElMessage.success(`任务 "${task.name}" 已${statusText}`)
}

/**
 * 删除任务
 */
const handleDeleteTask = (taskId) => {
  ElMessageBox.confirm(
    '确定要删除这个任务吗？',
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    const index = scheduledTasks.value.findIndex(t => t.id === taskId)
    if (index !== -1) {
      const taskName = scheduledTasks.value[index].name
      scheduledTasks.value.splice(index, 1)
      ElMessage.success(`任务 "${taskName}" 已删除`)
    }
  }).catch(() => {
    // 用户取消删除
  })
}

/**
 * 显示执行历史
 */
const handleShowHistory = (task) => {
  currentTask.value = task
  historyDialogVisible.value = true
}

/**
 * 编辑任务
 */
const handleEditTask = (task) => {
  currentTask.value = task
  newTaskForm.name = task.name
  newTaskForm.type = task.type
  newTaskForm.config = { ...task.config }
  editTaskDialogVisible.value = true
}

/**
 * 保存新任务
 */
const handleSaveTask = () => {
  if (!newTaskForm.name.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  
  // 验证配置
  if (newTaskForm.type === 'daily' && !newTaskForm.config.time) {
    ElMessage.warning('请选择执行时间')
    return
  }
  if (newTaskForm.type === 'once' && !newTaskForm.config.dateTime) {
    ElMessage.warning('请选择执行时间')
    return
  }
  if (newTaskForm.type === 'weekday') {
    if (!newTaskForm.config.time || newTaskForm.config.dayOfWeek.length === 0) {
      ElMessage.warning('请选择执行时间和星期')
      return
    }
  }
  if (newTaskForm.type === 'monthly') {
    if (!newTaskForm.config.time || newTaskForm.config.monthDay.length === 0) {
      ElMessage.warning('请选择执行时间和日期')
      return
    }
  }
  
  const newTask = {
    id: generateTaskId(scheduledTasks.value),
    name: newTaskForm.name,
    type: newTaskForm.type,
    config: { ...newTaskForm.config },
    status: 'disabled',  // 默认禁用
    createTime: getCurrentTime(),
    lastExecuteTime: null,
    executionHistory: []
  }
  
  scheduledTasks.value.push(newTask)
  addTaskDialogVisible.value = false
  
  // 重置表单
  newTaskForm.name = ''
  newTaskForm.type = 'daily'
  newTaskForm.config = {
    time: '09:00',
    dateTime: '',
    dayOfWeek: [],
    monthDay: []
  }
  
  ElMessage.success(`任务 "${newTask.name}" 已添加`)
}

/**
 * 更新任务
 */
const handleUpdateTask = () => {
  if (!newTaskForm.name.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  
  const task = currentTask.value
  task.name = newTaskForm.name
  task.type = newTaskForm.type
  task.config = { ...newTaskForm.config }
  
  editTaskDialogVisible.value = false
  ElMessage.success(`任务 "${task.name}" 已更新`)
}

/**
 * 保存系统设置
 */
const saveSettings = () => {
  // 验证已启用的通知方式是否都已配置
  const errors = []
  
  if (settings.notificationMethods.includes('dingtalk')) {
    if (!settings.notificationConfig.dingtalk.id) {
      errors.push('钉钉机器人ID')
    }
  }
  
  if (settings.notificationMethods.includes('wecom')) {
    if (!settings.notificationConfig.wecom.id) {
      errors.push('企业微信机器人ID')
    }
  }
  
  if (settings.notificationMethods.includes('email')) {
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
 * 添加策略日志（包装函数）
 */
const addStrategyLog = (level, category, message, details = {}) => {
  addLog(strategyLogs, level, category, message, details, getCurrentTime)
}

/**
 * 添加策略到列表
 */
const handleAddStrategy = (template) => {
  const newStrategyId = generateStrategyId(strategies.value)
  const currentTime = getCurrentTime()
  
  const newStrategy = {
    // 基础字段
    id: newStrategyId,
    name: template.name,
    status: '已停止',
    startTime: '',
    runningTime: '-',
    
    // 基础信息
    description: template.description,
    author: template.author,
    createTime: currentTime,
    lastModifyTime: currentTime,
    
    // 持仓信息（空数组）
    positions: [],
    
    // 参数配置（简化版）
    parameters: {
      trading: {},
      risk: {},
      indicator: {}
    },
    
    // 风险控制（使用模板的默认值）
    riskControl: {
      maxPosition: template.defaultRiskControl.maxPosition,
      stopLossRatio: template.defaultRiskControl.stopLossRatio,
      takeProfitRatio: template.defaultRiskControl.takeProfitRatio,
      maxDrawdown: template.defaultRiskControl.maxDrawdown
    }
  }
  
  // 添加到策略列表
  strategies.value.push(newStrategy)
  
  // 添加日志
  addStrategyLog(
    'success',
    '添加策略',
    `成功添加策略 "${template.name}"`,
    { strategyId: newStrategyId, strategyName: template.name }
  )
  
  // 关闭对话框
  addStrategyDialogVisible.value = false
  
  // 显示成功提示
  ElMessage.success(`策略 "${template.name}" 已成功添加到列表`)
}

/**
 * 启动策略
 */
const handleStartStrategy = (strategy) => {
  strategy.status = '运行中'
  strategy.startTime = getCurrentTime()
  
  // 添加日志
  addStrategyLog(
    'success',
    '启动策略',
    `策略 "${strategy.name}" 已启动`,
    { strategyId: strategy.id, strategyName: strategy.name }
  )
  
  ElMessage.success(`策略 "${strategy.name}" 已启动`)
}

/**
 * 停止策略
 */
const handleStopStrategy = (strategy) => {
  strategy.status = '已停止'
  strategy.runningTime = '-'
  
  // 添加日志
  addStrategyLog(
    'warning',
    '停止策略',
    `策略 "${strategy.name}" 已停止`,
    { strategyId: strategy.id, strategyName: strategy.name }
  )
  
  ElMessage.success(`策略 "${strategy.name}" 已停止`)
}

/**
 * 删除策略
 */
const handleDeleteStrategy = (strategyId) => {
  ElMessageBox.confirm(
    '确定要删除这个策略吗？',
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    const index = strategies.value.findIndex(s => s.id === strategyId)
    if (index !== -1) {
      const strategy = strategies.value[index]
      strategies.value.splice(index, 1)
      
      // 添加日志
      addStrategyLog(
        'warning',
        '删除策略',
        `策略 "${strategy.name}" 已删除`,
        { strategyId: strategy.id, strategyName: strategy.name }
      )
      
      ElMessage.success(`策略 "${strategy.name}" 已删除`)
    }
  }).catch(() => {
    // 用户取消删除
  })
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
  
  // 添加日志
  addStrategyLog(
    'info',
    '参数配置',
    `策略 "${currentStrategy.value.name}" 风险控制参数已更新`,
    { 
      strategyId: currentStrategy.value.id, 
      strategyName: currentStrategy.value.name,
      maxPosition: editableParameters.riskControl.maxPosition,
      stopLossRatio: editableParameters.riskControl.stopLossRatio,
      takeProfitRatio: editableParameters.riskControl.takeProfitRatio,
      maxDrawdown: editableParameters.riskControl.maxDrawdown
    }
  )
  
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

/* 日志容器样式 */
.log-container {
  max-height: 400px;
  overflow-y: auto;
}

.log-item {
  display: flex;
  align-items: center;
}

.log-message {
  color: #606266;
  font-size: 14px;
}

</style>

