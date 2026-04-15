"""数据库性能监控工具

提供慢查询日志、连接池监控和性能分析功能
"""
import time
from typing import Optional, Dict, List

from sqlalchemy import event, text
from loguru import logger

from core.database_router import get_db_router


class QueryPerformanceMonitor:
    """查询性能监控器"""

    def __init__(self, slow_query_threshold: float = 1.0):
        """初始化监控器

        Args:
            slow_query_threshold: 慢查询阈值（秒）
        """
        self.slow_query_threshold = slow_query_threshold
        self.query_stats: Dict[str, List[float]] = {}
        self.slow_queries: List[Dict] = []

        # 注册 SQLAlchemy 事件监听
        self._register_event_listeners()

    def _register_event_listeners(self):
        """注册 SQLAlchemy 事件监听器"""
        router = get_db_router()

        @event.listens_for(router.master_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())

        @event.listens_for(router.master_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop(-1)
            self._record_query(statement, total)

    def _record_query(self, query: str, duration: float):
        """记录查询性能

        Args:
            query: SQL 查询语句
            duration: 执行时间（秒）
        """
        # 简化查询键（去除参数值）
        query_key = self._simplify_query(query)

        # 记录统计信息
        if query_key not in self.query_stats:
            self.query_stats[query_key] = []
        self.query_stats[query_key].append(duration)

        # 保留最近 100 次记录
        if len(self.query_stats[query_key]) > 100:
            self.query_stats[query_key] = self.query_stats[query_key][-100:]

        # 记录慢查询
        if duration > self.slow_query_threshold:
            slow_query = {
                "query": query[:500],  # 限制长度
                "duration": duration,
                "timestamp": time.time(),
            }
            self.slow_queries.append(slow_query)

            # 只保留最近 100 个慢查询
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]

            logger.warning(f"慢查询检测: {duration:.2f}s\n{query[:200]}")

    def _simplify_query(self, query: str) -> str:
        """简化查询语句（用于分组统计）"""
        # 去除换行和多余空格
        simplified = ' '.join(query.split())
        # 截取前 100 字符作为键
        return simplified[:100]

    def get_stats(self) -> Dict:
        """获取查询统计信息

        Returns:
            包含平均、最大、最小执行时间的字典
        """
        stats = {}
        for query_key, durations in self.query_stats.items():
            if durations:
                stats[query_key] = {
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "max_duration": max(durations),
                    "min_duration": min(durations),
                    "total_duration": sum(durations),
                }

        # 按平均执行时间排序
        sorted_stats = dict(
            sorted(stats.items(), key=lambda x: x[1]["avg_duration"], reverse=True)[:20]
        )

        return sorted_stats

    def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """获取最慢的查询

        Args:
            limit: 返回数量限制

        Returns:
            慢查询列表
        """
        sorted_queries = sorted(
            self.slow_queries, key=lambda x: x["duration"], reverse=True
        )
        return sorted_queries[:limit]

    def reset_stats(self):
        """重置统计信息"""
        self.query_stats.clear()
        self.slow_queries.clear()


# ==================== 连接池监控 ====================

class ConnectionPoolMonitor:
    """连接池监控器"""

    def __init__(self):
        self.router = get_db_router()

    def get_pool_stats(self) -> Dict:
        """获取连接池统计信息

        Returns:
            包含主库和从库连接池状态的字典
        """
        stats = {"master": {}, "slaves": []}

        # 主库统计
        master_pool = self.router.master_engine.pool
        stats["master"] = {
            "pool_size": master_pool.size(),
            "checked_in": master_pool.checkedin(),
            "checked_out": master_pool.checkedout(),
            "overflow": master_pool.overflow(),
            "invalidated": getattr(master_pool, 'invalidated', lambda: 0)(),
        }

        # 从库统计
        for i, engine in enumerate(self.router.slave_engines):
            pool = engine.pool
            stats["slaves"].append({
                "index": i,
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            })

        return stats

    def get_health_status(self) -> Dict:
        """获取数据库健康状态"""
        return self.router.health_check()


# ==================== EXPLAIN 分析工具 ====================

class QueryAnalyzer:
    """查询分析器 - 提供 EXPLAIN 分析"""

    def __init__(self):
        self.router = get_db_router()

    def explain_query(self, query: str, params: Dict = None) -> List[Dict]:
        """执行 EXPLAIN ANALYZE

        Args:
            query: SQL 查询语句
            params: 查询参数

        Returns:
            EXPLAIN 结果
        """
        with self.router.read_session() as session:
            explain_query = f"EXPLAIN ANALYZE {query}"
            result = session.execute(text(explain_query), params or {})

            return [{"plan": row[0]} for row in result.fetchall()]

    def analyze_table_stats(self, table_name: str) -> Dict:
        """分析表统计信息

        Args:
            table_name: 表名

        Returns:
            表的统计信息
        """
        with self.router.read_session() as session:
            # 获取表大小
            size_query = text("""
                SELECT
                    pg_size_pretty(pg_total_relation_size(:table)) as total_size,
                    pg_size_pretty(pg_relation_size(:table)) as table_size,
                    pg_size_pretty(pg_indexes_size(:table)) as index_size
            """)

            size_result = session.execute(size_query, {"table": table_name}).fetchone()

            # 获取行数统计
            count_query = text("""
                SELECT
                    reltuples::bigint as estimated_rows,
                    n_live_tup::bigint as live_rows,
                    n_dead_tup::bigint as dead_rows
                FROM pg_class c
                JOIN pg_stat_user_tables s ON c.relname = s.relname
                WHERE c.relname = :table
            """)

            count_result = session.execute(count_query, {"table": table_name}).fetchone()

            return {
                "table_name": table_name,
                "total_size": size_result[0] if size_result else "N/A",
                "table_size": size_result[1] if size_result else "N/A",
                "index_size": size_result[2] if size_result else "N/A",
                "estimated_rows": count_result[0] if count_result else 0,
                "live_rows": count_result[1] if count_result else 0,
                "dead_rows": count_result[2] if count_result else 0,
            }


# ==================== 全局实例 ====================

query_monitor = QueryPerformanceMonitor(slow_query_threshold=1.0)
pool_monitor = ConnectionPoolMonitor()
query_analyzer = QueryAnalyzer()


def get_performance_report() -> Dict:
    """获取完整的性能报告"""
    return {
        "query_stats": query_monitor.get_stats(),
        "slow_queries": query_monitor.get_slow_queries(5),
        "connection_pool": pool_monitor.get_pool_stats(),
        "health": pool_monitor.get_health_status(),
    }
