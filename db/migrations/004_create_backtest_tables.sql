-- 回测引擎相关表

-- 1. 回测任务表
CREATE TABLE IF NOT EXISTS backtest_tasks (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    task_type VARCHAR(50) NOT NULL, -- 'strategy', 'portfolio', 'timing'
    strategy_codes TEXT[], -- 使用的策略代码列表
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL DEFAULT 1000000.00,
    commission_rate DECIMAL(6,5) DEFAULT 0.00025, -- 佣金率
    slippage DECIMAL(6,5) DEFAULT 0.001, -- 滑点
    position_limit DECIMAL(5,2) DEFAULT 1.0, -- 仓位上限
    parameters JSONB DEFAULT '{}', -- 回测参数
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE backtest_tasks IS '回测任务表';
COMMENT ON COLUMN backtest_tasks.task_type IS '任务类型：strategy策略回测/portfolio组合回测/timing择时回测';
COMMENT ON COLUMN backtest_tasks.status IS '任务状态：pending待运行/running运行中/completed完成/failed失败';

-- 2. 回测结果汇总表
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES backtest_tasks(id) ON DELETE CASCADE,
    total_return DECIMAL(10,4), -- 总收益率
    annualized_return DECIMAL(10,4), -- 年化收益率
    max_drawdown DECIMAL(10,4), -- 最大回撤
    sharpe_ratio DECIMAL(10,4), -- 夏普比率
    sortino_ratio DECIMAL(10,4), -- 索提诺比率
    calmar_ratio DECIMAL(10,4), -- 卡玛比率
    volatility DECIMAL(10,4), -- 波动率
    beta DECIMAL(10,4), -- Beta系数
    alpha DECIMAL(10,4), -- Alpha系数
    information_ratio DECIMAL(10,4), -- 信息比率
    win_rate DECIMAL(5,4), -- 胜率
    profit_loss_ratio DECIMAL(10,4), -- 盈亏比
    total_trades INTEGER, -- 总交易次数
    winning_trades INTEGER, -- 盈利次数
    losing_trades INTEGER, -- 亏损次数
    avg_holding_days DECIMAL(6,2), -- 平均持仓天数
    final_capital DECIMAL(15,2), -- 最终资金
    benchmark_return DECIMAL(10,4), -- 基准收益率
    excess_return DECIMAL(10,4), -- 超额收益
    metrics JSONB, -- 详细指标JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE backtest_results IS '回测结果汇总表';

-- 3. 回测每日净值表
CREATE TABLE IF NOT EXISTS backtest_nav (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES backtest_tasks(id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    nav DECIMAL(12,6) NOT NULL, -- 单位净值
    total_capital DECIMAL(15,2) NOT NULL, -- 总资金
    market_value DECIMAL(15,2), -- 股票市值
    cash DECIMAL(15,2), -- 现金
    daily_return DECIMAL(10,6), -- 日收益率
    benchmark_nav DECIMAL(12,6), -- 基准净值
    drawdown DECIMAL(10,4), -- 当前回撤
    positions_count INTEGER, -- 持仓数量
    turnover DECIMAL(10,4), -- 换手率
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE backtest_nav IS '回测每日净值表';

-- 4. 回测交易记录表
CREATE TABLE IF NOT EXISTS backtest_trades (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES backtest_tasks(id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(50),
    trade_type VARCHAR(10) NOT NULL, -- 'buy', 'sell'
    volume INTEGER NOT NULL,
    price DECIMAL(10,4) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    commission DECIMAL(10,2), -- 佣金
    slippage DECIMAL(10,2), -- 滑点成本
    total_cost DECIMAL(15,2), -- 总成本
    strategy_code VARCHAR(50), -- 产生信号的策略
    signal_id INTEGER, -- 关联的信号ID
    pnl DECIMAL(15,2), -- 盈亏（卖出时计算）
    return_rate DECIMAL(10,4), -- 收益率（卖出时计算）
    holding_days INTEGER, -- 持仓天数（卖出时计算）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE backtest_trades IS '回测交易记录表';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_backtest_tasks_status ON backtest_tasks(status);
CREATE INDEX IF NOT EXISTS idx_backtest_tasks_dates ON backtest_tasks(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_backtest_results_task ON backtest_results(task_id);
CREATE INDEX IF NOT EXISTS idx_backtest_nav_task_date ON backtest_nav(task_id, trade_date);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_task ON backtest_trades(task_id);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_date ON backtest_trades(trade_date);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_stock ON backtest_trades(stock_code);
