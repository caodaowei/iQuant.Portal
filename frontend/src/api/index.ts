import request from '@/utils/request'

// 策略相关 API
export interface Strategy {
  code: string
  name: string
  type: string
  active?: boolean
}

export const strategyApi = {
  // 获取策略列表
  getList() {
    return request.get('/strategies')
  },

  // 运行策略
  run(code: string, params?: any) {
    return request.post(`/strategies/${code}/run`, params)
  },
}

// 回测相关 API
export interface BacktestParams {
  strategy: string
  days: number
  initial_capital: number
}

export interface BacktestResult {
  strategy: string
  initial_capital: number
  final_capital: number
  total_return: number
  annualized_return: number
  max_drawdown: number
  sharpe_ratio: number
  total_trades: number
  start_date: string
  end_date: string
  chart: any
}

export const backtestApi = {
  // 同步回测
  runSync(params: BacktestParams) {
    return request.post('/backtest/sync', null, { params })
  },

  // 异步回测
  runAsync(params: BacktestParams) {
    return request.post('/backtest/async', null, { params })
  },
}

// AI 诊断 API
export interface DiagnosisResult {
  code: string
  final_decision: {
    decision: string
    confidence: number
    reasoning: string
  }
  stages: any
}

export const diagnosisApi = {
  // 同步诊断
  getSync(stockCode: string) {
    return request.get(`/diagnosis/${stockCode}/sync`)
  },

  // 异步诊断
  getAsync(stockCode: string) {
    return request.get(`/diagnosis/${stockCode}/async`)
  },
}

// 数据同步 API
export const dataApi = {
  // 同步单只股票
  syncStock(code: string, days: number = 365) {
    return request.post(`/data/sync/${code}`, null, { params: { days } })
  },

  // 批量同步
  syncBatch(codes: string[], days: number = 365) {
    return request.post('/data/sync/batch', { stock_codes: codes, days })
  },
}

// 任务管理 API
export const taskApi = {
  // 查询任务状态
  getStatus(taskId: string) {
    return request.get(`/tasks/${taskId}`)
  },

  // 撤销任务
  revoke(taskId: string) {
    return request.delete(`/tasks/${taskId}`)
  },
}

// 系统状态 API
export const systemApi = {
  getStatus() {
    return request.get('/status')
  },

  getCacheStats() {
    return request.get('/cache/stats')
  },

  clearCache(namespace?: string) {
    return request.post('/cache/clear', null, { params: { namespace } })
  },
}

// 投资账本 API
export interface LedgerAccount {
  id: number
  account_code: string
  account_name: string
  account_type: string
  total_capital: number
  available_cash: number
  market_value: number
  total_pnl: number
  status: string
  is_default: boolean
  created_at?: string
}

export interface PositionWithQuote {
  stock_code: string
  stock_name: string
  total_volume: number
  available_volume: number
  avg_cost: number
  total_cost: number
  current_price: number
  market_value: number
  floating_pnl: number
  floating_pnl_rate: number
  open_date: string | null
  last_trade_date: string | null
}

export interface TradeRecord {
  fill_no: string
  stock_code: string
  trade_type: 'buy' | 'sell'
  fill_volume: number
  fill_price: number
  fill_amount: number
  commission: number
  stamp_tax: number
  transfer_fee: number
  other_fees: number
  total_cost: number
  fill_time: string
  order_no: string
  strategy_code: string | null
}

export interface AssetHistory {
  date: string
  cash_balance: number
  market_value: number
  total_asset: number
  nav: number
  daily_return: number
}

export interface PnlStatistics {
  total_trades: number
  buy_trades: number
  sell_trades: number
  realized_pnl: number
  win_rate: number
  avg_pnl_per_trade: number
  max_single_profit: number
  max_single_loss: number
  total_fees: number
  avg_holding_days: number
}

export interface PnlByStock {
  stock_code: string
  stock_name: string
  total_buy_volume: number
  total_sell_volume: number
  total_buy_amount: number
  total_sell_amount: number
  total_fees: number
  realized_pnl: number
}

export interface DailyPnl {
  date: string
  pnl: number
  sell_count: number
  fees: number
}

export const ledgerApi = {
  // 获取账户列表
  getAccounts() {
    return request.get<{ accounts: LedgerAccount[]; count: number }>('/ledger/accounts')
  },

  // 获取账户详情
  getAccount(accountId: number) {
    return request.get<LedgerAccount>(`/ledger/account/${accountId}`)
  },

  // 添加账户
  addAccount(data: {
    account_name: string
    account_type: string
    initial_capital: number
    is_default?: boolean
  }) {
    return request.post('/ledger/accounts', data)
  },

  // 更新账户
  updateAccount(accountId: number, data: {
    account_name?: string
    account_type?: string
    is_default?: boolean
  }) {
    return request.put(`/ledger/accounts/${accountId}`, data)
  },

  // 删除账户
  deleteAccount(accountId: number) {
    return request.delete(`/ledger/accounts/${accountId}`)
  },

  // 获取持仓列表
  getPositions(accountId: number) {
    return request.get<{ positions: PositionWithQuote[]; count: number }>('/ledger/positions', {
      params: { account_id: accountId },
    })
  },

  // 获取交易历史
  getTradeHistory(params: {
    account_id: number
    limit?: number
    offset?: number
    stock_code?: string
    trade_type?: string
    start_date?: string
    end_date?: string
  }) {
    return request.get<{ trades: TradeRecord[]; total: number; limit: number; offset: number }>(
      '/ledger/trades',
      { params }
    )
  },

  // 获取资产历史
  getAssetHistory(accountId: number, days: number = 90) {
    return request.get<{ history: AssetHistory[]; count: number }>('/ledger/assets/history', {
      params: { account_id: accountId, days },
    })
  },

  // 获取盈亏统计
  getPnlSummary(accountId: number) {
    return request.get<PnlStatistics>('/ledger/pnl/summary', {
      params: { account_id: accountId },
    })
  },

  // 获取每日盈亏
  getDailyPnl(accountId: number, days: number = 30) {
    return request.get<{ daily_pnl: DailyPnl[]; count: number }>('/ledger/pnl/daily', {
      params: { account_id: accountId, days },
    })
  },

  // 获取按股票统计的盈亏
  getPnlByStock(accountId: number) {
    return request.get<{ pnl_by_stock: PnlByStock[]; count: number }>('/ledger/pnl/by-stock', {
      params: { account_id: accountId },
    })
  },

  // 获取资金流水
  getCapitalFlows(accountId: number, limit: number = 50, flowType?: string) {
    return request.get('/ledger/capital-flows', {
      params: { account_id: accountId, limit, flow_type: flowType },
    })
  },
}
