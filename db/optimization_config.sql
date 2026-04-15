-- ==================== PostgreSQL 配置优化建议 ====================

-- 执行以下命令需要超级用户权限
-- psql -U postgres -d iquant_strategy

-- 1. 内存配置优化

-- shared_buffers: 设置为系统内存的 25%
-- 示例：16GB 系统设置为 4GB
ALTER SYSTEM SET shared_buffers = '4GB';

-- effective_cache_size: 设置为系统内存的 50-75%
-- 示例：16GB 系统设置为 12GB
ALTER SYSTEM SET effective_cache_size = '12GB';

-- work_mem: 每个操作的工作内存（谨慎设置，会乘以并发连接数）
-- 示例：64MB - 256MB
ALTER SYSTEM SET work_mem = '64MB';

-- maintenance_work_mem: 维护操作（VACUUM, CREATE INDEX）的内存
-- 示例：1GB
ALTER SYSTEM SET maintenance_work_mem = '1GB';


-- 2. WAL (Write-Ahead Logging) 配置

-- wal_buffers: WAL 缓冲区大小
ALTER SYSTEM SET wal_buffers = '64MB';

-- checkpoint_completion_target: 检查点完成目标
ALTER SYSTEM SET checkpoint_completion_target = 0.9;

-- min_wal_size / max_wal_size: WAL 文件大小
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';


-- 3. 查询优化器配置

-- random_page_cost: 随机页面读取成本（SSD 可以降低）
ALTER SYSTEM SET random_page_cost = 1.1;

-- effective_io_concurrency: 并发 I/O 数量（SSD 可以提高）
ALTER SYSTEM SET effective_io_concurrency = 200;

-- default_statistics_target: 统计信息目标（提高可改善查询计划）
ALTER SYSTEM SET default_statistics_target = 200;


-- 4. 连接配置

-- max_connections: 最大连接数（根据应用需求调整）
ALTER SYSTEM SET max_connections = 200;

-- superuser_reserved_connections: 保留给超级用户的连接
ALTER SYSTEM SET superuser_reserved_connections = 3;


-- 5. 自动清理 (Autovacuum) 配置

-- 启用自动清理
ALTER SYSTEM SET autovacuum = on;

-- 最大自动清理工作进程数
ALTER SYSTEM SET autovacuum_max_workers = 3;

-- 自动清理间隔
ALTER SYSTEM SET autovacuum_naptime = '10s';

-- 触发 VACUUM 的死元组阈值
ALTER SYSTEM SET autovacuum_vacuum_threshold = 50;

-- 触发 VACUUM 的死元组比例
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.1;

-- 触发 ANALYZE 的变更元组比例
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.05;


-- 6. 日志配置

-- 启用慢查询日志
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 记录超过 1 秒的查询

-- 记录检查点
ALTER SYSTEM SET log_checkpoints = on;

-- 记录连接
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;

-- 记录锁等待
ALTER SYSTEM SET log_lock_waits = on;

-- 日志格式
ALTER SYSTEM SET log_line_prefix = '%m [%p] %q%u@%d ';


-- 7. 并行查询配置

-- 最大并行工作进程数
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;

-- 最大并行维护工作进程数
ALTER SYSTEM SET max_parallel_maintenance_workers = 4;

-- 总并行工作进程数
ALTER SYSTEM SET max_parallel_workers = 8;

-- 并行扫描的最小表大小
ALTER SYSTEM SET min_parallel_table_scan_size = '8MB';


-- 8. 应用更改并重启

-- 执行以下命令使配置生效（部分配置需要重启）
-- SELECT pg_reload_conf();  -- 重载配置（不需要重启）
-- pg_ctl restart            -- 重启 PostgreSQL


-- ==================== 监控查询 ====================

-- 查看当前配置
SELECT name, setting, unit, category
FROM pg_settings
WHERE name IN (
    'shared_buffers',
    'effective_cache_size',
    'work_mem',
    'maintenance_work_mem',
    'max_connections',
    'random_page_cost',
    'effective_io_concurrency'
)
ORDER BY category, name;

-- 查看数据库大小
SELECT
    datname as database_name,
    pg_size_pretty(pg_database_size(datname)) as size
FROM pg_database
ORDER BY pg_database_size(datname) DESC;

-- 查看表大小和索引大小
SELECT
    schemaname,
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(relid)) as total_size,
    pg_size_pretty(pg_relation_size(relid)) as table_size,
    pg_size_pretty(pg_indexes_size(relid)) as index_size,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 20;

-- 查看最慢的查询
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- 查看索引使用情况
SELECT
    schemaname,
    relname as table_name,
    indexrelname as index_name,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC
LIMIT 20;

-- 查看未使用的索引（可以考虑删除）
SELECT
    schemaname,
    relname as table_name,
    indexrelname as index_name,
    idx_scan as index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND NOT indisunique
  AND NOT indisprimary
ORDER BY pg_relation_size(indexrelid) DESC;

-- 查看连接数
SELECT
    count(*) as total_connections,
    count(CASE WHEN state = 'active' THEN 1 END) as active,
    count(CASE WHEN state = 'idle' THEN 1 END) as idle,
    count(CASE WHEN state = 'idle in transaction' THEN 1 END) as idle_in_transaction
FROM pg_stat_activity;

-- 查看锁等待
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
