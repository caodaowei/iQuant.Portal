-- ==================== 数据库性能优化索引 ====================

-- 1. 股票日线数据表索引优化
-- 常用查询：按股票代码和日期范围查询
CREATE INDEX IF NOT EXISTS idx_stock_daily_code_date_desc 
ON stock_daily (stock_code, trade_date DESC);

-- 覆盖索引：包含常用查询字段，避免回表
CREATE INDEX IF NOT EXISTS idx_stock_daily_covering 
ON stock_daily (stock_code, trade_date) 
INCLUDE (open_price, high_price, low_price, close_price, volume, amount);

-- 2. 交易订单表索引优化
-- 常用查询：按账户和状态查询订单
CREATE INDEX IF NOT EXISTS idx_trade_orders_account_status 
ON trade_orders (account_id, status);

-- 按创建时间倒序查询（最近订单）
CREATE INDEX IF NOT EXISTS idx_trade_orders_created_desc 
ON trade_orders (created_at DESC);

-- 复合索引：账户 + 股票 + 时间
CREATE INDEX IF NOT EXISTS idx_trade_orders_account_stock_date 
ON trade_orders (account_id, stock_code, created_at DESC);

-- 3. 持仓明细表索引优化
-- 常用查询：按账户查询持仓，按市值排序
CREATE INDEX IF NOT EXISTS idx_position_details_account_value 
ON position_details (account_id, market_value DESC);

-- 唯一约束：每个账户每只股票只有一个持仓记录
CREATE UNIQUE INDEX IF NOT EXISTS idx_position_unique 
ON position_details (account_id, stock_code);

-- 4. 回测结果表索引优化
-- 常用查询：按策略和运行时间查询
CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy_time 
ON backtest_runs (strategy_code, started_at DESC);

-- 按用户查询回测历史
CREATE INDEX IF NOT EXISTS idx_backtest_runs_user 
ON backtest_runs (user_id, started_at DESC);

-- 5. 风控检查记录索引
-- 常用查询：按时间和类型查询
CREATE INDEX IF NOT EXISTS idx_risk_checks_type_time 
ON risk_checks (check_type, created_at DESC);

-- 6. AI 诊断记录索引（如果存在）
CREATE INDEX IF NOT EXISTS idx_diagnosis_stock_time 
ON diagnosis_records (stock_code, created_at DESC);

-- 7. 审计日志表索引优化
-- 常用查询：按用户和时间查询，按操作类型查询
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_time 
ON audit_logs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action_time 
ON audit_logs (action, created_at DESC);

-- 8. 部分索引（Partial Indexes）- 只索引活跃数据
-- 只索引未完成的订单（通常只占一小部分）
CREATE INDEX IF NOT EXISTS idx_active_orders 
ON trade_orders (order_no, account_id) 
WHERE status IN ('pending', 'partial_filled');

-- 只索引最近的交易日线数据（最近一年）
CREATE INDEX IF NOT EXISTS idx_recent_daily_data 
ON stock_daily (stock_code, trade_date DESC) 
WHERE trade_date >= CURRENT_DATE - INTERVAL '1 year';

-- 9. GIN 索引 - 用于 JSONB 字段搜索
CREATE INDEX IF NOT EXISTS idx_risk_checks_details_gin 
ON risk_checks USING GIN (details);

CREATE INDEX IF NOT EXISTS idx_audit_logs_details_gin 
ON audit_logs USING GIN (details);

-- 10. BRIN 索引 - 适用于时间序列数据（占用空间小）
CREATE INDEX IF NOT EXISTS idx_stock_daily_date_brin 
ON stock_daily USING BRIN (trade_date);

CREATE INDEX IF NOT EXISTS idx_audit_logs_time_brin 
ON audit_logs USING BRIN (created_at);

-- ==================== 查询优化视图 ====================

-- 1. 股票最新价格视图（避免每次 JOIN）
CREATE OR REPLACE VIEW v_latest_stock_prices AS
SELECT DISTINCT ON (sd.stock_code)
    sd.stock_code,
    s.stock_name,
    sd.trade_date,
    sd.close_price,
    sd.volume,
    sd.amount,
    (sd.close_price - LAG(sd.close_price) OVER (PARTITION BY sd.stock_code ORDER BY sd.trade_date)) / 
        NULLIF(LAG(sd.close_price) OVER (PARTITION BY sd.stock_code ORDER BY sd.trade_date), 0) * 100 as change_pct
FROM stock_daily sd
JOIN stocks s ON sd.stock_code = s.stock_code
ORDER BY sd.stock_code, sd.trade_date DESC;

-- 2. 账户持仓汇总视图
CREATE OR REPLACE VIEW v_account_positions_summary AS
SELECT
    pd.account_id,
    ta.account_name,
    COUNT(pd.id) as position_count,
    SUM(pd.market_value) as total_market_value,
    SUM(pd.total_cost) as total_cost,
    SUM(pd.floating_pnl) as total_floating_pnl,
    SUM(pd.floating_pnl) / NULLIF(SUM(pd.total_cost), 0) * 100 as total_pnl_rate
FROM position_details pd
JOIN trading_accounts ta ON pd.account_id = ta.id
GROUP BY pd.account_id, ta.account_name;

-- 3. 今日交易统计视图
CREATE OR REPLACE VIEW v_today_trading_stats AS
SELECT
    DATE(created_at) as trade_date,
    COUNT(*) as order_count,
    COUNT(CASE WHEN status = 'filled' THEN 1 END) as filled_count,
    SUM(CASE WHEN status = 'filled' THEN volume * price ELSE 0 END) as total_amount
FROM trade_orders
WHERE created_at >= CURRENT_DATE
GROUP BY DATE(created_at);

-- 4. 策略绩效汇总视图
CREATE OR REPLACE VIEW v_strategy_performance_summary AS
SELECT
    br.strategy_code,
    COUNT(br.id) as run_count,
    AVG(br.total_return) as avg_return,
    MAX(br.total_return) as best_return,
    MIN(br.total_return) as worst_return,
    AVG(br.sharpe_ratio) as avg_sharpe,
    AVG(br.max_drawdown) as avg_drawdown
FROM backtest_results br
WHERE br.started_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY br.strategy_code;

-- ==================== 分区表建议（超大数据量时启用）====================

-- 注意：以下脚本为参考，实际启用需要迁移现有数据

/*
-- 按月分区的 stock_daily 表示例
CREATE TABLE stock_daily_partitioned (
    LIKE stock_daily INCLUDING ALL
) PARTITION BY RANGE (trade_date);

-- 创建分区
CREATE TABLE stock_daily_2024_01 PARTITION OF stock_daily_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE stock_daily_2024_02 PARTITION OF stock_daily_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- ... 为每个月创建分区

-- 迁移数据
INSERT INTO stock_daily_partitioned SELECT * FROM stock_daily;

-- 重命名表
ALTER TABLE stock_daily RENAME TO stock_daily_old;
ALTER TABLE stock_daily_partitioned RENAME TO stock_daily;
*/

-- ==================== 自动清理配置优化 ====================

-- 对频繁更新的表调整 autovacuum 参数
ALTER TABLE trade_orders SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05,
    autovacuum_vacuum_threshold = 1000,
    autovacuum_analyze_threshold = 500
);

ALTER TABLE audit_logs SET (
    autovacuum_vacuum_scale_factor = 0.2,
    autovacuum_analyze_scale_factor = 0.1
);

-- ==================== 统计信息更新 ====================

-- 更新所有表的统计信息（帮助查询优化器选择更好的执行计划）
ANALYZE stock_daily;
ANALYZE trade_orders;
ANALYZE position_details;
ANALYZE backtest_runs;
ANALYZE audit_logs;
