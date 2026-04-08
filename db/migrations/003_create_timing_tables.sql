-- 择时策略相关表

-- 1. 择时策略配置表
CREATE TABLE IF NOT EXISTS timing_strategies (
    id SERIAL PRIMARY KEY,
    strategy_code VARCHAR(50) UNIQUE NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL, -- 'trend', 'mean_reversion', 'breakout', etc.
    description TEXT,
    parameters JSONB NOT NULL DEFAULT '{}', -- 策略参数配置
    indicators JSONB NOT NULL DEFAULT '[]', -- 使用的技术指标列表
    market_scope VARCHAR(20) NOT NULL DEFAULT 'all', -- 'all', 'sh', 'sz', 'cyb', 'kcb'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE timing_strategies IS '择时策略配置表';
COMMENT ON COLUMN timing_strategies.strategy_code IS '策略代码，唯一标识';
COMMENT ON COLUMN timing_strategies.strategy_type IS '策略类型：trend趋势跟踪/mean_reversion均值回归/breakout突破';
COMMENT ON COLUMN timing_strategies.parameters IS '策略参数JSON配置';
COMMENT ON COLUMN timing_strategies.indicators IS '使用的技术指标列表';

-- 2. 择时信号表
CREATE TABLE IF NOT EXISTS timing_signals (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES timing_strategies(id),
    trade_date DATE NOT NULL,
    signal_type VARCHAR(20) NOT NULL, -- 'buy', 'sell', 'hold', 'strong_buy', 'strong_sell'
    signal_strength DECIMAL(3,2) NOT NULL CHECK (signal_strength >= 0 AND signal_strength <= 1),
    market_index VARCHAR(20) NOT NULL, -- '000001.SH', '399001.SZ', '399006.SZ'
    index_close DECIMAL(10,2),
    index_volume BIGINT,
    indicators_values JSONB, -- 各指标计算值
    reason TEXT, -- 信号产生原因
    is_executed BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE timing_signals IS '择时信号表，记录每日市场择时信号';
COMMENT ON COLUMN timing_signals.signal_type IS '信号类型：buy买入/sell卖出/hold持有/strong_buy强烈买入/strong_sell强烈卖出';
COMMENT ON COLUMN timing_signals.signal_strength IS '信号强度 0-1';

-- 3. 市场状态表
CREATE TABLE IF NOT EXISTS market_status (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    market_index VARCHAR(20) NOT NULL,
    trend_status VARCHAR(20) NOT NULL, -- 'bull', 'bear', 'oscillation', 'unknown'
    volatility_status VARCHAR(20) NOT NULL, -- 'high', 'medium', 'low'
    volume_status VARCHAR(20) NOT NULL, -- 'high', 'normal', 'low'
    sentiment_score DECIMAL(5,2), -- 市场情绪分数 -100 到 100
    technical_score DECIMAL(5,2), -- 技术面综合分数
    fundamental_score DECIMAL(5,2), -- 基本面综合分数
    overall_score DECIMAL(5,2), -- 综合评分
    analysis JSONB, -- 详细分析数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE market_status IS '市场状态表，记录每日市场整体状态评估';
COMMENT ON COLUMN market_status.trend_status IS '趋势状态：bull牛市/bear熊市/oscillation震荡/unknown未知';
COMMENT ON COLUMN market_status.volatility_status IS '波动率状态：high高/medium中/low低';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_timing_strategies_type ON timing_strategies(strategy_type);
CREATE INDEX IF NOT EXISTS idx_timing_strategies_active ON timing_strategies(is_active);
CREATE INDEX IF NOT EXISTS idx_timing_signals_date ON timing_signals(trade_date);
CREATE INDEX IF NOT EXISTS idx_timing_signals_strategy ON timing_signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_timing_signals_type ON timing_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_market_status_date ON market_status(trade_date);
CREATE INDEX IF NOT EXISTS idx_market_status_trend ON market_status(trend_status);

-- 插入示例策略
INSERT INTO timing_strategies (strategy_code, strategy_name, strategy_type, description, parameters, indicators) VALUES
('MA_TREND', '均线趋势策略', 'trend', '基于多条均线判断趋势方向', 
 '{"short_ma": 5, "medium_ma": 20, "long_ma": 60, "threshold": 0.02}'::jsonb,
 '["MA5", "MA20", "MA60"]'::jsonb),

('MACD_SIGNAL', 'MACD信号策略', 'trend', '基于MACD金叉死叉产生信号',
 '{"fast": 12, "slow": 26, "signal": 9}'::jsonb,
 '["MACD", "MACD_SIGNAL", "MACD_HIST"]'::jsonb),

('RSI_MEAN_REVERT', 'RSI均值回归', 'mean_reversion', 'RSI超买超卖回归策略',
 '{"period": 14, "overbought": 70, "oversold": 30}'::jsonb,
 '["RSI14"]'::jsonb),

('BOLL_BREAKOUT', '布林带突破', 'breakout', '布林带上下轨突破策略',
 '{"period": 20, "std": 2}'::jsonb,
 '["BOLL_UPPER", "BOLL_MIDDLE", "BOLL_LOWER"]'::jsonb)

ON CONFLICT (strategy_code) DO NOTHING;
