"""数据库连接管理"""
from contextlib import contextmanager
from typing import Generator, Optional

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from config.settings import settings


class DatabaseManager:
    """数据库管理器"""
    
    _instance: Optional["DatabaseManager"] = None
    _engine = None
    _session_factory = None
    
    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if self._engine is None:
            self._init_engine()
    
    def _init_engine(self) -> None:
        """初始化数据库引擎"""
        try:
            self._engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
            )
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
            )
            logger.info("数据库引擎初始化成功")
        except Exception as e:
            logger.error(f"数据库引擎初始化失败: {e}")
            raise
    
    @property
    def engine(self):
        return self._engine
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """获取数据库会话上下文管理器"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()
    
    def execute(self, sql: str, params: Optional[dict] = None) -> list:
        """执行SQL语句"""
        with self.session() as session:
            result = session.execute(text(sql), params or {})
            try:
                return result.fetchall()
            except:
                # INSERT/UPDATE/DELETE 等不返回行的操作
                return []
    
    def fetch_one(self, sql: str, params: Optional[dict] = None) -> Optional[tuple]:
        """查询单条记录"""
        with self.session() as session:
            result = session.execute(text(sql), params or {})
            return result.fetchone()
    
    def fetch_all(self, sql: str, params: Optional[dict] = None) -> list:
        """查询所有记录"""
        return self.execute(sql, params)
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            with self.session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False


# 全局数据库管理器实例
db = DatabaseManager()
