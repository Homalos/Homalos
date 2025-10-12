<template>
  <el-card shadow="hover">
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
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

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
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

