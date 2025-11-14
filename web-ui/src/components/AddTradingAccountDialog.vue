<template>
  <el-dialog
    v-model="visible"
    title="添加新资金账户"
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

      <!-- 显示名称 -->
      <el-form-item label="账户名称" prop="display_name">
        <el-input
          v-model="formData.display_name"
          placeholder="请输入账户显示名称（如：主账户、备用账户等）"
          maxlength="100"
          show-word-limit
          clearable
        />
      </el-form-item>

      <!-- 券商选择 -->
      <el-form-item label="开户机构" prop="broker_key">
        <el-select
          v-model="formData.broker_key"
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

      <!-- 券商ID -->
      <el-form-item label="券商ID" prop="broker_id">
        <el-input
          v-model="formData.broker_id"
          placeholder="请输入券商ID"
          maxlength="50"
          clearable
        />
      </el-form-item>

      <!-- 资金账号 -->
      <el-form-item label="资金账号" prop="account_id">
        <el-input
          v-model="formData.account_id"
          placeholder="请输入资金账号"
          maxlength="100"
          clearable
        />
      </el-form-item>

      <!-- 交易密码 -->
      <el-form-item label="交易密码" prop="password">
        <el-input
          v-model="formData.password"
          type="password"
          placeholder="请输入交易密码（至少6位）"
          show-password
          maxlength="100"
        />
      </el-form-item>

      <!-- 记住密码 -->
      <el-form-item>
        <el-checkbox v-model="formData.remember_password">
          记住密码（加密存储）
        </el-checkbox>
      </el-form-item>

      <!-- 高级配置 -->
      <el-divider content-position="left">高级配置</el-divider>

      <!-- 应用ID -->
      <el-form-item label="应用ID" prop="app_id">
        <el-input
          v-model="formData.app_id"
          placeholder="可选，留空使用默认值"
          maxlength="100"
          clearable
        />
        <div style="color: #909399; font-size: 12px; margin-top: 4px;">
          💡 用于特定券商的应用认证
        </div>
      </el-form-item>

      <!-- 授权码 -->
      <el-form-item label="授权码" prop="auth_code">
        <el-input
          v-model="formData.auth_code"
          placeholder="可选，留空使用默认值"
          maxlength="100"
          clearable
        />
        <div style="color: #909399; font-size: 12px; margin-top: 4px;">
          💡 用于特定券商的授权认证
        </div>
      </el-form-item>

      <!-- 行情服务器 -->
      <el-form-item label="行情服务器" prop="md_node_name">
        <el-select
          v-model="formData.md_node_name"
          placeholder="可选，选择行情服务器节点"
          style="width: 100%;"
          clearable
        >
          <el-option
            v-for="node in mdNodeList"
            :key="node"
            :label="node"
            :value="node"
          />
        </el-select>
        <div style="color: #909399; font-size: 12px; margin-top: 4px;">
          💡 对应brokers.yaml中的行情节点配置
        </div>
      </el-form-item>

      <!-- 交易服务器 -->
      <el-form-item label="交易服务器" prop="td_node_name">
        <el-select
          v-model="formData.td_node_name"
          placeholder="可选，选择交易服务器节点"
          style="width: 100%;"
          clearable
        >
          <el-option
            v-for="node in tdNodeList"
            :key="node"
            :label="node"
            :value="node"
          />
        </el-select>
        <div style="color: #909399; font-size: 12px; margin-top: 4px;">
          💡 对应brokers.yaml中的交易节点配置
        </div>
      </el-form-item>

      <!-- 账户设置 -->
      <el-divider content-position="left">账户设置</el-divider>

      <!-- 是否激活 -->
      <el-form-item label="账户状态">
        <el-switch
          v-model="formData.is_active"
          active-text="激活"
          inactive-text="禁用"
        />
        <div style="color: #909399; font-size: 12px; margin-top: 4px;">
          💡 禁用的账户无法登录和交易
        </div>
      </el-form-item>

      <!-- 是否默认 -->
      <el-form-item label="默认账户">
        <el-switch
          v-model="formData.is_default"
          active-text="是"
          inactive-text="否"
        />
        <div style="color: #909399; font-size: 12px; margin-top: 4px;">
          💡 默认账户将在启动时自动登录
        </div>
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
import { getBrokers, addTradingAccount } from '@/api/tradingAccount'
import { useTradingAccountStore } from '@/stores/tradingAccount'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const tradingAccountStore = useTradingAccountStore()
const formRef = ref(null)
const loading = ref(false)
const brokerList = ref([])

// 模拟的服务器节点列表（实际应从后端获取）
const mdNodeList = ref(['MD_NODE_1', 'MD_NODE_2', 'MD_NODE_3'])
const tdNodeList = ref(['TD_NODE_1', 'TD_NODE_2', 'TD_NODE_3'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const formData = reactive({
  display_name: '',
  broker_key: '',
  broker_id: '',
  account_id: '',
  password: '',
  remember_password: false,
  app_id: '',
  auth_code: '',
  md_node_name: '',
  td_node_name: '',
  is_active: true,
  is_default: false
})

const rules = computed(() => ({
  display_name: [
    { required: true, message: '请输入账户名称', trigger: 'blur' },
    { min: 2, max: 100, message: '账户名称长度为2-100个字符', trigger: 'blur' }
  ],
  broker_key: [
    { required: true, message: '请选择开户机构', trigger: 'change' }
  ],
  broker_id: [
    { required: true, message: '请输入券商ID', trigger: 'blur' },
    { min: 1, max: 50, message: '券商ID长度为1-50个字符', trigger: 'blur' }
  ],
  account_id: [
    { required: true, message: '请输入资金账号', trigger: 'blur' },
    { min: 1, max: 100, message: '资金账号长度为1-100个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入交易密码', trigger: 'blur' },
    { min: 6, max: 100, message: '交易密码长度为6-100个字符', trigger: 'blur' }
  ],
  app_id: [
    { max: 100, message: '应用ID长度不超过100个字符', trigger: 'blur' }
  ],
  auth_code: [
    { max: 100, message: '授权码长度不超过100个字符', trigger: 'blur' }
  ],
  md_node_name: [
    { max: 50, message: '行情服务器节点名称长度不超过50个字符', trigger: 'blur' }
  ],
  td_node_name: [
    { max: 50, message: '交易服务器节点名称长度不超过50个字符', trigger: 'blur' }
  ]
}))

/**
 * 处理券商变化
 */
function handleBrokerChange(value) {
  // 可以根据选择的券商加载对应的节点配置
  const broker = brokerList.value.find(b => b.broker_key === value)
  if (broker) {
    // 这里可以根据券商类型加载不同的节点列表
    console.log('选择的券商:', broker)
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
        display_name: formData.display_name,
        broker_key: formData.broker_key,
        broker_id: formData.broker_id,
        account_id: formData.account_id,
        password: formData.password,
        remember_password: formData.remember_password,
        app_id: formData.app_id || null,
        auth_code: formData.auth_code || null,
        md_node_name: formData.md_node_name || null,
        td_node_name: formData.td_node_name || null,
        is_active: formData.is_active,
        is_default: formData.is_default
      }

      // 调用API添加账户
      await addTradingAccount(accountData)
      
      ElMessage.success('账户添加成功')
      emit('success')
      handleClose()
    } catch (error) {
      console.error('添加账户失败:', error)
      ElMessage.error(error.response?.data?.detail || '添加账户失败')
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
