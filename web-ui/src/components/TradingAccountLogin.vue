<template>
  <el-dialog
    v-model="visible"
    title="登录资金账户"
    width="500px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <!-- 无账户时的引导提示 -->
    <el-alert
      v-if="!hasAccounts"
      title="还没有券商账户"
      type="info"
      :closable="false"
      style="margin-bottom: 20px;"
    >
      <template #default>
        <div style="margin-top: 8px;">
          您还没有添加券商账户，请先在"管理资金账户"中添加您的券商账户信息。
        </div>
        <el-button
          type="primary"
          size="small"
          style="margin-top: 12px;"
          @click="handleGoToManage"
        >
          前往添加账户
        </el-button>
      </template>
    </el-alert>

    <!-- 有账户时显示登录表单 -->
    <el-form
      v-if="hasAccounts"
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
    >
      <!-- 选择账户 -->
      <el-form-item label="选择账户" prop="account_id">
        <el-select
          v-model="formData.account_id"
          placeholder="请选择账户"
          style="width: 100%;"
        >
          <el-option
            v-for="account in accountList"
            :key="account.id"
            :label="account.account_name || account.display_name"
            :value="account.id"
          >
            <span>{{ account.account_name || account.display_name }}</span>
            <span style="float: right; color: #8492a6; font-size: 13px;">
              {{ account.broker_id }} - {{ account.account_id }}
            </span>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 密码 -->
      <el-form-item label="交易密码" prop="password">
        <el-input
          v-model="formData.password"
          type="password"
          :placeholder="isPasswordRemembered ? '已保存密码，可直接登录（或输入新密码更新）' : '请输入交易密码'"
          show-password
          @keyup.enter="handleLogin"
        />
        <div v-if="isPasswordRemembered" style="color: #67C23A; font-size: 12px; margin-top: 4px;">
          <el-icon><Check /></el-icon>
          已记住密码，可直接登录
        </div>
      </el-form-item>

      <!-- 记住账户 -->
      <el-form-item>
        <el-checkbox v-model="formData.remember">
          记住此账户
        </el-checkbox>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button
        v-if="hasAccounts"
        type="primary"
        :loading="loading"
        @click="handleLogin"
      >
        登录
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { useTradingAccountStore } from '@/stores/tradingAccount'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'success', 'goToManage'])

const tradingAccountStore = useTradingAccountStore()
const formRef = ref(null)
const loading = ref(false)

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const hasAccounts = computed(() => tradingAccountStore.accountList.length > 0)
const accountList = computed(() => tradingAccountStore.accountList)

const formData = reactive({
  account_id: null,
  password: '',
  remember: false
})

// 当前选中账户是否记住了密码
const isPasswordRemembered = computed(() => {
  if (formData.account_id) {
    const account = accountList.value.find(acc => acc.id === formData.account_id)
    return account?.remember_password || false
  }
  return false
})

const rules = computed(() => ({
  account_id: [
    { required: true, message: '请选择账户', trigger: 'change' }
  ],
  password: [
    { 
      required: !isPasswordRemembered.value, 
      message: '请输入密码', 
      trigger: 'blur' 
    },
    { 
      min: 6, 
      message: '密码长度至少6位', 
      trigger: 'blur',
      validator: (rule, value, callback) => {
        if (value && value.length < 6) {
          callback(new Error('密码长度至少6位'))
        } else {
          callback()
        }
      }
    }
  ]
}))

/**
 * 前往管理账户
 */
function handleGoToManage() {
  visible.value = false
  emit('goToManage')
}

/**
 * 登录
 */
async function handleLogin() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    
    try {
      const loginData = {
        account_id: formData.account_id,
        password: formData.password,
        remember: formData.remember
      }
      
      const result = await tradingAccountStore.login(loginData)
      
      if (result.success) {
        // 保存上次登录的账户ID
        localStorage.setItem('last_trading_account_id', String(result.account.id))
        
        // 不在这里显示成功提示，由父组件显示更具体的提示
        emit('success', result.account)
        handleClose()
      } else {
        ElMessage.error(result.message || '登录失败')
      }
    } catch (error) {
      console.error('登录失败:', error)
      ElMessage.error('登录失败')
    } finally {
      loading.value = false
    }
  })
}

/**
 * 关闭对话框
 */
function handleClose() {
  formRef.value?.resetFields()
  visible.value = false
}

onMounted(() => {
  // 自动选择上次登录的账户
  if (hasAccounts.value) {
    const lastAccountId = localStorage.getItem('last_trading_account_id')
    if (lastAccountId) {
      const accountIdNum = parseInt(lastAccountId)
      const account = accountList.value.find(acc => acc.id === accountIdNum)
      if (account) {
        formData.account_id = accountIdNum
      }
    }
  }
})

// 监听对话框打开，刷新账户列表
watch(() => visible.value, async (newVisible) => {
  if (newVisible) {
    // 对话框打开时刷新账户列表
    await tradingAccountStore.fetchAccountList()
  }
})

// 监听账户选择变化，自动设置remember状态
watch(() => formData.account_id, (newAccountId) => {
  if (newAccountId) {
    const account = accountList.value.find(acc => acc.id === newAccountId)
    if (account && account.remember_password) {
      formData.remember = true
      // 清空密码字段，因为已经记住了
      formData.password = ''
    }
  }
})
</script>

<style scoped>
.el-select {
  width: 100%;
}
</style>

