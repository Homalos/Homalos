/**
 * 系统设置逻辑 Composable
 */
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

export function useSettings() {
  // ===== 状态管理 =====
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

  // ===== 方法 =====
  
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
   * 重置系统设置
   */
  const resetSettings = () => {
    settings.systemName = 'Homalos'
    settings.autoStart = true
    settings.logLevel = 'info'
    settings.notificationMethods = ['dingtalk', 'email']
    settings.notificationConfig = {
      dingtalk: { id: '' },
      wecom: { id: '' },
      email: { address: '', smtpServer: '' }
    }
    ElMessage.info('设置已重置')
  }

  return {
    // 状态
    settings,
    
    // 方法
    saveSettings,
    resetSettings
  }
}

