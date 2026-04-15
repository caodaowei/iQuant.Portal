<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 系统状态卡片 -->
      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <div class="status-content">
            <el-icon class="status-icon" :class="systemStatus.database === 'connected' ? 'success' : 'error'">
              <CircleCheck v-if="systemStatus.database === 'connected'" />
              <CircleClose v-else />
            </el-icon>
            <div class="status-info">
              <div class="status-label">数据库</div>
              <div class="status-value">{{ systemStatus.database }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <div class="status-content">
            <el-icon class="status-icon" :class="systemStatus.redis === 'connected' ? 'success' : 'error'">
              <CircleCheck v-if="systemStatus.redis === 'connected'" />
              <CircleClose v-else />
            </el-icon>
            <div class="status-info">
              <div class="status-label">Redis 缓存</div>
              <div class="status-value">{{ systemStatus.redis }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <div class="status-content">
            <el-icon class="status-icon success">
              <Cpu />
            </el-icon>
            <div class="status-info">
              <div class="status-label">策略数量</div>
              <div class="status-value">{{ strategyCount }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <div class="status-content">
            <el-icon class="status-icon success">
              <TrendCharts />
            </el-icon>
            <div class="status-info">
              <div class="status-label">缓存命中率</div>
              <div class="status-value">{{ cacheStats.hit_rate }}%</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快速操作 -->
    <el-card class="quick-actions" shadow="never">
      <template #header>
        <div class="card-header">
          <span>快速操作</span>
        </div>
      </template>
      <el-space wrap>
        <el-button type="primary" icon="Cpu" @click="$router.push('/strategies')">
          策略管理
        </el-button>
        <el-button type="success" icon="TrendCharts" @click="$router.push('/backtest')">
          运行回测
        </el-button>
        <el-button type="warning" icon="Search" @click="$router.push('/diagnosis')">
          AI 诊断
        </el-button>
        <el-button type="info" icon="Database" @click="$router.push('/data')">
          数据同步
        </el-button>
      </el-space>
    </el-card>

    <!-- 最近活动 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>系统信息</span>
          <el-button size="small" icon="Refresh" @click="fetchSystemInfo">刷新</el-button>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="系统版本">
          {{ systemStatus.version || 'N/A' }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ systemStatus.timestamp ? new Date(systemStatus.timestamp).toLocaleString() : 'N/A' }}
        </el-descriptions-item>
        <el-descriptions-item label="缓存命中">
          {{ cacheStats.hits || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="缓存未命中">
          {{ cacheStats.misses || 0 }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { CircleCheck, CircleClose, Cpu, TrendCharts, Search, Database, Refresh } from '@element-plus/icons-vue'
import { systemApi, strategyApi } from '@/api'

const systemStatus = ref<any>({})
const cacheStats = ref<any>({})
const strategyCount = ref(0)

const fetchSystemInfo = async () => {
  try {
    const [status, cache, strategies] = await Promise.all([
      systemApi.getStatus(),
      systemApi.getCacheStats(),
      strategyApi.getList(),
    ])

    systemStatus.value = status
    cacheStats.value = cache
    strategyCount.value = strategies.count || 0
  } catch (e) {
    console.error('Failed to fetch system info:', e)
  }
}

onMounted(() => {
  fetchSystemInfo()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.status-card {
  margin-bottom: 20px;
}

.status-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-icon {
  font-size: 48px;
}

.status-icon.success {
  color: #67c23a;
}

.status-icon.error {
  color: #f56c6c;
}

.status-info {
  flex: 1;
}

.status-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 4px;
}

.status-value {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
  text-transform: capitalize;
}

.quick-actions {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
