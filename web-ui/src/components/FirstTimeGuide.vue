<template>
  <el-dialog
    v-model="visible"
    title="欢迎使用 Homalos 量化交易系统"
    width="600px"
    :close-on-click-modal="false"
    :show-close="false"
  >
    <el-steps :active="currentStep" finish-status="success" align-center>
      <el-step title="欢迎" />
      <el-step title="添加资金账户" />
      <el-step title="完成" />
    </el-steps>

    <div class="step-content">
      <!-- 步骤1：欢迎 -->
      <div v-show="currentStep === 0" class="step-panel">
        <el-result icon="success" title="欢迎使用">
          <template #sub-title>
            <p>您已成功注册系统账号！</p>
            <p>接下来让我们完成初始设置，添加您的资金账户。</p>
          </template>
        </el-result>
      </div>

      <!-- 步骤2：添加账户 -->
      <div v-show="currentStep === 1" class="step-panel">
        <el-alert
          title="为什么要添加资金账户？"
          type="info"
          :closable="false"
          style="margin-bottom: 20px;"
        >
          <p>资金账户用于连接券商系统进行实际交易。</p>
          <p>您可以添加模拟账户进行测试，或添加实盘账户进行真实交易。</p>
        </el-alert>

        <el-form :model="accountData" label-width="100px">
          <el-form-item label="开户机构">
            <el-select v-model="accountData.broker_id" placeholder="请选择">
              <el-option
                v-for="broker in brokerList"
                :key="broker.broker_key"
                :label="broker.name"
                :value="broker.broker_key"
              >
                <span>{{ broker.name }}</span>
                <span style="float: right; color: #8492a6; font-size: 13px;">
                  {{ broker.broker_id }}
                </span>
              </el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="资金账号">
            <el-input v-model="accountData.account_id" placeholder="请输入资金账号" />
          </el-form-item>
          <el-form-item label="账户密码">
            <el-input
              v-model="accountData.password"
              type="password"
              placeholder="请输入账户密码"
              show-password
            />
          </el-form-item>
          <el-form-item label="显示名称">
            <el-input v-model="accountData.display_name" placeholder="如：模拟账户1" />
          </el-form-item>
        </el-form>
      </div>

      <!-- 步骤3：完成 -->
      <div v-show="currentStep === 2" class="step-panel">
        <el-result icon="success" title="设置完成">
          <template #sub-title>
            <p>恭喜！您已完成初始设置。</p>
            <p>现在您可以开始使用系统的全部功能了。</p>
          </template>
          <template #extra>
            <el-button type="primary" @click="handleViewDocs">
              查看使用文档
            </el-button>
          </template>
        </el-result>
      </div>
    </div>

    <template #footer>
      <el-button v-if="currentStep > 0" @click="handlePrev">上一步</el-button>
      <el-button v-if="currentStep < 2" @click="handleSkip">跳过</el-button>
      <el-button
        v-if="currentStep < 2"
        type="primary"
        :loading="loading"
        @click="handleNext"
      >
        {{ currentStep === 1 ? '添加账户' : '下一步' }}
      </el-button>
      <el-button v-if="currentStep === 2" type="primary" @click="handleFinish">
        开始使用
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { addTradingAccount, getBrokers } from '@/api/tradingAccount'
import { useTradingAccountStore } from '@/stores/tradingAccount'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'finish'])

const tradingAccountStore = useTradingAccountStore()

const visible = ref(props.modelValue)
const currentStep = ref(0)
const loading = ref(false)
const brokerList = ref([])

const accountData = reactive({
  broker_id: '',
  account_id: '',
  password: '',
  display_name: '',
  is_default: true
})

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

/**
 * 下一步
 */
async function handleNext() {
  if (currentStep.value === 0) {
    currentStep.value = 1
  } else if (currentStep.value === 1) {
    // 验证表单
    if (!accountData.broker_id || !accountData.account_id || !accountData.password) {
      ElMessage.warning('请填写完整的账户信息')
      return
    }
    
    // 添加账户
    loading.value = true
    try {
      await addTradingAccount(accountData)
      await tradingAccountStore.fetchAccountList()
      ElMessage.success('账户添加成功')
      currentStep.value = 2
    } catch (error) {
      ElMessage.error('添加失败，请检查信息是否正确')
    } finally {
      loading.value = false
    }
  }
}

/**
 * 上一步
 */
function handlePrev() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

/**
 * 跳过
 */
function handleSkip() {
  // 标记引导已完成
  localStorage.setItem('homalos_guide_completed', 'true')
  visible.value = false
  emit('finish', false)
}

/**
 * 完成
 */
function handleFinish() {
  // 标记引导已完成
  localStorage.setItem('homalos_guide_completed', 'true')
  visible.value = false
  emit('finish', true)
}

/**
 * 查看文档
 */
function handleViewDocs() {
  window.open('https://github.com/homalos', '_blank')
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
})
</script>

<style scoped>
.step-content {
  margin: 40px 0;
  min-height: 300px;
}

.step-panel {
  padding: 20px 0;
}

.el-select {
  width: 100%;
}
</style>

