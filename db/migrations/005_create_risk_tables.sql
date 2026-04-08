-- 风控管理相关表

-- 1. 风控规则配置表
CREATE TABLE IF NOT EXISTS risk_rules (
    id SERIAL PRIMARY KEY,
    rule_code VARCHAR(50) UNIQUE NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    rule_category VARCHAR(50) NOT NULL, -- 'position', 'exposure', 'drawdown', 'concentration', 'correlation'
    rule_type VARCHAR(20) NOT NULL, -- 'limit', 'stop', 'warning'
    description TEXT,
    parameters JSONB NOT NULL, -- 规则参数
    threshold_value DECIMAL(10,4), -- 阈值
    warning_level VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    action_type VARCHAR(50), -- 'block', 'notify', 'reduce', 'close'
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100, -- 优先级，数字越小优先级越高
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE risk_rules IS '风控规则配置表';
COMMENT ON COLUMN risk_rules.rule_category IS '规则类别：position仓位/exposure敞口/drawdown回撤/concentration集中度/correlation相关性';
COMMENT ON COLUMN risk_rules.rule_type IS '规则类型：limit限制/stop止损/warning预警';
COMMENT ON COLUMN risk_rules.action_type IS '触发动作：block阻断/notify通知/reduce减仓/close平仓';

-- 2. 风控检查记录表
CREATE TABLE IF NOT EXISTS risk_checks (
    id SERIAL PRIMARY KEY,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    check_type VARCHAR(50) NOT NULL, -- 'pre_trade', 'post_trade', 'periodic', 'realtime'
    account_id VARCHAR(50),
    portfolio_value DECIMAL(15,2),
    total_exposure DECIMAL(15,2),
    cash_ratio DECIMAL(5,4),
    position_count INTEGER,
    max_drawdown DECIMAL(10,4),
    daily_loss DECIMAL(15,2),
    check_results JSONB, -- 各规则检查结果
    overall_status VARCHAR(20), -- 'pass', 'warning', 'violation'
    violation_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE risk_checks IS '风控检查记录表';
COMMENT ON COLUMN risk_checks.check_type IS '检查类型：pre_trade交易前/post_trade交易后/periodic周期性/realtime实时';

-- 3. 风控告警记录表
CREATE TABLE IF NOT EXISTS risk_alerts (
    id SERIAL PRIMARY KEY,
    alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rule_id INTEGER REFERENCES risk_rules(id),
    alert_level VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    alert_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    related_positions JSONB, -- 相关持仓
    current_value DECIMAL(15,4), -- 当前值
    threshold_value DECIMAL(15,4), -- 阈值
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(50),
    action_taken VARCHAR(200),
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE risk_alerts IS '风控告警记录表';

-- 4. 持仓限额表
CREATE TABLE IF NOT EXISTS position_limits (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20),
    stock_name VARCHAR(50),
    limit_type VARCHAR(50) NOT NULL, -- 'single_stock', 'industry', 'sector', 'total'
    max_position_value DECIMAL(15,2), -- 最大持仓金额
    max_position_ratio DECIMAL(5,4), -- 最大持仓比例
    max_daily_buy DECIMAL(15,2), -- 单日最大买入
    max_daily_sell DECIMAL(15,2), -- 单日最大卖出
    effective_date DATE,
    expiry_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE position_limits IS '持仓限额表';

-- 5. 交易黑名单表
CREATE TABLE IF NOT EXISTS trade_blacklist (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(50),
    blacklist_type VARCHAR(50) NOT NULL, -- 'risk', 'compliance', 'manual', 'system'
    reason TEXT,
    effective_date DATE DEFAULT CURRENT_DATE,
    expiry_date DATE,
    is_permanent BOOLEAN DEFAULT FALSE,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE trade_blacklist IS '交易黑名单表';

-- 插入默认风控规则
INSERT INTO risk_rules (rule_code, rule_name, rule_category, rule_type, description, parameters, threshold_value, warning_level, action_type, priority) VALUES
('MAX_POSITION_RATIO', '单票持仓上限', 'position', 'limit', '单个股票持仓不得超过总资产的10%', '{"max_ratio": 0.10}'::jsonb, 0.10, 'high', 'block', 10),
('MAX_DRAWDOWN', '最大回撤限制', 'drawdown', 'stop', '账户最大回撤不得超过20%', '{"max_drawdown": 0.20}'::jsonb, 0.20, 'critical', 'reduce', 5),
('DAILY_LOSS_LIMIT', '单日亏损限制', 'drawdown', 'stop', '单日亏损不得超过总资产的5%', '{"max_daily_loss": 0.05}'::jsonb, 0.05, 'high', 'block', 8),
('MIN_CASH_RATIO', '最低现金比例', 'position', 'limit', '账户现金比例不得低于10%', '{"min_cash": 0.10}'::jsonb, 0.10, 'medium', 'warning', 20),
('MAX_TURNOVER', '换手率限制', 'exposure', 'warning', '单日换手率不得超过50%', '{"max_turnover": 0.50}'::jsonb, 0.50, 'medium', 'notify', 30)

ON CONFLICT (rule_code) DO NOTHING;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_risk_rules_category ON risk_rules(rule_category);
CREATE INDEX IF NOT EXISTS idx_risk_rules_active ON risk_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_risk_checks_time ON risk_checks(check_time);
CREATE INDEX IF NOT EXISTS idx_risk_checks_status ON risk_checks(overall_status);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_level ON risk_alerts(alert_level);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_resolved ON risk_alerts(is_resolved);
CREATE INDEX IF NOT EXISTS idx_position_limits_type ON position_limits(limit_type);
CREATE INDEX IF NOT EXISTS idx_trade_blacklist_code ON trade_blacklist(stock_code);
CREATE INDEX IF NOT EXISTS idx_trade_blacklist_active ON trade_blacklist(is_active) WHERE is_active = TRUE;
