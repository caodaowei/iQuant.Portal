#!/usr/bin/env python3
"""iQuant 量化交易系统主入口"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from loguru import logger

from config.settings import settings, LOG_DIR
from core.database import db


def setup_logging():
    """配置日志"""
    log_file = LOG_DIR / "iquant.log"
    
    logger.remove()  # 移除默认处理器
    
    # 控制台输出
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    
    # 文件输出
    logger.add(
        log_file,
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )
    
    logger.info(f"日志配置完成，日志文件: {log_file}")


def check_environment():
    """检查运行环境"""
    logger.info("=" * 50)
    logger.info("iQuant 量化交易系统 v0.1.0")
    logger.info("=" * 50)
    
    # 检查数据库连接
    logger.info("检查数据库连接...")
    if db.health_check():
        logger.info("✅ 数据库连接正常")
    else:
        logger.error("❌ 数据库连接失败")
        return False
    
    # 检查数据源
    logger.info("检查数据源...")
    from core.data_fetcher import data_fetcher
    
    if data_fetcher.tushare.is_available():
        logger.info("✅ Tushare 数据源可用")
    else:
        logger.warning("⚠️ Tushare 数据源未配置")
    
    if data_fetcher.akshare.is_available():
        logger.info("✅ AkShare 数据源可用")
    else:
        logger.warning("⚠️ AkShare 数据源未配置")
    
    return True


def main():
    """主函数"""
    setup_logging()
    
    if not check_environment():
        logger.error("环境检查失败，请检查配置")
        sys.exit(1)
    
    logger.info("系统初始化完成，准备运行...")
    
    # TODO: 启动策略引擎、回测引擎等
    
    logger.info("iQuant 系统运行中...")
    
    # 保持运行
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到退出信号，系统关闭")
        sys.exit(0)


if __name__ == "__main__":
    main()
