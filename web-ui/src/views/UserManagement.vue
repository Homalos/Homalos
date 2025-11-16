<template>
  <div class="user-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="title">用户管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加用户
          </el-button>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <div class="filter-container">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用户名、邮箱、手机号"
          style="width: 300px; margin-right: 10px;"
          clearable
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-select
          v-model="filterStatus"
          placeholder="状态筛选"
          style="width: 150px; margin-right: 10px;"
          clearable
          @change="handleSearch"
        >
          <el-option label="全部状态" value="" />
          <el-option label="未激活" value="inactive" />
          <el-option label="正常" value="active" />
          <el-option label="冻结" value="frozen" />
          <el-option label="禁用" value="disabled" />
        </el-select>
        
        <el-select
          v-model="filterRole"
          placeholder="角色筛选"
          style="width: 150px; margin-right: 10px;"
          clearable
          @change="handleSearch"
        >
          <el-option label="全部角色" value="" />
          <el-option label="普通用户" value="normal" />
          <el-option label="管理员" value="admin" />
        </el-select>
        
        <el-select
          v-model="filterUserType"
          placeholder="用户类型"
          style="width: 150px; margin-right: 10px;"
          clearable
          @change="handleSearch"
        >
          <el-option label="全部类型" value="" />
          <el-option label="普通用户" value="user" />
          <el-option label="管理员" value="admin" />
        </el-select>
        
        <el-button type="primary" @click="handleSearch">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
        
        <el-button @click="handleReset">
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
      </div>

      <!-- 用户列表 -->
      <el-table
        :data="userList"
        v-loading="loading"
        style="width: 100%; margin-top: 20px;"
        stripe
      >
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="full_name" label="全名" width="120" />
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row)">
              {{ getRoleText(row) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="用户类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.user_type === 'admin' ? 'warning' : 'success'">
              {{ row.user_type === 'admin' ? '管理员' : '用户' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="最后登录" width="180">
          <template #default="{ row }">
            {{ row.last_login_at ? formatDateTime(row.last_login_at) : '-' }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-dropdown @command="(command) => handleCommand(command, row)">
              <el-button size="small">
                更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="status">更改状态</el-dropdown-item>
                  <el-dropdown-item command="role">更改角色</el-dropdown-item>
                  <el-dropdown-item command="password">重置密码</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除用户</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 添加/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
      @close="handleDialogClose"
    >
      <el-form
        ref="userFormRef"
        :model="userForm"
        :rules="userFormRules"
        label-width="100px"
      >
        <!-- 基本信息 -->
        <div class="form-section">
          <h4 class="section-title">基本信息</h4>
          
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="userForm.username"
              placeholder="请输入用户名（3-50字符）"
              :disabled="isEdit"
              clearable
            />
          </el-form-item>
          
          <el-form-item label="邮箱" prop="email">
            <el-input 
              v-model="userForm.email" 
              type="email"
              placeholder="请输入邮箱地址" 
              clearable
            />
          </el-form-item>
          
          <el-form-item label="手机号" prop="phone">
            <el-input 
              v-model="userForm.phone" 
              placeholder="请输入手机号（可选）" 
              clearable
            />
          </el-form-item>
          
          <el-form-item label="全名" prop="full_name">
            <el-input 
              v-model="userForm.full_name" 
              placeholder="请输入真实姓名（可选）" 
              clearable
            />
          </el-form-item>
        </div>
        
        <!-- 安全设置（仅创建时） -->
        <div v-if="!isEdit" class="form-section">
          <h4 class="section-title">安全设置</h4>
          
          <el-form-item label="登录密码" prop="password">
            <el-input
              v-model="userForm.password"
              type="password"
              placeholder="请输入密码（至少6位，建议包含大小写字母、数字和特殊字符）"
              show-password
            />
            <div class="password-strength">
              <div class="strength-bar">
                <div 
                  class="strength-fill" 
                  :class="passwordStrengthClass"
                  :style="{ width: passwordStrengthWidth }"
                ></div>
              </div>
              <span class="strength-text">{{ passwordStrengthText }}</span>
            </div>
          </el-form-item>
          
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="userForm.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              show-password
            />
          </el-form-item>
        </div>
        
        <!-- 系统设置 -->
        <div class="form-section">
          <h4 class="section-title">系统设置</h4>
          
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="时区" prop="timezone">
                <el-select
                  v-model="userForm.timezone"
                  placeholder="选择时区"
                  style="width: 100%"
                >
                  <el-option
                    v-for="tz in timezoneOptions"
                    :key="tz.value"
                    :label="tz.label"
                    :value="tz.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="语言" prop="locale">
                <el-select
                  v-model="userForm.locale"
                  placeholder="选择语言"
                  style="width: 100%"
                >
                  <el-option
                    v-for="lang in languageOptions"
                    :key="lang.value"
                    :label="lang.label"
                    :value="lang.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </div>
        
        <!-- 权限设置（仅创建时） -->
        <div v-if="!isEdit" class="form-section">
          <h4 class="section-title">权限设置</h4>
          
          <el-form-item label="用户角色" prop="role">
            <el-radio-group v-model="userForm.role">
              <el-radio label="normal">普通用户</el-radio>
              <el-radio label="admin">普通管理员</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item label="账户状态" prop="status">
            <el-radio-group v-model="userForm.status">
              <el-radio label="active">正常</el-radio>
              <el-radio label="inactive">未激活</el-radio>
            </el-radio-group>
          </el-form-item>
        </div>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '创建用户' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 更改状态对话框 -->
    <el-dialog v-model="statusDialogVisible" title="更改用户状态" width="400px">
      <el-form label-width="80px">
        <el-form-item label="当前用户">
          <span>{{ currentUser?.username }}</span>
        </el-form-item>
        <el-form-item label="新状态">
          <el-select v-model="newStatus" placeholder="请选择状态">
            <el-option label="未激活" value="inactive" />
            <el-option label="正常" value="active" />
            <el-option label="冻结" value="frozen" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="statusDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleStatusSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 更改角色对话框 -->
    <el-dialog v-model="roleDialogVisible" title="更改用户角色" width="400px">
      <el-form label-width="80px">
        <el-form-item label="当前用户">
          <span>{{ currentUser?.username }}</span>
        </el-form-item>
        <el-form-item label="新角色">
          <el-select v-model="newRole" placeholder="请选择角色">
            <el-option label="普通用户" value="normal" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRoleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="passwordDialogVisible" title="重置用户密码" width="400px">
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordFormRules" label-width="80px">
        <el-form-item label="当前用户">
          <span>{{ currentUser?.username }}</span>
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handlePasswordSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, ArrowDown } from '@element-plus/icons-vue'
import {
  getUsersList,
  getAllUsersList,
  createUser,
  updateUser,
  updateUserStatus,
  updateUserRole,
  resetUserPassword,
  deleteUser
} from '@/api/users'

// 数据
const loading = ref(false)
const submitting = ref(false)
const userList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 搜索和筛选
const searchKeyword = ref('')
const filterStatus = ref('')
const filterRole = ref('')
const filterUserType = ref('')

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('添加用户')
const isEdit = ref(false)
const userFormRef = ref(null)
const userForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  phone: '',
  full_name: '',
  timezone: 'Asia/Shanghai',
  locale: 'zh-CN',
  role: 'normal',
  status: 'active'
})

// 时区选项
const timezoneOptions = [
  { value: 'Asia/Shanghai', label: '北京/上海时间 (UTC+8)' },
  { value: 'Asia/Hong_Kong', label: '香港时间 (UTC+8)' },
  { value: 'America/New_York', label: '纽约时间 (UTC-5)' },
  { value: 'Europe/London', label: '伦敦时间 (UTC+0)' },
  { value: 'UTC', label: '协调世界时 (UTC)' }
]

// 语言选项
const languageOptions = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'en-US', label: 'English' }
]

// 密码强度计算
const passwordStrength = computed(() => {
  const password = userForm.password
  if (!password) return 0
  
  let score = 0
  
  // 长度检查
  if (password.length >= 12) score += 25
  else if (password.length >= 8) score += 15
  else if (password.length >= 6) score += 10
  
  // 字符类型检查
  if (/[a-z]/.test(password)) score += 15
  if (/[A-Z]/.test(password)) score += 15
  if (/[0-9]/.test(password)) score += 15
  if (/[^a-zA-Z0-9]/.test(password)) score += 20
  
  // 复杂度检查
  if (/(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^a-zA-Z0-9])/.test(password)) {
    score += 10
  }
  
  return Math.min(score, 100)
})

const passwordStrengthText = computed(() => {
  const strength = passwordStrength.value
  if (strength < 30) return '弱'
  if (strength < 60) return '中等'
  if (strength < 80) return '强'
  return '很强'
})

const passwordStrengthClass = computed(() => {
  const strength = passwordStrength.value
  if (strength < 30) return 'weak'
  if (strength < 60) return 'medium'
  if (strength < 80) return 'strong'
  return 'very-strong'
})

const passwordStrengthWidth = computed(() => {
  return `${passwordStrength.value}%`
})

// 表单验证规则
const userFormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/, message: '用户名只能包含字母、数字、下划线和中文', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度在 6 到 50 个字符', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback()
          return
        }
        
        // 检查密码强度（建议但不强制）
        const hasUpper = /[A-Z]/.test(value)
        const hasLower = /[a-z]/.test(value)
        const hasDigit = /[0-9]/.test(value)
        const hasSpecial = /[^a-zA-Z0-9]/.test(value)
        
        // 如果密码太弱，给出警告但不阻止
        if (value.length < 8 || !hasUpper || !hasLower || !hasDigit) {
          console.warn('密码强度较弱，建议使用更强的密码')
        }
        
        callback()
      },
      trigger: 'blur'
    }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== userForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 状态对话框
const statusDialogVisible = ref(false)
const newStatus = ref('')

// 角色对话框
const roleDialogVisible = ref(false)
const newRole = ref('')

// 密码对话框
const passwordDialogVisible = ref(false)
const passwordFormRef = ref(null)
const passwordForm = reactive({
  newPassword: ''
})

const passwordFormRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度在 6 到 50 个字符', trigger: 'blur' }
  ]
}

// 当前操作的用户
const currentUser = ref(null)
const currentUserId = ref(null)

// 方法
const fetchUserList = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    if (filterRole.value) {
      params.role = filterRole.value
    }
    if (filterUserType.value) {
      params.user_type = filterUserType.value
    }
    
    // 使用getAllUsersList获取合并的用户和管理员列表
    const response = await getAllUsersList(params)
    userList.value = response.users
    total.value = response.total
  } catch (error) {
    ElMessage.error('获取用户列表失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchUserList()
}

const handleReset = () => {
  searchKeyword.value = ''
  filterStatus.value = ''
  filterRole.value = ''
  filterUserType.value = ''
  currentPage.value = 1
  fetchUserList()
}

const handlePageChange = () => {
  fetchUserList()
}

const handleSizeChange = () => {
  currentPage.value = 1
  fetchUserList()
}

const handleAdd = () => {
  isEdit.value = false
  dialogTitle.value = '添加用户'
  resetUserForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  // 检查是否为管理员
  if (row.user_type === 'admin') {
    ElMessage.warning('管理员编辑功能暂未实现')
    return
  }
  
  isEdit.value = true
  dialogTitle.value = '编辑用户'
  currentUserId.value = row.id  // 使用row.id而不是row.user_id
  
  userForm.username = row.username
  userForm.email = row.email
  userForm.phone = row.phone || ''
  userForm.full_name = row.full_name || ''
  
  dialogVisible.value = true
}

const handleCommand = (command, row) => {
  currentUser.value = row
  currentUserId.value = row.id  // 使用row.id而不是row.user_id
  
  // 检查是否为管理员（除了删除操作，删除操作在handleDelete中单独处理）
  if (row.user_type === 'admin' && command !== 'delete') {
    ElMessage.warning('管理员操作功能暂未实现')
    return
  }
  
  switch (command) {
    case 'status':
      newStatus.value = row.status
      statusDialogVisible.value = true
      break
    case 'role':
      newRole.value = row.role
      roleDialogVisible.value = true
      break
    case 'password':
      passwordForm.newPassword = ''
      passwordDialogVisible.value = true
      break
    case 'delete':
      handleDelete(row)
      break
  }
}

const handleSubmit = async () => {
  if (!userFormRef.value) return
  
  await userFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      if (isEdit.value) {
        // 编辑用户
        const data = {
          email: userForm.email,
          phone: userForm.phone || null,
          full_name: userForm.full_name || null
        }
        await updateUser(currentUserId.value, data)
        ElMessage.success('更新用户成功')
      } else {
        // 创建用户
        await createUser(userForm)
        ElMessage.success('创建用户成功')
      }
      
      dialogVisible.value = false
      fetchUserList()
    } catch (error) {
      ElMessage.error((isEdit.value ? '更新' : '创建') + '用户失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      submitting.value = false
    }
  })
}

const handleStatusSubmit = async () => {
  submitting.value = true
  try {
    await updateUserStatus(currentUserId.value, newStatus.value)
    ElMessage.success('更新用户状态成功')
    statusDialogVisible.value = false
    fetchUserList()
  } catch (error) {
    ElMessage.error('更新用户状态失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

const handleRoleSubmit = async () => {
  submitting.value = true
  try {
    await updateUserRole(currentUserId.value, newRole.value)
    ElMessage.success('更新用户角色成功')
    roleDialogVisible.value = false
    fetchUserList()
  } catch (error) {
    ElMessage.error('更新用户角色失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

const handlePasswordSubmit = async () => {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      await resetUserPassword(currentUserId.value, passwordForm.newPassword)
      ElMessage.success('重置密码成功')
      passwordDialogVisible.value = false
    } catch (error) {
      ElMessage.error('重置密码失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      submitting.value = false
    }
  })
}

const handleDelete = async (row) => {
  try {
    // 根据用户类型显示不同的提示
    const userTypeText = row.user_type === 'admin' ? '管理员' : '用户'
    
    await ElMessageBox.confirm(
      `确定要删除${userTypeText} "${row.username}" 吗？此操作不可逆！`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 根据user_type判断删除哪种用户
    if (row.user_type === 'admin') {
      // TODO: 实现管理员删除API
      ElMessage.warning('管理员删除功能暂未实现')
      return
    } else {
      // 删除普通用户，使用row.id而不是row.user_id
      await deleteUser(row.id)
      ElMessage.success('删除用户成功')
    }
    
    fetchUserList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除用户失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const handleDialogClose = () => {
  resetUserForm()
}

const resetUserForm = () => {
  userForm.username = ''
  userForm.email = ''
  userForm.password = ''
  userForm.confirmPassword = ''
  userForm.phone = ''
  userForm.full_name = ''
  userForm.timezone = 'Asia/Shanghai'
  userForm.locale = 'zh-CN'
  userForm.role = 'normal'
  userForm.status = 'active'
  
  if (userFormRef.value) {
    userFormRef.value.clearValidate()
  }
}

const getStatusType = (status) => {
  const typeMap = {
    inactive: 'info',
    active: 'success',
    frozen: 'warning',
    disabled: 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    inactive: '未激活',
    active: '正常',
    frozen: '冻结',
    disabled: '禁用'
  }
  return textMap[status] || status
}

// 根据user_type和role组合获取角色文本
const getRoleText = (row) => {
  if (row.user_type === 'admin') {
    // admins表：NORMAL=普通管理员, SUPER=超级管理员
    if (row.role === 'super') {
      return '超级管理员'
    } else if (row.role === 'normal') {
      return '普通管理员'
    }
    return '管理员'
  } else {
    // users表：NORMAL=普通用户
    return '普通用户'
  }
}

// 根据user_type和role组合获取标签类型
const getRoleTagType = (row) => {
  if (row.user_type === 'admin') {
    // 管理员使用danger色系
    if (row.role === 'super') {
      return 'danger'  // 超级管理员：红色
    } else {
      return 'warning'  // 普通管理员：橙色
    }
  } else {
    // 普通用户使用info色系
    return 'info'  // 普通用户：灰色
  }
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 生命周期
onMounted(() => {
  fetchUserList()
})
</script>

<style scoped>
.user-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .title {
  font-size: 18px;
  font-weight: bold;
}

.filter-container {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 表单分组样式 */
.form-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.form-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

/* 密码强度条样式 */
.password-strength {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.strength-bar {
  flex: 1;
  height: 4px;
  background-color: #f0f0f0;
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 2px;
}

.strength-fill.weak {
  background-color: #f56c6c;
}

.strength-fill.medium {
  background-color: #e6a23c;
}

.strength-fill.strong {
  background-color: #409eff;
}

.strength-fill.very-strong {
  background-color: #67c23a;
}

.strength-text {
  font-size: 12px;
  color: #909399;
  min-width: 40px;
}

</style>
