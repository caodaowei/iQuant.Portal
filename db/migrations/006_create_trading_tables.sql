-- 交易执行相关表

-- 1. 交易账户表
CREATE TABLE IF NOT EXISTS trading_accounts (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(50) UNIQUE NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(20) NOT NULL, -- 'real', 'simulation', 'backtest'
    broker VARCHAR(50), -- 券商
    api_type VARCHAR(50), -- 'xtquant', 'tushare', 'jqdata', 'manual'
    api_config JSONB, -- API配置（加密存储）
    initial_capital DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_capital DECIMAL(15,2) DEFAULT 0,
    available_cash DECIMAL(15,2) DEFAULT 0,
    frozen_cash DECIMAL(15,2) DEFAULT 0,
    market_value DECIMAL(15,2) DEFAULT 0,
    total_pnl DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'suspended', 'closed'
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE trading_accounts IS '交易账户表';
COMMENT ON COLUMN trading_accounts.account_type IS '账户类型：real实盘/simulation模拟/backtest回测';
COMMENT ON COLUMN trading_accounts.api_type IS 'API类型：xtquant迅投/tushare/jqdata聚宽/manual手动';

-- 2. 交易订单表
CREATE TABLE IF NOT EXISTS trade_orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE, -- 系统订单号
    broker_order_no VARCHAR(50), -- 券商订单号
    account_id INTEGER REFERENCES trading_accounts(id),
    strategy_code VARCHAR(50), -- 来源策略
    signal_id INTEGER, -- 来源信号
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(50),
    order_type VARCHAR(20) NOT NULL, -- 'market', 'limit', 'stop', 'stop_limit'
    trade_type VARCHAR(10) NOT NULL, -- 'buy', 'sell'
    order_volume INTEGER NOT NULL,
    order_price DECIMAL(10,4),
    filled_volume INTEGER DEFAULT 0,
    filled_amount DECIMAL(15,2) DEFAULT 0,
    avg_price DECIMAL(10,4),
    commission DECIMAL(10,2) DEFAULT 0,
    stamp_tax DECIMAL(10,2) DEFAULT 0, -- 印花税
    transfer_fee DECIMAL(10,2) DEFAULT 0, -- 过户费
    other_fees DECIMAL(10,2) DEFAULT 0,
    total_cost DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'submitted', 'partial', 'filled', 'cancelled', 'rejected', 'expired'
    submit_time TIMESTAMP,
    filled_time TIMESTAMP,
    cancelled_time TIMESTAMP,
    rejected_reason TEXT,
    valid_date DATE, -- 订单有效日期
    expire_time TIMESTAMP, -- 过期时间
    is_cancelled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE trade_orders IS '交易订单表';
COMMENT ON COLUMN trade_orders.order_type IS '订单类型：market市价/limit限价/stop止损/stop_limit限价止损';
COMMENT ON COLUMN trade_orders.status IS '订单状态：pending待提交/submitted已报/partial部分成交/filled已成/cancelled已撤/rejected已拒/expired过期';

-- 3. 成交明细表
CREATE TABLE IF NOT EXISTS trade_fills (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES trade_orders(id),
    fill_no VARCHAR(50), -- 成交编号
    account_id INTEGER REFERENCES trading_accounts(id),
    stock_code VARCHAR(20) NOT NULL,
    trade_type VARCHAR(10) NOT NULL,
    fill_volume INTEGER NOT NULL,
    fill_price DECIMAL(10,4) NOT NULL,
    fill_amount DECIMAL(15,2) NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0,
    stamp_tax DECIMAL(10,2) DEFAULT 0,
    transfer_fee DECIMAL(10,2) DEFAULT 0,
    other_fees DECIMAL(10,2) DEFAULT 0,
    total_cost DECIMAL(15,2) NOT NULL,
    fill_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE trade_fills IS '成交明细表';

-- 4. 持仓明细表
CREATE TABLE IF NOT EXISTS position_details (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES trading_accounts(id),
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(50),
    total_volume INTEGER DEFAULT 0, -- 总持仓
    available_volume INTEGER DEFAULT 0, -- 可用持仓
    frozen_volume INTEGER DEFAULT 0, -- 冻结持仓
    avg_cost DECIMAL(10,4) DEFAULT 0, -- 平均成本
    total_cost DECIMAL(15,2) DEFAULT 0, -- 总成本
    current_price DECIMAL(10,4), -- 当前价格
    market_value DECIMAL(15,2), -- 市值
    floating_pnl DECIMAL(15,2), -- 浮动盈亏
    floating_pnl_rate DECIMAL(10,4), -- 浮动盈亏率
    realized_pnl DECIMAL(15,2) DEFAULT 0, -- 已实现盈亏
    open_date DATE, -- 开仓日期
    last_trade_date DATE, -- 最后交易日期
    strategy_code VARCHAR(50), -- 所属策略
    is_closed BOOLEAN DEFAULT FALSE, -- 是否已清仓
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, stock_code)
);

COMMENT ON TABLE position_details IS '持仓明细表';

-- 5. 资金流水表
CREATE TABLE IF NOT EXISTS capital_flows (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES trading_accounts(id),
    flow_type VARCHAR(50) NOT NULL, -- 'deposit', 'withdraw', 'trade', 'fee', 'dividend', 'adjustment'
    trade_date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    balance DECIMAL(15,2) NOT NULL, -- 变动后余额
    related_order_id INTEGER REFERENCES trade_orders(id),
    stock_code VARCHAR(20),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE capital_flows IS '资金流水表';
COMMENT ON COLUMN capital_flows.flow_type IS '流水类型：deposit入金/withdraw出金/trade交易/fee费用/dividend分红/adjustment调整';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_trading_accounts_type ON trading_accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_trading_accounts_status ON trading_accounts(status);
CREATE INDEX IF NOT EXISTS idx_trade_orders_account ON trade_orders(account_id);
CREATE INDEX IF NOT EXISTS idx_trade_orders_stock ON trade_orders(stock_code);
CREATE INDEX IF NOT EXISTS idx_trade_orders_status ON trade_orders(status);
CREATE INDEX IF NOT EXISTS idx_trade_orders_date ON trade_orders(created_at);
CREATE INDEX IF NOT EXISTS idx_trade_fills_order ON trade_fills(order_id);
CREATE INDEX IF NOT EXISTS idx_trade_fills_account ON trade_fills(account_id);
CREATE INDEX IF NOT EXISTS idx_position_details_account ON position_details(account_id);
CREATE INDEX IF NOT EXISTS idx_position_details_stock ON position_details(stock_code);
CREATE INDEX IF NOT EXISTS idx_capital_flows_account ON capital_flows(account_id);
CREATE INDEX IF NOT EXISTS idx_capital_flows_date ON capital_flows(trade_date);

-- 插入默认模拟账户
INSERT INTO trading_accounts (account_code, account_name, account_type, initial_capital, total_capital, available_cash, is_default) VALUES
('SIM001', '默认模拟账户', 'simulation', 1000000.00, 1000000.00, 1000000.00, TRUE)
ON CONFLICT (account_code) DO NOTHING;
