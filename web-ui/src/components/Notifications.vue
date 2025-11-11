<template>
  <el-card shadow="hover">
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
</template>

<script setup>
import { getNotificationTagType } from '@/utils'
import { useNotifications } from '@/composables'

const {
  notifications,
  unreadCount,
  markAsRead,
  markAllAsRead
} = useNotifications()
</script>

<style scoped>
/* 全局卡片优化 - 与所有页面风格一致 */
:deep(.el-card),
.el-card {
  border-radius: 12px !important;
  border: 1px solid rgba(64, 158, 255, 0.08) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  overflow: hidden !important;
}

:deep(.el-card__header),
.el-card__header {
  border-radius: 12px 12px 0 0 !important;
}

:deep(.el-card__body),
.el-card__body {
  border-radius: 0 0 12px 12px !important;
}

:deep(.el-card.is-hover-shadow:hover),
:deep(.el-card.is-always-shadow),
.el-card.is-hover-shadow:hover,
.el-card.is-always-shadow {
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.12) !important;
}

/* 卡片header优化 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.card-header span {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  position: relative;
  padding-left: 12px;
}

/* header左侧渐变装饰条 */
.card-header span::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 18px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 2px;
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

/* Timeline中的通知项卡片优化 */
.notification-item {
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  margin-bottom: 0;
  border-radius: 10px !important;
  overflow: hidden;
}

.notification-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.18) !important;
  border-color: #409eff;
}

.notification-item.unread {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.08) 0%, rgba(64, 158, 255, 0.05) 100%);
  border-left: 4px solid #409eff;
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
  background: linear-gradient(135deg, #409eff 0%, #53a8ff 100%);
  border-radius: 50%;
  margin-right: 6px;
  box-shadow: 0 0 4px rgba(64, 158, 255, 0.6);
  animation: dotPulse 2s ease-in-out infinite;
}

@keyframes dotPulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
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
  border-top: 2px solid rgba(64, 158, 255, 0.08);
}

.notification-time {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}

/* 按钮渐变优化 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45) !important;
}

:deep(.el-button--text) {
  color: #409eff;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-button--text:hover) {
  color: #53a8ff;
  background: rgba(64, 158, 255, 0.08);
}

/* Tag美化 */
:deep(.el-tag) {
  border-radius: 6px;
  padding: 6px 12px;
  font-weight: 500;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-tag:hover) {
  transform: translateY(-1px);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.12);
}

:deep(.el-tag--success) {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%);
  color: #ffffff;
}

:deep(.el-tag--warning) {
  background: linear-gradient(135deg, #e6a23c 0%, #cf9236 100%);
  color: #ffffff;
}

:deep(.el-tag--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #dd5a5a 100%);
  color: #ffffff;
}

:deep(.el-tag--info) {
  background: linear-gradient(135deg, rgba(144, 147, 153, 0.9) 0%, rgba(144, 147, 153, 0.8) 100%);
  color: #ffffff;
}
</style>

