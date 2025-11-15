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
          <p style="margin-top: 10px; color: #E6A23C;">提示：点击"添加账户"按钮后，请在弹出的对话框中填写完整信息。</p>
        </el-alert>

        <div style="text-align: center; padding: 20px;">
          <el-button
            type="primary"
            size="large"
            :icon="Plus"
            @click="showAddDialog = true"
          >
            添加资金账户
          </el-button>
          <p v-if="accountAdded" style="margin-top: 15px; color: #67C23A;">
            <el-icon><SuccessFilled /></el-icon>
            账户已添加成功！点击"下一步"继续
          </p>
        </div>
      </div>

      <!-- 添加账户对话框 -->
      <AddBrokerageAccountDialog
        v-model="showAddDialog"
        @success="handleAccountAdded"
      />

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
        @click="handleNext"
      >
        下一步
      </el-button>
      <el-button v-if="currentStep === 2" type="primary" @click="handleFinish">
        开始使用
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, SuccessFilled } from '@element-plus/icons-vue'
import { useBrokerageStore } from '@/stores/brokerage'
import AddBrokerageAccountDialog from './AddBrokerageAccountDialog.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'finish'])

const brokerageStore = useBrokerageStore()

const visible = ref(props.modelValue)
const currentStep = ref(0)
const showAddDialog = ref(false)
const accountAdded = ref(false)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

/**
 * 账户添加成功回调
 */
function handleAccountAdded() {
  accountAdded.value = true
  ElMessage.success('账户添加成功！')
}

/**
 * 下一步
 */
function handleNext() {
  if (currentStep.value === 0) {
    currentStep.value = 1
  } else if (currentStep.value === 1) {
    // 检查是否已添加账户
    if (!accountAdded.value) {
      ElMessage.warning('请先添加资金账户')
      return
    }
    currentStep.value = 2
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
  window.open('https://homalos.github.io/guide/quick_start', '_blank')
}
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

