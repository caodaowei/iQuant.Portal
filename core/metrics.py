"""Prometheus 指标收集和监控

提供应用程序性能指标(APM)收集功能，包括：
- HTTP 请求指标（计数、延迟、状态码）
- 业务指标（回测次数、AI诊断次数、缓存命中率）
- 系统资源指标（数据库连接池、Redis连接）
"""
import time
from typing import Callable

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ==================== HTTP 请求指标 ====================

# HTTP 请求计数器
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# HTTP 请求延迟直方图
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# HTTP 请求大小直方图
http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

# HTTP 响应大小直方图
http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

# ==================== 业务指标 ====================

# 回测执行计数器
backtest_executions_total = Counter(
    'backtest_executions_total',
    'Total backtest executions',
    ['strategy', 'status']
)

# AI 诊断计数器
ai_diagnosis_total = Counter(
    'ai_diagnosis_total',
    'Total AI diagnosis requests',
    ['stock_code', 'status']
)

# 数据同步计数器
data_sync_total = Counter(
    'data_sync_total',
    'Total data synchronization operations',
    ['sync_type', 'status']
)

# 选股器执行计数器
stock_selection_total = Counter(
    'stock_selection_total',
    'Total stock selection executions',
    ['status']
)

# 风控检查计数器
risk_check_total = Counter(
    'risk_check_total',
    'Total risk check operations',
    ['result']
)

# 异步任务计数器
celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

# 异步任务持续时间
celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
)

# ==================== 缓存指标 ====================

# 缓存命中/未命中
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'namespace', 'result']
)

# 缓存命中率
cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio by namespace',
    ['namespace']
)

# ==================== 数据库指标 ====================

# 数据库查询持续时间
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# 慢查询计数器
db_slow_queries_total = Counter(
    'db_slow_queries_total',
    'Total slow database queries',
    ['query_type']
)

# 数据库连接池状态
db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size',
    ['pool_type']  # master or slave
)

db_connection_pool_active = Gauge(
    'db_connection_pool_active',
    'Active database connections in pool',
    ['pool_type']
)

db_connection_pool_available = Gauge(
    'db_connection_pool_available',
    'Available database connections in pool',
    ['pool_type']
)

# ==================== Redis 指标 ====================

# Redis 连接状态
redis_connection_status = Gauge(
    'redis_connection_status',
    'Redis connection status (1 = connected, 0 = disconnected)'
)

# Redis 命令执行时间
redis_command_duration_seconds = Histogram(
    'redis_command_duration_seconds',
    'Redis command execution duration in seconds',
    ['command'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

# ==================== 系统指标 ====================

# 应用运行时间
app_uptime_seconds = Gauge(
    'app_uptime_seconds',
    'Application uptime in seconds'
)

# 活跃用户数
active_users = Gauge(
    'active_users',
    'Number of active users'
)


# ==================== Prometheus 中间件 ====================

class PrometheusMiddleware(BaseHTTPMiddleware):
    """FastAPI Prometheus 监控中间件

    自动收集所有 HTTP 请求的指标：
    - 请求计数
    - 请求持续时间
    - 请求/响应大小
    - 状态码分布
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 执行请求
        response = await call_next(request)

        # 计算持续时间
        duration = time.time() - start_time

        # 提取端点路径（将路径参数替换为通用标识）
        endpoint = self._normalize_endpoint(request.url.path)

        # 记录指标
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(response.status_code)
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)

        # 记录请求大小
        content_length = request.headers.get('content-length')
        if content_length:
            http_request_size_bytes.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(int(content_length))

        # 记录响应大小
        response_size = int(response.headers.get('content-length', 0))
        http_response_size_bytes.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(response_size)

        return response

    @staticmethod
    def _normalize_endpoint(path: str) -> str:
        """标准化端点路径，将具体 ID 替换为占位符

        例如：
        - /api/diagnosis/000001.SZ/sync -> /api/diagnosis/{id}/sync
        - /api/tasks/abc-123-def -> /api/tasks/{id}
        """
        parts = path.strip('/').split('/')

        # 识别并替换常见的 ID 模式
        normalized = []
        for i, part in enumerate(parts):
            # 跳过空部分
            if not part:
                continue

            # 检测是否为 ID（数字、股票代码、UUID等）
            if (part.isdigit() or
                '.SZ' in part or '.SH' in part or
                len(part) == 36 and part.count('-') == 4):  # UUID 格式
                normalized.append('{id}')
            else:
                normalized.append(part)

        return '/' + '/'.join(normalized)


def create_metrics_endpoint():
    """创建 Prometheus metrics 端点

    Returns:
        返回 metrics 内容的函数
    """
    def metrics():
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    return metrics


# ==================== 辅助函数 ====================

def update_cache_stats(cache_manager):
    """更新缓存统计指标

    Args:
        cache_manager: CacheManager 实例
    """
    try:
        stats = cache_manager.get_stats()

        # 更新总体缓存命中率
        cache_hit_ratio.labels(namespace='total').set(
            stats.get('hit_rate', 0) / 100.0
        )

        # 记录缓存操作计数
        cache_operations_total.labels(
            operation='get',
            namespace='all',
            result='hit'
        ).inc(stats.get('hits', 0))

        cache_operations_total.labels(
            operation='get',
            namespace='all',
            result='miss'
        ).inc(stats.get('misses', 0))

        cache_operations_total.labels(
            operation='any',
            namespace='all',
            result='error'
        ).inc(stats.get('errors', 0))

    except Exception as e:
        # 静默失败，避免影响主流程
        pass


def update_db_pool_stats(pool_monitor):
    """更新数据库连接池指标

    Args:
        pool_monitor: ConnectionPoolMonitor 实例
    """
    try:
        stats = pool_monitor.get_pool_stats()

        # 主库连接池
        master = stats.get('master', {})
        db_connection_pool_size.labels(pool_type='master').set(
            master.get('pool_size', 0)
        )
        db_connection_pool_active.labels(pool_type='master').set(
            master.get('checked_out', 0)
        )
        db_connection_pool_available.labels(pool_type='master').set(
            master.get('checked_in', 0)
        )

        # 从库连接池
        for slave in stats.get('slaves', []):
            idx = slave.get('index', 0)
            db_connection_pool_size.labels(pool_type=f'slave_{idx}').set(
                slave.get('pool_size', 0)
            )
            db_connection_pool_active.labels(pool_type=f'slave_{idx}').set(
                slave.get('checked_out', 0)
            )
            db_connection_pool_available.labels(pool_type=f'slave_{idx}').set(
                slave.get('checked_in', 0)
            )

    except Exception as e:
        pass


def update_redis_status(cache_manager):
    """更新 Redis 连接状态指标

    Args:
        cache_manager: CacheManager 实例
    """
    try:
        is_connected = cache_manager.health_check()
        redis_connection_status.set(1 if is_connected else 0)
    except Exception:
        redis_connection_status.set(0)
