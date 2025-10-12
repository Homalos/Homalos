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
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

