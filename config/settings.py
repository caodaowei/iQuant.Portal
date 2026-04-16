"""配置管理"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """应用配置"""

    # 数据库配置
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "iquant_strategy"
    db_user: str = "iquant_user"
    db_password: str = "admin123"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Tushare配置
    tushare_token: str = ""

    # 日志配置
    log_level: str = "INFO"

    # 交易配置
    default_account: str = "SIM001"
    commission_rate: float = 0.00025
    slippage: float = 0.001

    # 日志配置
    log_file: str = "logs/iquant.log"

    # 回测配置
    default_start_date: str = "2020-01-01"
    default_end_date: str = "2024-12-31"
    default_initial_capital: int = 1000000

    class Config:
        env_file = CONFIG_DIR / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """数据库连接URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        """Redis连接URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
