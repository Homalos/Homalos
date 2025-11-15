<template>
  <el-dialog
    v-model="visible"
    title="管理资金账户"
    width="800px"
    :close-on-click-modal="false"
  >
    <el-table :data="accountList" stripe>
      <el-table-column prop="account_name" label="账户名称" />
      <el-table-column prop="broker_name" label="券商名称" width="120" />
      <el-table-column prop="account_type" label="账户类型" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.account_type?.toUpperCase() === 'SIMULATION'" type="warning" size="small">
            模拟
          </el-tag>
          <el-tag v-else-if="row.account_type?.toUpperCase() === 'PRODUCTION'" type="primary" size="small">
            实盘
          </el-tag>
          <el-tag v-else type="info" size="small">
            {{ row.account_type || '未知' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="account_id" label="资金账号" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.status?.toUpperCase() === 'ACTIVE'" type="success" size="small">
            激活
          </el-tag>
          <el-tag v-else-if="row.status?.toUpperCase() === 'INACTIVE'" type="info" size="small">
            未激活
          </el-tag>
          <el-tag v-else type="danger" size="small">
            错误
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="默认" width="80">
        <template #default="{ row }">
          <el-icon v-if="row.is_default" color="#67C23A">
            <Check />
          </el-icon>
        </template>
      </el-table-column>
      <el-table-column label="最后登录" width="160">
        <template #default="{ row }">
          {{ formatDateTime(row.last_login) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="!isCurrentAccount(row) && row.status?.toUpperCase() === 'ACTIVE'"
            link
            type="success"
            size="small"
            @click="handleSwitch(row)"
          >
            切换
          </el-button>
          <el-button
            v-if="row.status?.toUpperCase() === 'INACTIVE'"
            link
            type="success"
            size="small"
            @click="handleActivate(row)"
          >
            激活
          </el-button>
          <el-button
            v-if="row.status?.toUpperCase() === 'ACTIVE'"
            link
            type="warning"
            size="small"
            @click="handleDeactivate(row)"
          >
            停用
          </el-button>
          <el-button
            v-if="!row.is_default"
            link
            type="primary"
            size="small"
            @click="handleSetDefault(row)"
          >
            设为默认
          </el-button>
          <el-button
            link
            type="primary"
            size="small"
            @click="handleEdit(row)"
          >
            编辑
          </el-button>
          <el-button
            link
            type="warning"
            size="small"
            @click="handleChangePassword(row)"
          >
            修改密码
          </el-button>
          <el-button
            :disabled="isCurrentAccount(row)"
            link
            type="danger"
            size="small"
            @click="handleDelete(row)"
            :title="isCurrentAccount(row) ? '无法删除当前登录的账户' : '删除账户'"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <template #footer>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        添加账户
      </el-button>
      <el-button @click="visible = false">关闭</el-button>
    </template>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑账户"
      width="400px"
      append-to-body
    >
      <el-form
        ref="editFormRef"
        :model="editFormData"
        label-width="100px"
      >
        <el-form-item label="账户名称">
          <el-input v-model="editFormData.account_name" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="editFormData.is_active"
            active-text="激活"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="450px"
      append-to-body
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordFormData"
        :rules="passwordRules"
        label-width="100px"
      >
        <el-form-item label="账户信息">
          <div class="account-info">
            <div>{{ currentAccount?.account_name }}</div>
            <div class="account-detail">
              {{ currentAccount?.broker_id }} - {{ currentAccount?.account_id }}
            </div>
          </div>
        </el-form-item>
        <el-form-item label="旧密码" prop="old_password">
          <el-input
            v-model="passwordFormData.old_password"
            type="password"
            placeholder="请输入旧密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordFormData.new_password"
            type="password"
            placeholder="请输入新密码（至少6位）"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="passwordFormData.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            show-password
            @keyup.enter="handleSavePassword"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="handleSavePassword">
          确认修改
        </el-button>
      </template>
    </el-dialog>

    <!-- 切换账户对话框 -->
    <el-dialog
      v-model="switchDialogVisible"
      title="切换资金账户"
      width="450px"
      append-to-body
    >
      <el-form
        ref="switchFormRef"
        :model="switchFormData"
        :rules="switchRules"
        label-width="100px"
      >
        <el-form-item label="账户信息">
          <div class="account-info">
            <div>{{ switchAccount?.account_name }}</div>
            <div class="account-detail">
              {{ maskAccountId(switchAccount?.account_id) }}
            </div>
          </div>
        </el-form-item>
        <el-form-item label="账户密码" prop="password">
          <el-input
            v-model="switchFormData.password"
            type="password"
            placeholder="请输入账户密码"
            show-password
            @keyup.enter="handleConfirmSwitch"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="switchDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="switchLoading" @click="handleConfirmSwitch">
          确认切换
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加账户对话框 -->
    <AddBrokerageAccountDialog
      v-model="addDialogVisible"
      @success="handleAddSuccess"
    />
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Plus } from '@element-plus/icons-vue'
import { useBrokerageStore } from '@/stores/brokerage'
import { useTradingAccountStore } from '@/stores/tradingAccount'
import {
  updateBrokerage,
  deleteBrokerage,
  setDefaultBrokerage,
  activateBrokerage,
  deactivateBrokerage,
  changeBrokeragePassword
} from '@/api/brokerage'
import { getTradingCoreStatus } from '@/api/tradingCore'
import AddBrokerageAccountDialog from './AddBrokerageAccountDialog.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'requestLogin'])

const brokerageStore = useBrokerageStore()
const tradingAccountStore = useTradingAccountStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const accountList = computed(() => brokerageStore.brokerages)

const addDialogVisible = ref(false)
const editDialogVisible = ref(false)
const editFormRef = ref(null)
const editFormData = reactive({
  id: null,
  account_name: '',
  is_active: true
})

const passwordDialogVisible = ref(false)
const passwordFormRef = ref(null)
const passwordLoading = ref(false)
const currentAccount = ref(null)

const passwordFormData = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const passwordRules = {
  old_password: [
    { required: true, message: '请输入旧密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value === passwordFormData.old_password) {
          callback(new Error('新密码不能与旧密码相同'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value !== passwordFormData.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
}

// 切换账户相关
const switchDialogVisible = ref(false)
const switchFormRef = ref(null)
const switchLoading = ref(false)
const switchAccount = ref(null)

const switchFormData = reactive({
  password: ''
})

const switchRules = {
  password: [
    { required: true, message: '请输入账户密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ]
}

/**
 * 格式化日期时间
 */
function formatDateTime(dateTime) {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

/**
 * 加密账号 - 只显示后4位
 */
function maskAccountId(accountId) {
  if (!accountId || accountId.length <= 4) {
    return accountId
  }
  const visiblePart = accountId.slice(-4)
  const maskedPart = '*'.repeat(accountId.length - 4)
  return maskedPart + visiblePart
}

/**
 * 判断是否为当前登录账户
 */
function isCurrentAccount(row) {
  // 统一转换为字符串进行比较
  return String(tradingAccountStore.accountId) === String(row.id)
}

/**
 * 设为默认
 */
async function handleSetDefault(row) {
  try {
    // 使用新的 brokerage API
    await setDefaultBrokerage(row.id)
    ElMessage.success('设置成功')
    // 刷新 brokerage store 的账户列表
    await brokerageStore.fetchBrokerages(true)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '设置失败')
  }
}

/**
 * 编辑
 */
function handleEdit(row) {
  editFormData.id = row.id
  editFormData.account_name = row.account_name
  editFormData.is_active = row.is_active
  editDialogVisible.value = true
}

/**
 * 保存编辑
 */
async function handleSaveEdit() {
  try {
    await updateBrokerage(editFormData.id, {
      account_name: editFormData.account_name
    })
    ElMessage.success('保存成功')
    editDialogVisible.value = false
    await tradingAccountStore.fetchAccountList()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

/**
 * 删除
 */
async function handleDelete(row) {
  try {
    // 1. 检查是否是当前账户
    if (isCurrentAccount(row)) {
      ElMessage.error('无法删除当前登录的账户，请先切换到其他账户或退出登录')
      return
    }
    
    // 2. 检查交易核心状态
    let warningMessage = `确定要删除账户 "${row.account_name}" 吗？\n删除后将无法恢复。`
    let confirmButtonText = '确定删除'
    let type = 'warning'
    
    try {
      const coreStatus = await getTradingCoreStatus()
      if (coreStatus && coreStatus.status === 'RUNNING') {
        warningMessage = `警告：交易核心正在运行！\n\n` +
                        `删除账户 "${row.account_name}" 可能影响：\n` +
                        `• 当前交易系统的稳定性\n` +
                        `• 如需重新连接网关将无法使用此账户\n` +
                        `• 无法通过该账户重新登录\n\n` +
                        `强烈建议：先停止交易核心再删除账户。`
        type = 'error'
        confirmButtonText = '仍要删除'
      }
    } catch (error) {
      console.warn('获取交易核心状态失败:', error)
    }
    
    await ElMessageBox.confirm(warningMessage, '确认删除账户', {
      confirmButtonText,
      cancelButtonText: '取消',
      type,
      distinguishCancelAndClose: true,
      dangerouslyUseHTMLString: false
    })
    
    // 使用新的 brokerage API
    await deleteBrokerage(row.id)
    ElMessage.success('删除成功')
    // 刷新 brokerage store 的账户列表
    await brokerageStore.fetchBrokerages(true)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

/**
 * 添加账户
 */
function handleAdd() {
  addDialogVisible.value = true
}

/**
 * 添加账户成功处理
 * 注意：API调用已在AddTradingAccountDialog中完成，这里只需要刷新列表
 */
async function handleAddSuccess() {
  // 关闭添加对话框
  addDialogVisible.value = false
  
  // 刷新账户列表
  await brokerageStore.fetchBrokerages(true)
  
  // 提示用户需要激活账户后才能登录
  ElMessage.success({
    message: '账户添加成功！请先激活账户后再登录',
    duration: 3000
  })
}

/**
 * 激活账户
 */
async function handleActivate(row) {
  try {
    await ElMessageBox.confirm(
      `确定要激活账户 "${row.account_name}" 吗？`,
      '激活账户',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    await brokerageStore.activate(row.id)
    ElMessage.success('账户已激活')
    
    // 刷新列表
    await brokerageStore.fetchBrokerages(true)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '激活失败')
    }
  }
}

/**
 * 停用账户
 */
async function handleDeactivate(row) {
  try {
    await ElMessageBox.confirm(
      `确定要停用账户 "${row.account_name}" 吗？\n停用后需要重新激活才能使用。`,
      '停用账户',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await brokerageStore.deactivate(row.id)
    ElMessage.success('账户已停用')
    
    // 刷新列表
    await brokerageStore.fetchBrokerages(true)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '停用失败')
    }
  }
}

/**
 * 修改密码
 */
function handleChangePassword(row) {
  currentAccount.value = row
  passwordFormData.old_password = ''
  passwordFormData.new_password = ''
  passwordFormData.confirm_password = ''
  passwordDialogVisible.value = true
}

/**
 * 保存密码
 */
async function handleSavePassword() {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    passwordLoading.value = true
    try {
      // 使用新的 brokerage API 修改密码
      await changeBrokeragePassword(currentAccount.value.id, passwordFormData.new_password)
      ElMessage.success('密码修改成功')
      passwordDialogVisible.value = false
      
      // 清空表单
      passwordFormRef.value?.resetFields()
      
      // 刷新账户列表
      await brokerageStore.fetchBrokerages(true)
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '密码修改失败')
    } finally {
      passwordLoading.value = false
    }
  })
}

/**
 * 切换账户
 */
function handleSwitch(row) {
  switchAccount.value = row
  switchFormData.password = ''
  switchDialogVisible.value = true
  
  // 清除表单验证状态
  if (switchFormRef.value) {
    switchFormRef.value.clearValidate()
  }
}

/**
 * 确认切换
 */
async function handleConfirmSwitch() {
  if (!switchFormRef.value) return
  
  await switchFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    switchLoading.value = true
    try {
      // 调用登录方法切换账户
      const result = await tradingAccountStore.login({
        account_id: switchAccount.value.id,
        password: switchFormData.password
      })
      
      if (result.success) {
        ElMessage.success(`已切换到账户：${switchAccount.value.account_name}`)
        switchDialogVisible.value = false
        
        // 清空表单
        switchFormRef.value?.resetFields()
      } else {
        ElMessage.error(result.message || '切换失败')
      }
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '切换失败，请检查密码')
    } finally {
      switchLoading.value = false
    }
  })
}

// 监听对话框打开，自动获取最新的券商账户列表
watch(visible, (newVal) => {
  if (newVal) {
    // 对话框打开时获取数据
    brokerageStore.fetchBrokerages(true)
  }
})
</script>

<style scoped>
.account-info {
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.account-detail {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}
</style>
