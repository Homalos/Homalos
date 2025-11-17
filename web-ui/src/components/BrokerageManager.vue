<template>
  <div class="brokerage-manager">
    <div class="header">
      <h2>券商账户管理</h2>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加账户
      </el-button>
    </div>

    <!-- 账户列表 -->
    <el-table
      v-loading="brokerageStore.loading"
      :data="brokerageStore.brokerages"
      stripe
      style="width: 100%"
    >
      <el-table-column prop="account_name" label="账户名称" min-width="120" />
      
      <el-table-column label="默认" width="80" align="center">
        <template #default="{ row }">
          <el-icon v-if="row.is_default" color="#67C23A" :size="20">
            <Check />
          </el-icon>
        </template>
      </el-table-column>
      
      <el-table-column prop="broker_name" label="券商" min-width="180" show-overflow-tooltip />
      
      <el-table-column prop="account_id" label="资金账号" min-width="120" />
      
      <el-table-column prop="account_type" label="账户类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.account_type === 'production' ? 'danger' : 'info'" size="small">
            {{ row.account_type === 'production' ? '实盘' : '模拟' }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="created_at" label="创建时间" min-width="160">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="420" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="!isCurrentAccount(row)"
            size="small"
            type="success"
            @click="handleSwitch(row)"
          >
            切换登录
          </el-button>
          
          <el-button
            v-if="!row.is_default"
            size="small"
            @click="handleSetDefault(row.id)"
          >
            设为默认
          </el-button>
          
          <el-button
            size="small"
            @click="handleEdit(row)"
          >
            编辑
          </el-button>
          
          <el-button
            size="small"
            type="warning"
            @click="handleChangePassword(row)"
          >
            修改密码
          </el-button>
          
          <el-button
            size="small"
            type="danger"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加账户对话框 -->
    <AddBrokerageAccountDialog
      v-model="showAddDialog"
      @success="handleAddSuccess"
    />

    <!-- 编辑账户对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑券商账户"
      width="500px"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editFormRules"
        label-width="120px"
      >
        <el-form-item label="账户名称" prop="account_name">
          <el-input v-model="editForm.account_name" placeholder="请输入账户别名" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpdate" :loading="brokerageStore.loading">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 切换登录对话框 -->
    <el-dialog
      v-model="showSwitchDialog"
      title="切换登录账户"
      width="450px"
    >
      <el-form
        ref="switchFormRef"
        :model="switchForm"
        :rules="switchFormRules"
        label-width="100px"
      >
        <el-form-item label="账户信息">
          <div class="account-info">
            <div>{{ switchAccount?.account_name }}</div>
            <div class="account-detail">
              {{ switchAccount?.broker_name }} - {{ switchAccount?.account_id }}
            </div>
          </div>
        </el-form-item>
        <el-form-item label="账户密码" prop="password">
          <el-input
            v-model="switchForm.password"
            type="password"
            placeholder="请输入账户密码"
            show-password
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showSwitchDialog = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmSwitch" :loading="switchLoading">
          确认切换
        </el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="showPasswordDialog"
      title="修改账户密码"
      width="450px"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordFormRules"
        label-width="100px"
      >
        <el-form-item label="账户信息">
          <div class="account-info">
            <div>{{ passwordAccount?.account_name }}</div>
            <div class="account-detail">
              {{ passwordAccount?.broker_name }} - {{ passwordAccount?.account_id }}
            </div>
          </div>
        </el-form-item>
        <el-form-item label="旧密码" prop="old_password">
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            placeholder="请输入旧密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            placeholder="请输入新密码（至少6位）"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmPassword" :loading="passwordLoading">
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Check } from '@element-plus/icons-vue'
import { useBrokerageStore } from '@/stores/brokerage'
import { useTradingAccountStore } from '@/stores/tradingAccount'
import { changeBrokeragePassword } from '@/api/brokerage'
import AddBrokerageAccountDialog from './AddBrokerageAccountDialog.vue'

const brokerageStore = useBrokerageStore()
const tradingAccountStore = useTradingAccountStore()

// 对话框显示状态
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const showSwitchDialog = ref(false)
const showPasswordDialog = ref(false)

// 表单引用
const editFormRef = ref(null)
const switchFormRef = ref(null)
const passwordFormRef = ref(null)

// 加载状态
const switchLoading = ref(false)
const passwordLoading = ref(false)

// 当前操作的账户
const switchAccount = ref(null)
const passwordAccount = ref(null)

// 编辑表单
const editForm = ref({
  id: null,
  account_name: ''
})

// 切换登录表单
const switchForm = reactive({
  password: ''
})

// 修改密码表单
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

// 表单验证规则
const editFormRules = {
  account_name: [
    { required: true, message: '请输入账户名称', trigger: 'blur' }
  ]
}

const switchFormRules = {
  password: [
    { required: true, message: '请输入账户密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ]
}

const passwordFormRules = {
  old_password: [
    { required: true, message: '请输入旧密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value === passwordForm.old_password) {
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
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
}

// 加载账户列表
onMounted(() => {
  loadBrokerages()
})

async function loadBrokerages() {
  try {
    await brokerageStore.fetchBrokerages(true)
  } catch (error) {
    ElMessage.error('加载券商账户列表失败')
  }
}

// 添加账户成功回调
async function handleAddSuccess() {
  // 关闭对话框
  showAddDialog.value = false
  
  // 刷新账户列表
  await loadBrokerages()
  
  ElMessage.success('券商账户添加成功')
}

// 编辑账户
function handleEdit(row) {
  editForm.value = {
    id: row.id,
    account_name: row.account_name,
    is_default: row.is_default
  }
  showEditDialog.value = true
}

// 更新账户
async function handleUpdate() {
  try {
    await editFormRef.value.validate()
    const { id, ...data } = editForm.value
    await brokerageStore.modifyBrokerage(id, data)
    ElMessage.success('更新券商账户成功')
    showEditDialog.value = false
  } catch (error) {
    if (error !== false) {
      ElMessage.error(error.message || '更新券商账户失败')
    }
  }
}

// 删除账户
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除券商账户"${row.account_name}"吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await brokerageStore.removeBrokerage(row.id)
    ElMessage.success('删除券商账户成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除券商账户失败')
    }
  }
}

// 设置默认账户
async function handleSetDefault(id) {
  try {
    await brokerageStore.setDefault(id)
    ElMessage.success('设置默认账户成功')
  } catch (error) {
    ElMessage.error(error.message || '设置默认账户失败')
  }
}

// 格式化日期
function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 判断是否为当前登录账户
function isCurrentAccount(row) {
  return String(tradingAccountStore.accountId) === String(row.id)
}

// 切换登录
function handleSwitch(row) {
  switchAccount.value = row
  switchForm.password = ''
  showSwitchDialog.value = true
  
  // 清除表单验证状态
  setTimeout(() => {
    switchFormRef.value?.clearValidate()
  }, 0)
}

// 确认切换
async function handleConfirmSwitch() {
  if (!switchFormRef.value) return
  
  await switchFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    switchLoading.value = true
    try {
      // 调用登录方法切换账户
      const result = await tradingAccountStore.login({
        account_id: switchAccount.value.id,
        password: switchForm.password
      })
      
      if (result.success) {
        ElMessage.success(`已切换到账户：${switchAccount.value.account_name}`)
        showSwitchDialog.value = false
        
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

// 修改密码
function handleChangePassword(row) {
  passwordAccount.value = row
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  showPasswordDialog.value = true
  
  // 清除表单验证状态
  setTimeout(() => {
    passwordFormRef.value?.clearValidate()
  }, 0)
}

// 确认修改密码
async function handleConfirmPassword() {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    passwordLoading.value = true
    try {
      await changeBrokeragePassword(passwordAccount.value.id, {
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password
      })
      
      ElMessage.success('密码修改成功')
      showPasswordDialog.value = false
      
      // 清空表单
      passwordFormRef.value?.resetFields()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '密码修改失败')
    } finally {
      passwordLoading.value = false
    }
  })
}
</script>

<style scoped>
.brokerage-manager {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.account-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.account-info {
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.account-info > div:first-child {
  font-weight: 600;
  margin-bottom: 5px;
}

.account-detail {
  font-size: 12px;
  color: #909399;
}
</style>
