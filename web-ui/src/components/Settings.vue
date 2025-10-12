<template>
  <el-card shadow="hover">
    <template #header>
      <div class="card-header">
        <span>系统设置</span>
      </div>
    </template>
    <el-form label-width="140px">
      <!-- 基础设置 -->
      <el-divider content-position="left">
        <span style="font-weight: 600;">基础设置</span>
      </el-divider>
      <el-form-item label="开发模式">
        <el-switch v-model="settings.devMode" />
      </el-form-item>
      <el-form-item v-if="settings.devMode" label="交易时间检查" style="margin-left: 20px;">
        <el-switch v-model="settings.tradingTimeCheck" />
        <span style="margin-left: 10px; color: #909399; font-size: 13px;">
          开启后将检查是否在交易时间内
        </span>
      </el-form-item>
      <el-form-item v-if="!settings.devMode" label="交易时间检查" style="margin-left: 20px;">
        <el-switch v-model="settings.tradingTimeCheck" disabled />
        <span style="margin-left: 10px; color: #E6A23C; font-size: 13px;">
          <el-icon style="vertical-align: middle;"><Warning /></el-icon>
          生产模式下交易时间检查永远启用，不可修改
        </span>
      </el-form-item>
      
      <!-- 日志设置 -->
      <el-divider content-position="left">
        <span style="font-weight: 600;">日志设置</span>
      </el-divider>
      <el-form-item label="日志级别">
        <el-select v-model="settings.logging.level" style="width: 200px;">
          <el-option label="DEBUG" value="DEBUG" />
          <el-option label="INFO" value="INFO" />
          <el-option label="WARNING" value="WARNING" />
          <el-option label="ERROR" value="ERROR" />
        </el-select>
      </el-form-item>
      <el-form-item label="文件大小上限">
        <el-input 
          v-model="settings.logging.rotation" 
          placeholder="例如: 50 MB"
          style="width: 200px;"
        />
        <span style="margin-left: 10px; color: #909399; font-size: 13px;">
          单个日志文件达到此大小后自动轮转
        </span>
      </el-form-item>
      <el-form-item label="日志保留时间">
        <el-input 
          v-model="settings.logging.retention" 
          placeholder="例如: 14 days"
          style="width: 200px;"
        />
        <span style="margin-left: 10px; color: #909399; font-size: 13px;">
          超过保留时间的日志将被自动删除
        </span>
      </el-form-item>
      <el-form-item label="压缩格式">
        <el-select v-model="settings.logging.compression" style="width: 200px;">
          <el-option label="ZIP" value="zip" />
          <el-option label="TAR.GZ" value="tar.gz" />
          <el-option label="TAR.BZ2" value="tar.bz2" />
        </el-select>
        <span style="margin-left: 10px; color: #909399; font-size: 13px;">
          归档日志文件的压缩格式
        </span>
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
          <el-form-item label="应用ID">
            <el-input 
              v-model="settings.notificationConfig.wecom.agentId" 
              placeholder="请输入应用ID"
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
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Warning } from '@element-plus/icons-vue'
import { 
  getSystemConfig, 
  updateSystemConfig, 
  getNotificationConfig, 
  updateNotificationConfig,
  getLoggingConfig,
  updateLoggingConfig
} from '@/api/system'

const settings = reactive({
  systemName: 'Homalos',
  devMode: true,              // 开发模式，默认开启
  tradingTimeCheck: false,    // 交易时间检查，默认关闭
  logging: {
    level: 'INFO',            // 日志级别
    rotation: '50 MB',        // 单个日志文件大小上限
    retention: '14 days',     // 日志保留时间
    compression: 'zip'        // 日志文件压缩格式
  },
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
      agentId: '',           // 应用ID
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

/**
 * 加载系统配置
 */
const loadSystemConfig = async () => {
  try {
    const response = await getSystemConfig()
    console.log('获取系统配置:', response)
    
    // 更新 settings 中的系统配置项
    if (response.dev_mode !== undefined) {
      settings.devMode = response.dev_mode
    }
    if (response.dev_trading_hours_check !== undefined) {
      settings.tradingTimeCheck = response.dev_trading_hours_check
    }
    
    console.log('系统配置已加载:', { devMode: settings.devMode, tradingTimeCheck: settings.tradingTimeCheck })
  } catch (error) {
    console.error('加载系统配置失败:', error)
    ElMessage.error('加载系统配置失败')
  }
  
  // 加载通知配置
  try {
    const notificationResponse = await getNotificationConfig()
    console.log('获取通知配置:', notificationResponse)
    
    // 更新钉钉配置
    if (notificationResponse.dingtalk) {
      settings.notificationConfig.dingtalk.enabled = notificationResponse.dingtalk.enabled
      settings.notificationConfig.dingtalk.name = notificationResponse.dingtalk.name
      settings.notificationConfig.dingtalk.id = notificationResponse.dingtalk.id
      settings.notificationConfig.dingtalk.webhookUrl = notificationResponse.dingtalk.webhookUrl
    }
    
    // 更新企业微信配置
    if (notificationResponse.wecom) {
      settings.notificationConfig.wecom.enabled = notificationResponse.wecom.enabled
      settings.notificationConfig.wecom.name = notificationResponse.wecom.name
      settings.notificationConfig.wecom.corpId = notificationResponse.wecom.corpId
      settings.notificationConfig.wecom.agentId = notificationResponse.wecom.agentId
      settings.notificationConfig.wecom.appSecret = notificationResponse.wecom.appSecret
    }
    
    // 更新邮件配置
    if (notificationResponse.email) {
      settings.notificationConfig.email.enabled = notificationResponse.email.enabled
      settings.notificationConfig.email.address = notificationResponse.email.address
      settings.notificationConfig.email.smtpServer = notificationResponse.email.smtpServer
    }
    
    console.log('通知配置已加载')
  } catch (error) {
    console.error('加载通知配置失败:', error)
    ElMessage.warning('加载通知配置失败，使用默认配置')
  }
  
  // 加载日志配置
  try {
    const loggingResponse = await getLoggingConfig()
    console.log('获取日志配置:', loggingResponse)
    
    if (loggingResponse) {
      settings.logging.level = loggingResponse.level
      settings.logging.rotation = loggingResponse.rotation
      settings.logging.retention = loggingResponse.retention
      settings.logging.compression = loggingResponse.compression
    }
    
    console.log('日志配置已加载')
  } catch (error) {
    console.error('加载日志配置失败:', error)
    ElMessage.warning('加载日志配置失败，使用默认配置')
  }
}

/**
 * 保存系统设置
 */
const saveSettings = async () => {
  let systemConfigSaved = false
  let loggingConfigSaved = false
  let notificationConfigSaved = false
  
  // ========== 第一步：保存系统配置 ==========
  try {
    const systemConfig = {
      dev_mode: settings.devMode,
      dev_trading_hours_check: settings.tradingTimeCheck
    }
    
    console.log('保存系统配置:', systemConfig)
    
    const response = await updateSystemConfig(systemConfig)
    console.log('系统配置保存响应:', response)
    
    systemConfigSaved = true
    ElMessage.success('系统配置保存成功')
  } catch (error) {
    console.error('保存系统配置失败:', error)
    ElMessage.error('系统配置保存失败')
  }
  
  // ========== 第二步：保存日志配置 ==========
  try {
    const loggingConfig = {
      level: settings.logging.level,
      rotation: settings.logging.rotation,
      retention: settings.logging.retention,
      compression: settings.logging.compression
    }
    
    console.log('保存日志配置:', loggingConfig)
    
    const loggingResponse = await updateLoggingConfig(loggingConfig)
    console.log('日志配置保存响应:', loggingResponse)
    
    loggingConfigSaved = true
    ElMessage.success('日志配置保存成功')
  } catch (error) {
    console.error('保存日志配置失败:', error)
    ElMessage.error('日志配置保存失败')
  }
  
  // ========== 第三步：验证并保存通知配置 ==========
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
    if (!settings.notificationConfig.wecom.agentId) {
      errors.push('应用ID')
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
  
  // 如果有未填写的配置，显示警告（但不影响系统配置的保存）
  if (errors.length > 0) {
    ElMessage.warning(`通知配置未完整填写：${errors.join('、')}，已跳过保存通知配置`)
    console.log('通知配置验证失败，跳过保存')
  } else {
    // 保存通知配置到后端
    try {
      const notificationConfig = {
        dingtalk: {
          enabled: settings.notificationConfig.dingtalk.enabled,
          name: settings.notificationConfig.dingtalk.name,
          id: settings.notificationConfig.dingtalk.id,
          webhookUrl: settings.notificationConfig.dingtalk.webhookUrl
        },
        wecom: {
          enabled: settings.notificationConfig.wecom.enabled,
          name: settings.notificationConfig.wecom.name,
          corpId: settings.notificationConfig.wecom.corpId,
          agentId: settings.notificationConfig.wecom.agentId,
          appSecret: settings.notificationConfig.wecom.appSecret
        },
        email: {
          enabled: settings.notificationConfig.email.enabled,
          address: settings.notificationConfig.email.address,
          smtpServer: settings.notificationConfig.email.smtpServer
        }
      }
      
      console.log('保存通知配置:', notificationConfig)
      
      const notificationResponse = await updateNotificationConfig(notificationConfig)
      console.log('通知配置保存响应:', notificationResponse)
      
      notificationConfigSaved = true
      ElMessage.success('通知配置保存成功')
      
      // 如果所有配置都保存成功，显示完整成功消息
      if (systemConfigSaved && loggingConfigSaved && notificationConfigSaved) {
        ElMessage.success('所有设置保存成功')
      }
    } catch (error) {
      console.error('保存通知配置失败:', error)
      ElMessage.error('通知配置保存失败')
    }
  }
}

// 组件挂载时加载系统配置
onMounted(() => {
  loadSystemConfig()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

