<template>
  <el-dialog
    v-model="visible"
    title="管理资金账户"
    width="800px"
    :close-on-click-modal="false"
  >
    <el-table :data="accountList" stripe>
      <el-table-column prop="display_name" label="账户名称" />
      <el-table-column prop="broker_id" label="券商ID" width="100" />
      <el-table-column prop="account_id" label="资金账号" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success" size="small">
            激活
          </el-tag>
          <el-tag v-else type="info" size="small">
            禁用
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
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
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
            type="danger"
            size="small"
            @click="handleDelete(row)"
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
        <el-form-item label="显示名称">
          <el-input v-model="editFormData.display_name" />
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
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Plus } from '@element-plus/icons-vue'
import { useTradingAccountStore } from '@/stores/tradingAccount'
import {
  updateTradingAccount,
  deleteTradingAccount,
  switchTradingAccount
} from '@/api/tradingAccount'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'add'])

const tradingAccountStore = useTradingAccountStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const accountList = computed(() => tradingAccountStore.accountList)

const editDialogVisible = ref(false)
const editFormRef = ref(null)
const editFormData = reactive({
  id: null,
  display_name: '',
  is_active: true
})

/**
 * 格式化日期时间
 */
function formatDateTime(dateTime) {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

/**
 * 设为默认
 */
async function handleSetDefault(row) {
  try {
    await switchTradingAccount(row.id)
    ElMessage.success('设置成功')
    await tradingAccountStore.fetchAccountList()
  } catch (error) {
    ElMessage.error('设置失败')
  }
}

/**
 * 编辑
 */
function handleEdit(row) {
  editFormData.id = row.id
  editFormData.display_name = row.display_name
  editFormData.is_active = row.is_active
  editDialogVisible.value = true
}

/**
 * 保存编辑
 */
async function handleSaveEdit() {
  try {
    await updateTradingAccount(editFormData.id, {
      display_name: editFormData.display_name,
      is_active: editFormData.is_active
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
    await ElMessageBox.confirm(
      `确定要删除账户 "${row.display_name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteTradingAccount(row.id)
    ElMessage.success('删除成功')
    await tradingAccountStore.fetchAccountList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

/**
 * 添加账户
 */
function handleAdd() {
  visible.value = false
  emit('add')
}
</script>

