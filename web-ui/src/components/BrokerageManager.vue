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
      <el-table-column prop="account_name" label="账户名称" width="180">
        <template #default="{ row }">
          <div class="account-name">
            {{ row.account_name }}
            <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
          </div>
        </template>
      </el-table-column>
      
      <el-table-column prop="broker_name" label="券商" width="150" />
      
      <el-table-column prop="account_id" label="资金账号" width="150" />
      
      <el-table-column prop="account_type" label="账户类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.account_type === 'production' ? 'danger' : 'info'" size="small">
            {{ row.account_type === 'production' ? '实盘' : '模拟' }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag
            :type="getStatusType(row.status)"
            size="small"
          >
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="connection_status" label="连接状态" width="120">
        <template #default="{ row }">
          <el-tag
            v-if="row.connection_status"
            :type="getConnectionType(row.connection_status)"
            size="small"
          >
            {{ getConnectionText(row.connection_status) }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="!row.is_default"
            size="small"
            @click="handleSetDefault(row.id)"
          >
            设为默认
          </el-button>
          
          <el-button
            v-if="row.status === 'inactive'"
            size="small"
            type="success"
            @click="handleActivate(row.id)"
          >
            激活
          </el-button>
          
          <el-button
            v-if="row.status === 'active'"
            size="small"
            type="warning"
            @click="handleDeactivate(row.id)"
          >
            停用
          </el-button>
          
          <el-button
            size="small"
            @click="handleEdit(row)"
          >
            编辑
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
    <el-dialog
      v-model="showAddDialog"
      title="添加券商账户"
      width="600px"
    >
      <el-form
        ref="addFormRef"
        :model="addForm"
        :rules="addFormRules"
        label-width="120px"
      >
        <el-form-item label="账户名称" prop="account_name">
          <el-input v-model="addForm.account_name" placeholder="请输入账户别名" />
        </el-form-item>
        
        <el-form-item label="券商代码" prop="broker_code">
          <el-input v-model="addForm.broker_code" placeholder="如：simnow7x24" />
        </el-form-item>
        
        <el-form-item label="券商名称" prop="broker_name">
          <el-input v-model="addForm.broker_name" placeholder="如：SimNow 7x24" />
        </el-form-item>
        
        <el-form-item label="资金账号" prop="account_id">
          <el-input v-model="addForm.account_id" placeholder="请输入资金账号" />
        </el-form-item>
        
        <el-form-item label="投资者ID" prop="investor_id">
          <el-input v-model="addForm.investor_id" placeholder="请输入投资者ID" />
        </el-form-item>
        
        <el-form-item label="券商ID" prop="broker_id">
          <el-input v-model="addForm.broker_id" placeholder="请输入券商ID" />
        </el-form-item>
        
        <el-form-item label="交易密码" prop="password">
          <el-input
            v-model="addForm.password"
            type="password"
            placeholder="请输入交易密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="授权码">
          <el-input v-model="addForm.auth_code" placeholder="选填" />
        </el-form-item>
        
        <el-form-item label="应用ID">
          <el-input v-model="addForm.app_id" placeholder="选填" />
        </el-form-item>
        
        <el-form-item label="账户类型" prop="account_type">
          <el-radio-group v-model="addForm.account_type">
            <el-radio label="simulation">模拟盘</el-radio>
            <el-radio label="production">实盘</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="设为默认">
          <el-switch v-model="addForm.is_default" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd" :loading="brokerageStore.loading">
          确定
        </el-button>
      </template>
    </el-dialog>

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
        
        <el-form-item label="账户状态" prop="status">
          <el-radio-group v-model="editForm.status">
            <el-radio label="active">激活</el-radio>
            <el-radio label="inactive">未激活</el-radio>
            <el-radio label="error">错误</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="设为默认">
          <el-switch v-model="editForm.is_default" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpdate" :loading="brokerageStore.loading">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useBrokerageStore } from '@/stores/brokerage'

const brokerageStore = useBrokerageStore()

// 对话框显示状态
const showAddDialog = ref(false)
const showEditDialog = ref(false)

// 表单引用
const addFormRef = ref(null)
const editFormRef = ref(null)

// 添加表单
const addForm = ref({
  account_name: '',
  broker_code: '',
  broker_name: '',
  account_id: '',
  investor_id: '',
  broker_id: '',
  password: '',
  auth_code: '',
  app_id: '',
  account_type: 'production',
  is_default: false
})

// 编辑表单
const editForm = ref({
  id: null,
  account_name: '',
  status: 'active',
  is_default: false
})

// 表单验证规则
const addFormRules = {
  account_name: [
    { required: true, message: '请输入账户名称', trigger: 'blur' }
  ],
  broker_code: [
    { required: true, message: '请输入券商代码', trigger: 'blur' }
  ],
  broker_name: [
    { required: true, message: '请输入券商名称', trigger: 'blur' }
  ],
  account_id: [
    { required: true, message: '请输入资金账号', trigger: 'blur' }
  ],
  investor_id: [
    { required: true, message: '请输入投资者ID', trigger: 'blur' }
  ],
  broker_id: [
    { required: true, message: '请输入券商ID', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入交易密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const editFormRules = {
  account_name: [
    { required: true, message: '请输入账户名称', trigger: 'blur' }
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

// 添加账户
async function handleAdd() {
  try {
    await addFormRef.value.validate()
    await brokerageStore.addBrokerage(addForm.value)
    ElMessage.success('添加券商账户成功')
    showAddDialog.value = false
    resetAddForm()
  } catch (error) {
    if (error !== false) {
      ElMessage.error(error.message || '添加券商账户失败')
    }
  }
}

// 编辑账户
function handleEdit(row) {
  editForm.value = {
    id: row.id,
    account_name: row.account_name,
    status: row.status,
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

// 激活账户
async function handleActivate(id) {
  try {
    await brokerageStore.activate(id)
    ElMessage.success('激活账户成功')
  } catch (error) {
    ElMessage.error(error.message || '激活账户失败')
  }
}

// 停用账户
async function handleDeactivate(id) {
  try {
    await brokerageStore.deactivate(id)
    ElMessage.success('停用账户成功')
  } catch (error) {
    ElMessage.error(error.message || '停用账户失败')
  }
}

// 重置添加表单
function resetAddForm() {
  addForm.value = {
    account_name: '',
    broker_code: '',
    broker_name: '',
    account_id: '',
    investor_id: '',
    broker_id: '',
    password: '',
    auth_code: '',
    app_id: '',
    account_type: 'production',
    is_default: false
  }
  addFormRef.value?.resetFields()
}

// 状态类型
function getStatusType(status) {
  const types = {
    active: 'success',
    inactive: 'info',
    error: 'danger'
  }
  return types[status] || 'info'
}

// 状态文本
function getStatusText(status) {
  const texts = {
    active: '激活',
    inactive: '未激活',
    error: '错误'
  }
  return texts[status] || status
}

// 连接状态类型
function getConnectionType(status) {
  const types = {
    connected: 'success',
    disconnected: 'info',
    connecting: 'warning',
    error: 'danger'
  }
  return types[status] || 'info'
}

// 连接状态文本
function getConnectionText(status) {
  const texts = {
    connected: '已连接',
    disconnected: '已断开',
    connecting: '连接中',
    error: '连接错误'
  }
  return texts[status] || status
}

// 格式化日期
function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
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
</style>
