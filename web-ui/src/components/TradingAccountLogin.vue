<template>
  <el-dialog
    v-model="visible"
    title="登录资金账户"
    width="500px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
    >
      <!-- 选择已有账户或新账户 -->
      <el-form-item label="登录方式">
        <el-radio-group v-model="loginMode">
          <el-radio label="existing" :disabled="!hasAccounts">
            使用已有账户
          </el-radio>
          <el-radio label="new">
            输入新账户
          </el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- 已有账户选择 -->
      <el-form-item
        v-if="loginMode === 'existing'"
        label="选择账户"
        prop="account_id"
      >
        <el-select
          v-model="formData.account_id"
          placeholder="请选择账户"
          style="width: 100%;"
        >
          <el-option
            v-for="account in accountList"
            :key="account.id"
            :label="account.display_name"
            :value="account.id"
          >
            <span>{{ account.display_name }}</span>
            <span style="float: right; color: #8492a6; font-size: 13px;">
              {{ account.broker_id }} - {{ account.account_id }}
            </span>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 新账户输入 -->
      <template v-if="loginMode === 'new'">
        <el-form-item label="开户机构" prop="broker_key">
          <el-select
            v-model="formData.broker_key"
            placeholder="请选择开户机构"
            style="width: 100%;"
          >
            <el-option
              v-for="broker in brokerList"
              :key="broker.broker_key"
              :label="broker.name"
              :value="broker.broker_key"
            >
              <span>{{ broker.name }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="资金账户" prop="account_number">
          <el-input
            v-model="formData.account_number"
            placeholder="请输入资金账户"
          />
        </el-form-item>

        <el-form-item label="应用ID">
          <el-input
            v-model="formData.app_id"
            placeholder="可选，留空使用默认值"
          />
        </el-form-item>

        <el-form-item label="授权码">
          <el-input
            v-model="formData.auth_code"
            placeholder="可选，留空使用默认值"
          />
        </el-form-item>
      </template>

      <!-- 密码（两种模式都需要） -->
      <el-form-item label="交易密码" prop="password">
        <el-input
          v-model="formData.password"
          type="password"
          placeholder="请输入交易密码"
          show-password
          @keyup.enter="handleLogin"
        />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useTradingAccountStore } from '@/stores/tradingAccount'
import { getBrokers } from '@/api/tradingAccount'

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
const loginMode = ref('existing')
const brokerList = ref([])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const hasAccounts = computed(() => tradingAccountStore.accountList.length > 0)
const accountList = computed(() => tradingAccountStore.accountList)

const formData = reactive({
  account_id: null,
  broker_key: '',
  account_number: '',
  app_id: '',
  auth_code: '',
  password: '',
  remember: false
})

const rules = {
  account_id: [
    { required: true, message: '请选择账户', trigger: 'change' }
  ],
  broker_key: [
    { required: true, message: '请选择开户机构', trigger: 'change' }
  ],
  account_number: [
    { required: true, message: '请输入资金账号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ]
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
        password: formData.password,
        remember: formData.remember
      }
      
      if (loginMode.value === 'existing') {
        loginData.account_id = formData.account_id
      } else {
        loginData.broker_key = formData.broker_key
        loginData.account_number = formData.account_number
        if (formData.app_id) loginData.app_id = formData.app_id
        if (formData.auth_code) loginData.auth_code = formData.auth_code
      }
      
      const result = await tradingAccountStore.login(loginData)
      
      if (result.success) {
        ElMessage.success('登录成功')
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
  // 清空新增的字段
  formData.app_id = ''
  formData.auth_code = ''
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
  }
}

onMounted(() => {
  loadBrokers()
  
  // 如果没有账户，默认使用新账户模式
  if (!hasAccounts.value) {
    loginMode.value = 'new'
  }
})
</script>

<style scoped>
.el-select {
  width: 100%;
}
</style>

