<template>
  <div class="backtest">
    <el-row :gutter="20">
      <!-- 参数配置 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>回测参数</span>
          </template>

          <el-form :model="form" label-width="100px">
            <el-form-item label="策略">
              <el-select v-model="form.strategy" placeholder="选择策略" style="width: 100%">
                <el-option
                  v-for="s in strategies"
                  :key="s.code"
                  :label="s.name"
                  :value="s.code"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="回测天数">
              <el-input-number v-model="form.days" :min="30" :max="3650" style="width: 100%" />
            </el-form-item>

            <el-form-item label="初始资金">
              <el-input-number
                v-model="form.initial_capital"
                :min="10000"
                :step="10000"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="running" @click="runBacktest" style="width: 100%">
                {{ running ? '回测中...' : '开始回测' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 结果展示 -->
      <el-col :span="16">
        <el-card v-if="result">
          <template #header>
            <span>回测结果</span>
          </template>

          <el-descriptions :column="3" border>
            <el-descriptions-item label="总收益率">
              <span :class="result.total_return >= 0 ? 'positive' : 'negative'">
                {{ (result.total_return * 100).toFixed(2) }}%
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="年化收益">
              {{ (result.annualized_return * 100).toFixed(2) }}%
            </el-descriptions-item>
            <el-descriptions-item label="最大回撤">
              <span class="negative">{{ (result.max_drawdown * 100).toFixed(2) }}%</span>
            </el-descriptions-item>
            <el-descriptions-item label="夏普比率">
              {{ result.sharpe_ratio.toFixed(2) }}
            </el-descriptions-item>
            <el-descriptions-item label="交易次数">
              {{ result.total_trades }}
            </el-descriptions-item>
            <el-descriptions-item label="回测区间">
              {{ result.start_date }} ~ {{ result.end_date }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- 净值曲线图表 -->
          <div ref="chartRef" style="height: 400px; margin-top: 20px"></div>
        </el-card>

        <el-empty v-else description="请配置参数并开始回测" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { strategyApi, backtestApi, type Strategy, type BacktestResult } from '@/api'

const strategies = ref<Strategy[]>([])
const form = ref({
  strategy: 'MA_TREND',
  days: 300,
  initial_capital: 1000000,
})

const running = ref(false)
const result = ref<BacktestResult | null>(null)
const chartRef = ref<HTMLElement>()

const fetchStrategies = async () => {
  try {
    const data = await strategyApi.getList()
    strategies.value = data.strategies || []
  } catch (e) {
    ElMessage.error('获取策略列表失败')
  }
}

const runBacktest = async () => {
  running.value = true
  try {
    result.value = await backtestApi.runSync(form.value)
    ElMessage.success('回测完成')

    // 渲染图表
    await nextTick()
    renderChart()
  } catch (e) {
    ElMessage.error('回测失败')
  } finally {
    running.value = false
  }
}

const renderChart = () => {
  if (!chartRef.value || !result.value?.chart) return

  const chart = echarts.init(chartRef.value)
  const option = {
    title: { text: '净值曲线' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: result.value.chart.dates || [] },
    yAxis: { type: 'value' },
    series: [
      {
        name: '净值',
        type: 'line',
        data: result.value.chart.nav || [],
        smooth: true,
        areaStyle: { opacity: 0.3 },
      },
    ],
  }
  chart.setOption(option)
}

onMounted(() => {
  fetchStrategies()
})
</script>

<style scoped>
.backtest {
  padding: 20px;
}

.positive {
  color: #67c23a;
  font-weight: bold;
}

.negative {
  color: #f56c6c;
  font-weight: bold;
}
</style>
