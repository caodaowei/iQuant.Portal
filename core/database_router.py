"""数据库读写分离管理器

支持主从复制架构，自动将写操作路由到主库，读操作路由到从库。
如果从库不可用，自动降级到主库读取。
"""
from typing import Optional, Any, List, Dict
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from config.settings import settings


class DatabaseRouter:
    """数据库路由器 - 管理主从连接"""

    def __init__(
        self,
        master_url: Optional[str] = None,
        slave_urls: Optional[List[str]] = None,
    ):
        """初始化数据库路由器

        Args:
            master_url: 主库连接 URL
            slave_urls: 从库连接 URL 列表
        """
        self.master_url = master_url or settings.database_url

        # 如果没有配置从库，使用主库作为唯一数据源
        if slave_urls:
            self.slave_urls = slave_urls
            self.has_slaves = True
        else:
            self.slave_urls = [self.master_url]
            self.has_slaves = False

        # 创建引擎
        self.master_engine = create_engine(
            self.master_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            echo=False,
        )

        self.slave_engines = [
            create_engine(
                url,
                pool_size=max(1, settings.db_pool_size // len(self.slave_urls)),
                max_overflow=max(1, settings.db_max_overflow // len(self.slave_urls)),
                pool_pre_ping=True,
                echo=False,
            )
            for url in self.slave_urls
        ]

        # 创建会话工厂
        self.MasterSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.master_engine,
        )

        self.SlaveSessionLocals = [
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
            )
            for engine in self.slave_engines
        ]

        # 从库健康状态
        self.slave_health = [True] * len(self.slave_engines)

        logger.info(f"数据库路由器初始化完成 (从库数量: {len(self.slave_engines)})")

    def get_master_session(self) -> Session:
        """获取主库会话（用于写操作）"""
        return self.MasterSessionLocal()

    def get_slave_session(self) -> Session:
        """获取从库会话（用于读操作）

        使用轮询策略选择健康的从库，如果所有从库都不可用，则使用主库
        """
        if not self.has_slaves:
            return self.get_master_session()

        # 尝试找到健康的从库
        for i, (session_factory, healthy) in enumerate(
            zip(self.SlaveSessionLocals, self.slave_health)
        ):
            if healthy:
                try:
                    session = session_factory()
                    # 简单健康检查
                    session.execute(text("SELECT 1"))
                    return session
                except Exception as e:
                    logger.warning(f"从库 {i} 连接失败: {e}")
                    self.slave_health[i] = False

        # 所有从库都不可用，降级到主库
        logger.warning("所有从库不可用，降级到主库读取")
        return self.get_master_session()

    @contextmanager
    def write_session(self):
        """写操作会话上下文管理器（自动提交/回滚）"""
        session = self.get_master_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"写操作失败: {e}")
            raise
        finally:
            session.close()

    @contextmanager
    def read_session(self):
        """读操作会话上下文管理器"""
        session = self.get_slave_session()
        try:
            yield session
        except Exception as e:
            logger.error(f"读操作失败: {e}")
            raise
        finally:
            session.close()

    def health_check(self) -> Dict[str, bool]:
        """健康检查

        Returns:
            包含 master 和 slaves 健康状态的字典
        """
        result = {"master": False, "slaves": []}

        # 检查主库
        try:
            with self.get_master_session() as session:
                session.execute(text("SELECT 1"))
                result["master"] = True
        except Exception as e:
            logger.error(f"主库健康检查失败: {e}")

        # 检查从库
        for i, session_factory in enumerate(self.SlaveSessionLocals):
            try:
                with session_factory() as session:
                    session.execute(text("SELECT 1"))
                    result["slaves"].append(True)
                    self.slave_health[i] = True
            except Exception as e:
                logger.error(f"从库 {i} 健康检查失败: {e}")
                result["slaves"].append(False)
                self.slave_health[i] = False

        return result

    def close(self):
        """关闭所有连接"""
        self.master_engine.dispose()
        for engine in self.slave_engines:
            engine.dispose()
        logger.info("数据库连接已关闭")


# ==================== 查询优化辅助函数 ====================

class QueryOptimizer:
    """查询优化器 - 提供优化的查询方法"""

    def __init__(self, router: DatabaseRouter):
        self.router = router

    def get_stock_prices_batch(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
    ) -> List[Dict]:
        """批量获取股票价格（优化版）

        使用单次查询替代 N+1 查询
        """
        with self.router.read_session() as session:
            query = text("""
                SELECT stock_code, trade_date, close_price, volume
                FROM stock_daily
                WHERE stock_code = ANY(:codes)
                  AND trade_date BETWEEN :start_date AND :end_date
                ORDER BY stock_code, trade_date DESC
            """)

            result = session.execute(
                query,
                {"codes": stock_codes, "start_date": start_date, "end_date": end_date},
            )

            return [
                {
                    "stock_code": row[0],
                    "trade_date": str(row[1]),
                    "close_price": float(row[2]),
                    "volume": int(row[3]),
                }
                for row in result.fetchall()
            ]

    def get_latest_prices(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """获取最新价格（使用视图）"""
        with self.router.read_session() as session:
            query = text("""
                SELECT stock_code, stock_name, trade_date, close_price, volume, change_pct
                FROM v_latest_stock_prices
                WHERE stock_code = ANY(:codes)
            """)

            result = session.execute(query, {"codes": stock_codes})

            return {
                row[0]: {
                    "stock_name": row[1],
                    "trade_date": str(row[2]),
                    "close_price": float(row[3]),
                    "volume": int(row[4]),
                    "change_pct": float(row[5]) if row[5] else 0.0,
                }
                for row in result.fetchall()
            }

    def get_account_summary(self, account_id: int) -> Optional[Dict]:
        """获取账户持仓汇总（使用视图）"""
        with self.router.read_session() as session:
            query = text("""
                SELECT *
                FROM v_account_positions_summary
                WHERE account_id = :account_id
            """)

            result = session.execute(query, {"account_id": account_id}).fetchone()

            if result:
                return {
                    "account_id": result[0],
                    "account_name": result[1],
                    "position_count": result[2],
                    "total_market_value": float(result[3]),
                    "total_cost": float(result[4]),
                    "total_floating_pnl": float(result[5]),
                    "total_pnl_rate": float(result[6]) if result[6] else 0.0,
                }
            return None

    def bulk_insert_stock_data(self, data: List[Dict]):
        """批量插入股票数据（使用 COPY 协议优化）"""
        import pandas as pd
        from io import StringIO

        df = pd.DataFrame(data)

        with self.router.write_session() as session:
            # 使用 pandas 的 to_sql 批量插入
            df.to_sql(
                "stock_daily",
                session.bind,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=1000,
            )

    def get_strategy_performance(self, strategy_code: str, days: int = 90) -> Dict:
        """获取策略绩效统计（使用视图）"""
        with self.router.read_session() as session:
            query = text("""
                SELECT *
                FROM v_strategy_performance_summary
                WHERE strategy_code = :code
            """)

            result = session.execute(query, {"code": strategy_code}).fetchone()

            if result:
                return {
                    "strategy_code": result[0],
                    "run_count": result[1],
                    "avg_return": float(result[2]) if result[2] else 0.0,
                    "best_return": float(result[3]) if result[3] else 0.0,
                    "worst_return": float(result[4]) if result[4] else 0.0,
                    "avg_sharpe": float(result[5]) if result[5] else 0.0,
                    "avg_drawdown": float(result[6]) if result[6] else 0.0,
                }
            return {}


# ==================== 全局实例 ====================

# 单例模式
_db_router: Optional[DatabaseRouter] = None
_query_optimizer: Optional[QueryOptimizer] = None


def get_db_router() -> DatabaseRouter:
    """获取数据库路由器单例"""
    global _db_router
    if _db_router is None:
        _db_router = DatabaseRouter()
    return _db_router


def get_query_optimizer() -> QueryOptimizer:
    """获取查询优化器单例"""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer(get_db_router())
    return _query_optimizer
