/**
 * 通知管理逻辑 Composable
 */
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { notificationsData } from '@/mock'
import { getNotificationTagType } from '@/utils'

export function useNotifications() {
  // ===== 状态管理 =====
  const notifications = ref(notificationsData)

  // ===== 计算属性 =====
  const unreadCount = computed(() => {
    return notifications.value.filter(n => !n.isRead).length
  })

  // ===== 方法 =====
  
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

  return {
    // 状态
    notifications,
    
    // 计算属性
    unreadCount,
    
    // 方法
    markAsRead,
    markAllAsRead,
    getNotificationTagType
  }
}

