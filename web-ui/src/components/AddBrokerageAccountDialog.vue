<template>
  <el-dialog
    v-model="visible"
    title="添加券商账户"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
      @submit.prevent="handleSubmit"
    >
      <!-- 基本信息 -->
      <el-divider content-position="left">基本信息</el-divider>

      <el-form-item label="账户名称" prop="account_name">
        <el-input
          v-model="formData.account_name"
          placeholder="请输入账户名称（如：主账户、备用账户等）"
          maxlength="100"
          show-word-limit
          clearable
        />
      </el-form-item>

      <el-form-item label="开户机构" prop="broker_code">
        <el-select
          v-model="formData.broker_code"
          placeholder="请选择开户机构"
          style="width: 100%;"
          @change="handleBrokerChange"
          clearable
        >
          <el-option
            v-for="broker in brokerList"
            :key="broker.broker_key"
            :label="broker.name"
            :value="broker.broker_key"
          >
            <span>{{ broker.name }}</span>
            <span style="float: right; color: #8492a6; font-size: 13px;">
              {{ broker.broker_key }}
            </span>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 账户信息 -->
      <el-divider content-position="left">账户信息</el-divider>

      <el-form-item label="券商ID" prop="broker_id">
        <el-input
          v-model="formData.broker_id"
          placeholder="请输入券商ID"
          maxlength="50"
          clearable
        />
      </el-form-item>

      <el-form-item label="资金账号" prop="account_id">
        <el-input
          v-model="formData.account_id"
          placeholder="请输入资金账号"
          maxlength="50"
          clearable
        />
      </el-form-item>

      <el-form-item label="投资者ID" prop="investor_id">
        <el-input
          v-model="formData.investor_id"
          placeholder="请输入投资者ID（通常与资金账号相同）"
          maxlength="50"
          clearable
        />
      </el-form-item>

      <el-form-item label="交易密码" prop="password">
        <el-input
          v-model="formData.password"
          type="password"
          placeholder="请输入交易密码"
          show-password
          maxlength="100"
        />
      </el-form-item>

      <!-- 高级配置 -->
      <el-divider content-position="left">高级配置（可选）</el-divider>

      <el-form-item label="应用ID" prop="app_id">
        <el-input
          v-model="formData.app_id"
          placeholder="应用ID（可选）"
          maxlength="100"
          clearable
        />
      </el-form-item>

      <el-form-item label="授权码" prop="auth_code">
        <el-input
          v-model="formData.auth_code"
          placeholder="授权码（可选）"
          maxlength="100"
          clearable
        />
      </el-form-item>

      <!-- 账户设置 -->
      <el-divider content-position="left">账户设置</el-divider>

      <el-form-item label="账户类型" prop="account_type">
        <el-radio-group v-model="formData.account_type" :disabled="isAccountTypeDisabled">
          <el-radio label="production">实盘账户</el-radio>
          <el-radio label="simulation">模拟账户</el-radio>
        </el-radio-group>
        <div v-if="isAccountTypeDisabled" style="color: #909399; font-size: 12px; margin-top: 4px;">
          账户类型由开户机构自动确定
        </div>
      </el-form-item>

      <el-form-item>
        <el-checkbox v-model="formData.is_default">
          设为默认账户
        </el-checkbox>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        添加账户
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getBrokers } from '@/api/tradingAccount'
import { createBrokerage } from '@/api/brokerage'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const formRef = ref(null)
const loading = ref(false)
const brokerList = ref([])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 计算账户类型是否应该禁用（由开户机构自动确定）
const isAccountTypeDisabled = computed(() => {
  return !!formData.broker_code
})

const formData = reactive({
  account_name: '',
  broker_code: '',
  broker_name: '',
  broker_id: '',
  account_id: '',
  investor_id: '',
  password: '',
  app_id: '',
  auth_code: '',
  account_type: 'production',
  status: 'inactive',
  is_default: false
})

const rules = computed(() => ({
  account_name: [
    { required: true, message: '请输入账户名称', trigger: 'blur' },
    { min: 2, max: 100, message: '账户名称长度为2-100个字符', trigger: 'blur' }
  ],
  broker_code: [
    { required: true, message: '请选择开户机构', trigger: 'change' }
  ],
  broker_id: [
    { required: true, message: '请输入券商ID', trigger: 'blur' },
    { min: 1, max: 50, message: '券商ID长度为1-50个字符', trigger: 'blur' }
  ],
  account_id: [
    { required: true, message: '请输入资金账号', trigger: 'blur' },
    { min: 1, max: 50, message: '资金账号长度为1-50个字符', trigger: 'blur' }
  ],
  investor_id: [
    { required: true, message: '请输入投资者ID', trigger: 'blur' },
    { min: 1, max: 50, message: '投资者ID长度为1-50个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入交易密码', trigger: 'blur' },
    { min: 6, max: 100, message: '交易密码长度为6-100个字符', trigger: 'blur' }
  ]
}))

/**
 * 处理券商变化
 */
function handleBrokerChange(value) {
  const broker = brokerList.value.find(b => b.broker_key === value)
  if (broker) {
    formData.broker_name = broker.name
    
    // 根据券商配置的 is_simulation 字段自动设置账户类型
    // 如果配置中未指定，则根据名称判断（向后兼容）
    if (broker.is_simulation !== undefined) {
      formData.account_type = broker.is_simulation ? 'simulation' : 'production'
    } else {
      // 降级方案：根据名称判断
      formData.account_type = (broker.name && broker.name.includes('模拟')) ? 'simulation' : 'production'
    }
    
    // 自动填充投资者ID为资金账号（如果还没填）
    if (!formData.investor_id && formData.account_id) {
      formData.investor_id = formData.account_id
    }
  }
}

/**
 * 提交表单
 */
async function handleSubmit() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      // 构建账户数据
      const accountData = {
        account_name: formData.account_name,
        broker_code: formData.broker_code,
        broker_name: formData.broker_name,
        broker_id: formData.broker_id,
        account_id: formData.account_id,
        investor_id: formData.investor_id,
        password: formData.password,
        app_id: formData.app_id || null,
        auth_code: formData.auth_code || null,
        account_type: formData.account_type,
        status: 'inactive',
        is_default: formData.is_default
      }

      // 调用API添加账户
      await createBrokerage(accountData)
      
      ElMessage.success('券商账户添加成功')
      emit('success')
      handleClose()
    } catch (error) {
      console.error('添加券商账户失败:', error)
      ElMessage.error(error.response?.data?.detail || '添加券商账户失败')
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

/**
 * 加载券商列表
 */
async function loadBrokers() {
  try {
    const response = await getBrokers()
    brokerList.value = response
  } catch (error) {
    console.error('加载券商列表失败:', error)
    ElMessage.error('加载券商列表失败')
  }
}

onMounted(() => {
  loadBrokers()
})
</script>

<style scoped>
.el-divider {
  margin: 20px 0 16px 0;
}

.el-divider--horizontal {
  background: #dcdfe6;
}

:deep(.el-divider__text) {
  background: #fff;
  padding: 0 8px;
  color: #606266;
  font-weight: 500;
}
</style>
