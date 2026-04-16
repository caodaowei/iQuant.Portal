<template>
  <div class="investment-ledger">
    <!-- 顶部：账户选择器 -->
    <el-card class="account-selector-card" shadow="never">
      <div class="account-selector">
        <!-- 账户不多时使用多选卡片 -->
        <div v-if="accounts.length < 5" class="account-cards">
          <div
            v-for="account in accounts"
            :key="account.id"
            class="account-card"
            :class="{ active: selectedAccountIds.includes(account.id) }"
            @click="toggleAccountSelection(account.id)"
          >
            <div class="account-name">{{ account.account_name }}</div>
            <div class="account-balance">¥{{ formatNumber(account.total_capital) }}</div>
            <div class="account-status" v-if="selectedAccountIds.includes(account.id)">
              <el-icon><Check /></el-icon>
            </div>
          </div>
        </div>
        <!-- 账户较多时使用下拉选择 -->
        <el-select
          v-else
          v-model="selectedAccountIds"
          multiple
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
        <div class="account-actions">
          <el-button type="primary" :icon="Refresh" @click="refreshAllData" :loading="loading">
            刷新
          </el-button>
          <el-button type="success" @click="openAddAccountDialog">
            <el-icon><Plus /></el-icon>
            添加账户
          </el-button>
          <el-dropdown @command="handleAccountAction">
            <el-button type="info">
              账户管理
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">编辑当前账户</el-dropdown-item>
                <el-dropdown-item command="delete" type="danger">删除当前账户</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-card>

    <!-- 添加账户弹窗 -->
    <el-dialog
      v-model="addAccountDialogVisible"
      title="添加交易账户"
      width="400px"
    >
      <el-form :model="addAccountForm" :rules="addAccountRules" ref="addAccountFormRef">
        <el-form-item label="账户名称" prop="account_name">
          <el-input v-model="addAccountForm.account_name" placeholder="请输入账户名称" />
        </el-form-item>
        <el-form-item label="账户类型" prop="account_type">
          <el-select v-model="addAccountForm.account_type" placeholder="请选择账户类型">
            <el-option label="模拟账户" value="simulation" />
            <el-option label="实盘账户" value="real" />
          </el-select>
        </el-form-item>
        <el-form-item label="初始资金" prop="initial_capital">
          <el-input-number
            v-model="addAccountForm.initial_capital"
            :min="1000"
            :max="10000000"
            :step="1000"
            placeholder="请输入初始资金"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="addAccountForm.is_default">设为默认账户</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="addAccountDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleAddAccount">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑账户弹窗 -->
    <el-dialog
      v-model="editAccountDialogVisible"
      title="编辑交易账户"
      width="400px"
    >
      <el-form :model="editAccountForm" :rules="editAccountRules" ref="editAccountFormRef">
        <el-form-item label="账户名称" prop="account_name">
          <el-input v-model="editAccountForm.account_name" placeholder="请输入账户名称" />
        </el-form-item>
        <el-form-item label="账户类型" prop="account_type">
          <el-select v-model="editAccountForm.account_type" placeholder="请选择账户类型">
            <el-option label="模拟账户" value="simulation" />
            <el-option label="实盘账户" value="real" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="editAccountForm.is_default">设为默认账户</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editAccountDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleUpdateAccount">确定</el-button>
        </span>
      </template>
    </el-dialog>

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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, ArrowDown, Check } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { ledgerApi, type LedgerAccount, type PositionWithQuote, type TradeRecord, type AssetHistory, type PnlStatistics, type PnlByStock, type DailyPnl } from '@/api'

// 状态管理
const selectedAccountId = ref<number>(1)
const selectedAccountIds = ref<number[]>([])
const activeTab = ref('positions')
const loading = ref(false)
const positionsLoading = ref(false)
const tradesLoading = ref(false)
const assetHistoryLoading = ref(false)
const pnlLoading = ref(false)

// 账号管理相关状态
const addAccountDialogVisible = ref(false)
const editAccountDialogVisible = ref(false)
const addAccountForm = ref({
  account_name: '',
  account_type: 'simulation',
  initial_capital: 100000,
  is_default: false
})
const editAccountForm = ref({
  account_name: '',
  account_type: 'simulation',
  is_default: false
})
const addAccountFormRef = ref()
const editAccountFormRef = ref()

// 表单验证规则
const addAccountRules = {
  account_name: [
    { required: true, message: '请输入账户名称', trigger: 'blur' },
    { min: 2, max: 20, message: '账户名称长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  account_type: [
    { required: true, message: '请选择账户类型', trigger: 'change' }
  ],
  initial_capital: [
    { required: true, message: '请输入初始资金', trigger: 'blur' },
    { type: 'number', min: 1000, message: '初始资金至少为 1000 元', trigger: 'blur' }
  ]
}

const editAccountRules = {
  account_name: [
    { required: true, message: '请输入账户名称', trigger: 'blur' },
    { min: 2, max: 20, message: '账户名称长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  account_type: [
    { required: true, message: '请选择账户类型', trigger: 'change' }
  ]
}

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
    // 排序：实盘账户排在前面，模拟账户排在后面
    accounts.value = res.accounts.sort((a, b) => {
      if (a.account_type === 'real' && b.account_type !== 'real') {
        return -1
      } else if (a.account_type !== 'real' && b.account_type === 'real') {
        return 1
      } else {
        return 0
      }
    })
    if (accounts.value.length > 0) {
      // 尝试从 localStorage 中读取之前的选择
      let savedSelectedIds: number[] = []
      try {
        const saved = localStorage.getItem('selectedAccountIds')
        if (saved) {
          savedSelectedIds = JSON.parse(saved)
        }
      } catch (e) {
        console.error('读取保存的账户选择失败', e)
      }
      
      // 过滤出有效的账户 ID
      const validSelectedIds = savedSelectedIds.filter(id => 
        accounts.value.some(account => account.id === id)
      )
      
      if (validSelectedIds.length > 0) {
        // 使用保存的选择
        selectedAccountIds.value = validSelectedIds
        // 使用第一个选中的账户作为当前账户
        const firstSelectedAccount = accounts.value.find(a => a.id === validSelectedIds[0])
        if (firstSelectedAccount) {
          currentAccount.value = firstSelectedAccount
        } else {
          currentAccount.value = accounts.value[0]
        }
      } else {
        // 没有保存的选择，使用默认账户
        const defaultAccount = accounts.value.find(a => a.is_default) || accounts.value[0]
        selectedAccountIds.value = [defaultAccount.id]
        currentAccount.value = defaultAccount
      }
      
      // 保存选择到 localStorage
      localStorage.setItem('selectedAccountIds', JSON.stringify(selectedAccountIds.value))
      
      await refreshAllData()
    } else {
      // 账户列表为空，重置状态
      selectedAccountIds.value = []
      currentAccount.value = null
      ElMessage.warning('暂无交易账户，请添加账户')
    }
  } catch (error) {
    ElMessage.error('获取账户列表失败')
    // 出错时重置状态
    selectedAccountIds.value = []
    currentAccount.value = null
  }
}

// 打开添加账户弹窗
const openAddAccountDialog = () => {
  // 重置表单
  addAccountForm.value = {
    account_name: '',
    account_type: 'simulation',
    initial_capital: 100000,
    is_default: false
  }
  addAccountDialogVisible.value = true
}

// 处理添加账户
const handleAddAccount = async () => {
  // 表单验证
  if (!addAccountFormRef.value) return
  await addAccountFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await ledgerApi.addAccount(addAccountForm.value)
        ElMessage.success('账户添加成功')
        addAccountDialogVisible.value = false
        await loadAccounts()
      } catch (error) {
        ElMessage.error('添加账户失败')
      }
    }
  })
}

// 处理账户操作
const handleAccountAction = async (command) => {
  if (command === 'edit') {
    await openEditAccountDialog()
  } else if (command === 'delete') {
    await handleDeleteAccount()
  }
}

// 打开编辑账户弹窗
const openEditAccountDialog = async () => {
  if (!currentAccount.value) return
  
  // 填充表单数据
  editAccountForm.value = {
    account_name: currentAccount.value.account_name,
    account_type: currentAccount.value.account_type,
    is_default: currentAccount.value.is_default
  }
  editAccountDialogVisible.value = true
}

// 处理更新账户
const handleUpdateAccount = async () => {
  if (!currentAccount.value) return
  
  // 表单验证
  if (!editAccountFormRef.value) return
  await editAccountFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await ledgerApi.updateAccount(currentAccount.value.id, editAccountForm.value)
        ElMessage.success('账户更新成功')
        editAccountDialogVisible.value = false
        await loadAccounts()
      } catch (error) {
        ElMessage.error('更新账户失败')
      }
    }
  })
}

// 处理删除账户
const handleDeleteAccount = async () => {
  if (!currentAccount.value) return
  
  try {
    await ElMessageBox.confirm(
      '确定要删除当前账户吗？删除后将无法恢复。',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await ledgerApi.deleteAccount(currentAccount.value.id)
    ElMessage.success('账户删除成功')
    await loadAccounts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除账户失败')
    }
  }
}

// 账户切换
const onAccountChange = async (accountIds: number[]) => {
  if (accountIds.length === 0) {
    // 没有选择任何账户，重置状态
    currentAccount.value = null
    ElMessage.warning('请选择至少一个账户')
  } else {
    // 使用第一个选中的账户作为当前账户
    const account = accounts.value.find(a => a.id === accountIds[0])
    if (account) {
      currentAccount.value = account
      // 保存选择到 localStorage
      localStorage.setItem('selectedAccountIds', JSON.stringify(accountIds))
      await refreshAllData()
    } else {
      ElMessage.error('选择的账户不存在')
      // 重置为默认账户
      if (accounts.value.length > 0) {
        const defaultAccount = accounts.value.find(a => a.is_default) || accounts.value[0]
        selectedAccountIds.value = [defaultAccount.id]
        // 保存选择到 localStorage
        localStorage.setItem('selectedAccountIds', JSON.stringify(selectedAccountIds.value))
        currentAccount.value = defaultAccount
        await refreshAllData()
      } else {
        selectedAccountIds.value = []
        // 保存选择到 localStorage
        localStorage.setItem('selectedAccountIds', JSON.stringify(selectedAccountIds.value))
        currentAccount.value = null
      }
    }
  }
}

// 切换账户选择（用于卡片点击）
const toggleAccountSelection = (accountId: number) => {
  const index = selectedAccountIds.value.indexOf(accountId)
  if (index > -1) {
    // 已选中，取消选择
    selectedAccountIds.value.splice(index, 1)
  } else {
    // 未选中，添加选择
    selectedAccountIds.value.push(accountId)
  }
  // 保存选择到 localStorage
  localStorage.setItem('selectedAccountIds', JSON.stringify(selectedAccountIds.value))
  // 触发账户变更
  onAccountChange(selectedAccountIds.value)
}

// 刷新所有数据
const refreshAllData = async () => {
  if (selectedAccountIds.value.length === 0 || !currentAccount.value) {
    ElMessage.warning('请先选择一个账户')
    return
  }
  
  loading.value = true
  try {
    await Promise.all([
      loadPositions(),
      loadTradeHistory(),
      loadAssetHistory(),
      loadPnlSummary(),
    ])
  } catch (error) {
    ElMessage.error('刷新数据失败')
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
    if (selectedAccountIds.value.length === 0) {
      ElMessage.warning('请先选择一个账户')
      return
    }
    const res = await ledgerApi.getPositions(selectedAccountIds.value[0])
    positions.value = res.positions
    await nextTick()
    renderPositionPieChart()
  } catch (error) {
    console.error('获取持仓失败:', error)
    ElMessage.error('获取持仓失败')
  } finally {
    positionsLoading.value = false
  }
}

// 加载交易历史
const loadTradeHistory = async () => {
  tradesLoading.value = true
  try {
    if (selectedAccountIds.value.length === 0) {
      ElMessage.warning('请先选择一个账户')
      return
    }
    const params: any = {
      account_id: selectedAccountIds.value[0],
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
    trades.value = res.trades
    tradeTotal.value = res.total
    
    await nextTick()
    loadDailyPnlForChart()
  } catch (error) {
    console.error('获取交易历史失败:', error)
    ElMessage.error('获取交易历史失败')
  } finally {
    tradesLoading.value = false
  }
}

// 加载资产历史
const loadAssetHistory = async () => {
  assetHistoryLoading.value = true
  try {
    if (selectedAccountIds.value.length === 0) {
      ElMessage.warning('请先选择一个账户')
      return
    }
    const res = await ledgerApi.getAssetHistory(selectedAccountIds.value[0], assetDays.value)
    assetHistory.value = res.history
    await nextTick()
    renderAssetChart()
  } catch (error) {
    console.error('获取资产历史失败:', error)
    ElMessage.error('获取资产历史失败')
  } finally {
    assetHistoryLoading.value = false
  }
}

// 加载盈亏统计
const loadPnlSummary = async () => {
  pnlLoading.value = true
  try {
    if (selectedAccountIds.value.length === 0) {
      ElMessage.warning('请先选择一个账户')
      return
    }
    const [statsRes, byStockRes, dailyRes] = await Promise.all([
      ledgerApi.getPnlSummary(selectedAccountIds.value[0]),
      ledgerApi.getPnlByStock(selectedAccountIds.value[0]),
      ledgerApi.getDailyPnl(selectedAccountIds.value[0], 30),
    ])
    
    pnlStats.value = statsRes
    pnlByStock.value = byStockRes.pnl_by_stock
    dailyPnlData.value = dailyRes.daily_pnl
    
    await nextTick()
    renderDailyPnlChart()
  } catch (error) {
    console.error('获取盈亏统计失败:', error)
    ElMessage.error('获取盈亏统计失败')
  } finally {
    pnlLoading.value = false
  }
}

// 加载每日盈亏数据用于图表
const loadDailyPnlForChart = async () => {
  try {
    if (selectedAccountIds.value.length === 0) {
      return
    }
    const res = await ledgerApi.getDailyPnl(selectedAccountIds.value[0], 30)
    dailyPnlData.value = res.daily_pnl
    await nextTick()
    renderDailyPnlChart()
  } catch (error) {
    console.error('加载每日盈亏失败:', error)
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

.account-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.account-cards {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
  align-items: center;
}

.account-card {
  padding: 15px 20px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 150px;
  text-align: center;
  position: relative;
}

.account-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.account-card.active {
  border-color: #409eff;
  background-color: #ecf5ff;
  box-shadow: 0 2px 12px 0 rgba(64, 158, 255, 0.2);
}

.account-name {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 5px;
  color: #303133;
}

.account-balance {
  font-size: 14px;
  color: #606266;
}

.account-status {
  position: absolute;
  top: 10px;
  right: 10px;
  color: #409eff;
  font-size: 16px;
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
  color: #e74c3c;
}

.metric-value.loss {
  color: #27ae60;
}

.tab-card {
  min-height: 500px;
}

.trade-filter {
  margin-bottom: 20px;
}

.text-profit {
  color: #e74c3c;
  font-weight: bold;
}

.text-loss {
  color: #27ae60;
  font-weight: bold;
}
</style>
