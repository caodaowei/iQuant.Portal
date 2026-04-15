<template>
  <div class="investment-ledger">
    <!-- 顶部：账户选择器 -->
    <el-card class="account-selector-card" shadow="never">
      <div class="account-selector">
        <el-select
          v-model="selectedAccountId"
          placeholder="选择账户"
          @change="onAccountChange"
          style="width: 300px"
        >
          <el-option
            v-for="account in accounts"
            :key="account.id"
            :label="account.account_name"
            :value="account.id"
          >
            <span>{{ account.account_name }}</span>
            <span style="float: right; color: #8492a6; font-size: 13px">
              ¥{{ formatNumber(account.total_capital) }}
            </span>
          </el-option>
        </el-select>
        <el-button type="primary" :icon="Refresh" @click="refreshAllData" :loading="loading">
          刷新
        </el-button>
      </div>
    </el-card>

    <!-- 关键指标卡片 -->
    <el-row :gutter="20" class="metrics-row">
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-content">
            <div class="metric-label">总资产</div>
            <div class="metric-value primary">
              ¥{{ formatNumber(currentAccount?.total_capital || 0) }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-content">
            <div class="metric-label">累计盈亏</div>
            <div
              class="metric-value"
              :class="currentAccount?.total_pnl >= 0 ? 'profit' : 'loss'"
            >
              {{ currentAccount?.total_pnl >= 0 ? '+' : ''
              }}{{ formatNumber(currentAccount?.total_pnl || 0) }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-content">
            <div class="metric-label">持仓市值</div>
            <div class="metric-value">
              ¥{{ formatNumber(currentAccount?.market_value || 0) }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-content">
            <div class="metric-label">可用资金</div>
            <div class="metric-value">
              ¥{{ formatNumber(currentAccount?.available_cash || 0) }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Tab 标签页 -->
    <el-card class="tab-card" shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <!-- Tab 1: 持仓总览 -->
        <el-tab-pane label="持仓总览" name="positions">
          <div v-loading="positionsLoading">
            <el-table :data="positions" stripe style="width: 100%" max-height="400">
              <el-table-column prop="stock_code" label="股票代码" width="100" />
              <el-table-column prop="stock_name" label="股票名称" width="120" />
              <el-table-column prop="total_volume" label="持仓数量" width="100" align="right" />
              <el-table-column prop="avg_cost" label="成本价" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPrice(row.avg_cost) }}
                </template>
              </el-table-column>
              <el-table-column prop="current_price" label="现价" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPrice(row.current_price) }}
                </template>
              </el-table-column>
              <el-table-column prop="market_value" label="市值" width="120" align="right">
                <template #default="{ row }">
                  ¥{{ formatNumber(row.market_value) }}
                </template>
              </el-table-column>
              <el-table-column prop="floating_pnl" label="浮动盈亏" width="120" align="right">
                <template #default="{ row }">
                  <span :class="row.floating_pnl >= 0 ? 'text-profit' : 'text-loss'">
                    {{ row.floating_pnl >= 0 ? '+' : '' }}{{ formatNumber(row.floating_pnl) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="floating_pnl_rate" label="盈亏比例" width="100" align="right">
                <template #default="{ row }">
                  <span :class="row.floating_pnl_rate >= 0 ? 'text-profit' : 'text-loss'">
                    {{ row.floating_pnl_rate >= 0 ? '+' : '' }}{{ row.floating_pnl_rate }}%
                  </span>
                </template>
              </el-table-column>
            </el-table>

            <!-- 持仓分布饼图 -->
            <div ref="positionPieChartRef" style="height: 350px; margin-top: 20px"></div>
          </div>
        </el-tab-pane>

        <!-- Tab 2: 交易记录 -->
        <el-tab-pane label="交易记录" name="trades">
          <div v-loading="tradesLoading">
            <!-- 筛选器 -->
            <el-form :inline="true" class="trade-filter">
              <el-form-item label="日期范围">
                <el-date-picker
                  v-model="tradeDateRange"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  value-format="YYYY-MM-DD"
                  @change="loadTradeHistory"
                />
              </el-form-item>
              <el-form-item label="交易类型">
                <el-select v-model="tradeTypeFilter" placeholder="全部" clearable @change="loadTradeHistory" style="width: 120px">
                  <el-option label="买入" value="buy" />
                  <el-option label="卖出" value="sell" />
                </el-select>
              </el-form-item>
            </el-form>

            <el-table :data="trades" stripe style="width: 100%" max-height="400">
              <el-table-column prop="fill_time" label="成交时间" width="160">
                <template #default="{ row }">
                  {{ formatDateTime(row.fill_time) }}
                </template>
              </el-table-column>
              <el-table-column prop="stock_code" label="股票代码" width="100" />
              <el-table-column prop="trade_type" label="方向" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.trade_type === 'buy' ? 'success' : 'danger'" size="small">
                    {{ row.trade_type === 'buy' ? '买入' : '卖出' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="fill_volume" label="成交量" width="100" align="right" />
              <el-table-column prop="fill_price" label="成交价" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPrice(row.fill_price) }}
                </template>
              </el-table-column>
              <el-table-column prop="fill_amount" label="成交额" width="120" align="right">
                <template #default="{ row }">
                  ¥{{ formatNumber(row.fill_amount) }}
                </template>
              </el-table-column>
              <el-table-column prop="commission" label="手续费" width="100" align="right">
                <template #default="{ row }">
                  ¥{{ formatNumber(row.commission + row.stamp_tax) }}
                </template>
              </el-table-column>
            </el-table>

            <!-- 分页 -->
            <el-pagination
              v-model:current-page="tradePage"
              v-model:page-size="tradePageSize"
              :total="tradeTotal"
              layout="total, prev, pager, next"
              @current-change="loadTradeHistory"
              style="margin-top: 20px; justify-content: center"
            />

            <!-- 盈亏分布柱状图 -->
            <div ref="dailyPnlChartRef" style="height: 300px; margin-top: 20px"></div>
          </div>
        </el-tab-pane>

        <!-- Tab 3: 资产趋势 -->
        <el-tab-pane label="资产趋势" name="assets">
          <div v-loading="assetHistoryLoading">
            <!-- 时间范围选择 -->
            <el-radio-group v-model="assetDays" @change="loadAssetHistory" style="margin-bottom: 20px">
              <el-radio-button :label="7">近7天</el-radio-button>
              <el-radio-button :label="30">近30天</el-radio-button>
              <el-radio-button :label="90">近90天</el-radio-button>
              <el-radio-button :label="180">近180天</el-radio-button>
            </el-radio-group>

            <!-- 资产净值曲线图 -->
            <div ref="assetChartRef" style="height: 400px"></div>
          </div>
        </el-tab-pane>

        <!-- Tab 4: 盈亏分析 -->
        <el-tab-pane label="盈亏分析" name="pnl">
          <div v-loading="pnlLoading">
            <!-- 统计卡片 -->
            <el-row :gutter="20" style="margin-bottom: 20px">
              <el-col :span="6">
                <el-statistic title="累计盈亏" :value="pnlStats?.realized_pnl || 0" :precision="2">
                  <template #prefix>
                    <span :style="{ color: (pnlStats?.realized_pnl || 0) >= 0 ? '#67c23a' : '#f56c6c' }">
                      {{ (pnlStats?.realized_pnl || 0) >= 0 ? '+' : '' }}¥
                    </span>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="6">
                <el-statistic title="胜率" :value="pnlStats?.win_rate || 0" :precision="2" suffix="%" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="交易次数" :value="pnlStats?.total_trades || 0" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="平均持仓天数" :value="pnlStats?.avg_holding_days || 0" suffix="天" />
              </el-col>
            </el-row>

            <!-- 按股票盈亏排行 -->
            <h3 style="margin: 20px 0 10px">按股票盈亏排行</h3>
            <el-table :data="pnlByStock" stripe style="width: 100%" max-height="300">
              <el-table-column prop="stock_code" label="股票代码" width="100" />
              <el-table-column prop="stock_name" label="股票名称" width="120" />
              <el-table-column prop="total_buy_volume" label="买入总量" width="100" align="right" />
              <el-table-column prop="total_sell_volume" label="卖出总量" width="100" align="right" />
              <el-table-column prop="total_fees" label="总费用" width="100" align="right">
                <template #default="{ row }">
                  ¥{{ formatNumber(row.total_fees) }}
                </template>
              </el-table-column>
              <el-table-column prop="realized_pnl" label="实现盈亏" align="right">
                <template #default="{ row }">
                  <span :class="row.realized_pnl >= 0 ? 'text-profit' : 'text-loss'">
                    {{ row.realized_pnl >= 0 ? '+' : '' }}¥{{ formatNumber(row.realized_pnl) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { ledgerApi, type LedgerAccount, type PositionWithQuote, type TradeRecord, type AssetHistory, type PnlStatistics, type PnlByStock, type DailyPnl } from '@/api'

// 状态管理
const selectedAccountId = ref<number>(1)
const activeTab = ref('positions')
const loading = ref(false)
const positionsLoading = ref(false)
const tradesLoading = ref(false)
const assetHistoryLoading = ref(false)
const pnlLoading = ref(false)

// 数据
const accounts = ref<LedgerAccount[]>([])
const currentAccount = ref<LedgerAccount | null>(null)
const positions = ref<PositionWithQuote[]>([])
const trades = ref<TradeRecord[]>([])
const tradeTotal = ref(0)
const tradePage = ref(1)
const tradePageSize = ref(50)
const tradeDateRange = ref<[string, string] | null>(null)
const tradeTypeFilter = ref<string>('')
const assetHistory = ref<AssetHistory[]>([])
const assetDays = ref(90)
const pnlStats = ref<PnlStatistics | null>(null)
const pnlByStock = ref<PnlByStock[]>([])
const dailyPnlData = ref<DailyPnl[]>([])

// 图表引用
const positionPieChartRef = ref<HTMLElement>()
const dailyPnlChartRef = ref<HTMLElement>()
const assetChartRef = ref<HTMLElement>()

let positionPieChart: echarts.ECharts | null = null
let dailyPnlChart: echarts.ECharts | null = null
let assetChart: echarts.ECharts | null = null

// 格式化函数
const formatNumber = (num: number) => {
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatPrice = (price: number) => {
  return price.toFixed(2)
}

const formatDateTime = (datetime: string) => {
  return new Date(datetime).toLocaleString('zh-CN')
}

// 加载账户列表
const loadAccounts = async () => {
  try {
    const res = await ledgerApi.getAccounts()
    accounts.value = res.data.accounts
    if (accounts.value.length > 0 && !currentAccount.value) {
      const defaultAccount = accounts.value.find(a => a.is_default) || accounts.value[0]
      selectedAccountId.value = defaultAccount.id
      currentAccount.value = defaultAccount
      await refreshAllData()
    }
  } catch (error) {
    ElMessage.error('获取账户列表失败')
  }
}

// 账户切换
const onAccountChange = async (accountId: number) => {
  currentAccount.value = accounts.value.find(a => a.id === accountId) || null
  await refreshAllData()
}

// 刷新所有数据
const refreshAllData = async () => {
  if (!selectedAccountId.value) return
  
  loading.value = true
  try {
    await Promise.all([
      loadPositions(),
      loadTradeHistory(),
      loadAssetHistory(),
      loadPnlSummary(),
    ])
  } finally {
    loading.value = false
  }
}

// Tab 切换
const onTabChange = async (tabName: string) => {
  await nextTick()
  
  if (tabName === 'positions' && positions.value.length > 0) {
    renderPositionPieChart()
  } else if (tabName === 'trades' && trades.value.length > 0) {
    renderDailyPnlChart()
  } else if (tabName === 'assets' && assetHistory.value.length > 0) {
    renderAssetChart()
  }
}

// 加载持仓
const loadPositions = async () => {
  positionsLoading.value = true
  try {
    const res = await ledgerApi.getPositions(selectedAccountId.value)
    positions.value = res.data.positions
    await nextTick()
    renderPositionPieChart()
  } catch (error) {
    ElMessage.error('获取持仓失败')
  } finally {
    positionsLoading.value = false
  }
}

// 加载交易历史
const loadTradeHistory = async () => {
  tradesLoading.value = true
  try {
    const params: any = {
      account_id: selectedAccountId.value,
      limit: tradePageSize.value,
      offset: (tradePage.value - 1) * tradePageSize.value,
    }
    
    if (tradeDateRange.value) {
      params.start_date = tradeDateRange.value[0]
      params.end_date = tradeDateRange.value[1]
    }
    
    if (tradeTypeFilter.value) {
      params.trade_type = tradeTypeFilter.value
    }
    
    const res = await ledgerApi.getTradeHistory(params)
    trades.value = res.data.trades
    tradeTotal.value = res.data.total
    
    await nextTick()
    loadDailyPnlForChart()
  } catch (error) {
    ElMessage.error('获取交易历史失败')
  } finally {
    tradesLoading.value = false
  }
}

// 加载资产历史
const loadAssetHistory = async () => {
  assetHistoryLoading.value = true
  try {
    const res = await ledgerApi.getAssetHistory(selectedAccountId.value, assetDays.value)
    assetHistory.value = res.data.history
    await nextTick()
    renderAssetChart()
  } catch (error) {
    ElMessage.error('获取资产历史失败')
  } finally {
    assetHistoryLoading.value = false
  }
}

// 加载盈亏统计
const loadPnlSummary = async () => {
  pnlLoading.value = true
  try {
    const [statsRes, byStockRes, dailyRes] = await Promise.all([
      ledgerApi.getPnlSummary(selectedAccountId.value),
      ledgerApi.getPnlByStock(selectedAccountId.value),
      ledgerApi.getDailyPnl(selectedAccountId.value, 30),
    ])
    
    pnlStats.value = statsRes.data
    pnlByStock.value = byStockRes.data.pnl_by_stock
    dailyPnlData.value = dailyRes.data.daily_pnl
    
    await nextTick()
    renderDailyPnlChart()
  } catch (error) {
    ElMessage.error('获取盈亏统计失败')
  } finally {
    pnlLoading.value = false
  }
}

// 加载每日盈亏数据用于图表
const loadDailyPnlForChart = async () => {
  try {
    const res = await ledgerApi.getDailyPnl(selectedAccountId.value, 30)
    dailyPnlData.value = res.data.daily_pnl
    await nextTick()
    renderDailyPnlChart()
  } catch (error) {
    console.error('加载每日盈亏失败', error)
  }
}

// 渲染持仓饼图
const renderPositionPieChart = () => {
  if (!positionPieChartRef.value || positions.value.length === 0) return
  
  if (!positionPieChart) {
    positionPieChart = echarts.init(positionPieChartRef.value)
  }
  
  const option = {
    title: {
      text: '持仓分布',
      left: 'center',
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: ¥{c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle',
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        data: positions.value.map(p => ({
          name: p.stock_name || p.stock_code,
          value: p.market_value,
        })),
        label: {
          formatter: '{b}\n{d}%',
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      },
    ],
  }
  
  positionPieChart.setOption(option)
}

// 渲染每日盈亏柱状图
const renderDailyPnlChart = () => {
  if (!dailyPnlChartRef.value || dailyPnlData.value.length === 0) return
  
  if (!dailyPnlChart) {
    dailyPnlChart = echarts.init(dailyPnlChartRef.value)
  }
  
  const dates = dailyPnlData.value.map(d => d.date)
  const pnls = dailyPnlData.value.map(d => d.pnl)
  
  const option = {
    title: {
      text: '每日盈亏分布',
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
      },
    },
    xAxis: {
      type: 'category',
      data: dates,
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        type: 'bar',
        data: pnls.map(v => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? '#67c23a' : '#f56c6c',
          },
        })),
      },
    ],
  }
  
  dailyPnlChart.setOption(option)
}

// 渲染资产净值曲线图
const renderAssetChart = () => {
  if (!assetChartRef.value || assetHistory.value.length === 0) return
  
  if (!assetChart) {
    assetChart = echarts.init(assetChartRef.value)
  }
  
  const dates = assetHistory.value.map(h => h.date)
  const assets = assetHistory.value.map(h => h.total_asset)
  const navs = assetHistory.value.map(h => ((h.nav - 1) * 100).toFixed(2))
  
  const option = {
    title: {
      text: '资产净值曲线',
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0].axisValue
        const asset = params[0].value
        const nav = params[1].value
        return `${date}<br/>总资产: ¥${asset.toLocaleString()}<br/>收益率: ${nav}%`
      },
    },
    legend: {
      data: ['总资产', '收益率'],
      top: 30,
    },
    xAxis: {
      type: 'category',
      data: dates,
    },
    yAxis: [
      {
        type: 'value',
        name: '资产(元)',
        position: 'left',
      },
      {
        type: 'value',
        name: '收益率(%)',
        position: 'right',
      },
    ],
    series: [
      {
        name: '总资产',
        type: 'line',
        data: assets,
        smooth: true,
        areaStyle: { opacity: 0.3 },
      },
      {
        name: '收益率',
        type: 'line',
        yAxisIndex: 1,
        data: navs,
        smooth: true,
        lineStyle: { type: 'dashed' },
      },
    ],
  }
  
  assetChart.setOption(option)
}

// 窗口resize处理
const handleResize = () => {
  positionPieChart?.resize()
  dailyPnlChart?.resize()
  assetChart?.resize()
}

// 生命周期
onMounted(() => {
  loadAccounts()
  window.addEventListener('resize', handleResize)
})

// 清理
import { onUnmounted } from 'vue'
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  positionPieChart?.dispose()
  dailyPnlChart?.dispose()
  assetChart?.dispose()
})
</script>

<style scoped>
.investment-ledger {
  padding: 20px;
}

.account-selector-card {
  margin-bottom: 20px;
}

.account-selector {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metrics-row {
  margin-bottom: 20px;
}

.metric-card {
  text-align: center;
}

.metric-content {
  padding: 10px 0;
}

.metric-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
}

.metric-value.primary {
  color: #409eff;
}

.metric-value.profit {
  color: #67c23a;
}

.metric-value.loss {
  color: #f56c6c;
}

.tab-card {
  min-height: 500px;
}

.trade-filter {
  margin-bottom: 20px;
}

.text-profit {
  color: #67c23a;
  font-weight: bold;
}

.text-loss {
  color: #f56c6c;
  font-weight: bold;
}
</style>
