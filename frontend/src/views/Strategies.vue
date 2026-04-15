<template>
  <div class="strategies">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>策略列表</span>
          <el-button type="primary" icon="Refresh" @click="fetchStrategies">刷新</el-button>
        </div>
      </template>

      <el-table :data="strategies" stripe v-loading="loading">
        <el-table-column prop="code" label="策略代码" width="150" />
        <el-table-column prop="name" label="策略名称" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="runStrategy(row.code)">
              运行
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { strategyApi, type Strategy } from '@/api'

const strategies = ref<Strategy[]>([])
const loading = ref(false)

const fetchStrategies = async () => {
  loading.value = true
  try {
    const data = await strategyApi.getList()
    strategies.value = data.strategies || []
  } catch (e) {
    ElMessage.error('获取策略列表失败')
  } finally {
    loading.value = false
  }
}

const runStrategy = async (code: string) => {
  try {
    await strategyApi.run(code)
    ElMessage.success(`策略 ${code} 已启动`)
  } catch (e) {
    ElMessage.error('运行策略失败')
  }
}

onMounted(() => {
  fetchStrategies()
})
</script>

<style scoped>
.strategies {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
