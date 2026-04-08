#!/usr/bin/env python3
"""数据同步测试和初始化"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from loguru import logger

from core.data_sync import data_sync
from core.database import db


def init_database():
    """初始化数据库基础数据"""
    logger.info("=" * 60)
    logger.info("初始化数据库")
    logger.info("=" * 60)
    
    # 检查连接
    if db.health_check():
        logger.info("✅ 数据库连接正常")
    else:
        logger.error("❌ 数据库连接失败")
        return False
    
    # 检查表数量
    result = db.fetch_one("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
    logger.info(f"数据库表数量: {result[0]}")
    
    return True


def sync_stock_list():
    """同步股票列表"""
    logger.info("=" * 60)
    logger.info("同步股票列表")
    logger.info("=" * 60)
    
    try:
        count = data_sync.sync_stock_list()
        logger.info(f"✅ 同步完成，共 {count} 只股票")
        return count
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        return 0


def sync_index_data():
    """同步指数数据"""
    logger.info("=" * 60)
    logger.info("同步上证指数数据")
    logger.info("=" * 60)
    
    try:
        # 同步最近一年的数据
        from datetime import datetime, timedelta
        
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        
        count = data_sync.sync_index_data("000001", start_date, end_date)
        logger.info(f"✅ 同步完成，共 {count} 条数据")
        
        # 显示最新数据
        if count > 0:
            latest = db.fetch_one(
                "SELECT trade_date, close, change_pct FROM stock_daily "
                "WHERE code = '000001' ORDER BY trade_date DESC LIMIT 1"
            )
            if latest:
                logger.info(f"最新数据: 日期={latest[0]}, 收盘={latest[1]:.2f}, 涨跌幅={latest[2]:.2f}%")
        
        return count
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        return 0


def sync_sample_stocks():
    """同步示例股票数据"""
    logger.info("=" * 60)
    logger.info("同步示例股票数据")
    logger.info("=" * 60)
    
    # 一些示例股票
    sample_stocks = ["000001", "000002", "600000", "600519"]
    
    total = 0
    for stock_code in sample_stocks:
        try:
            count = data_sync.sync_stock_daily(stock_code)
            logger.info(f"  {stock_code}: {count} 条数据")
            total += count
        except Exception as e:
            logger.error(f"  {stock_code}: 失败 - {e}")
    
    logger.info(f"✅ 同步完成，共 {total} 条数据")
    return total


def verify_data():
    """验证数据"""
    logger.info("=" * 60)
    logger.info("数据验证")
    logger.info("=" * 60)
    
    # 股票列表数量
    stock_count = db.fetch_one("SELECT COUNT(*) FROM stock_info")
    logger.info(f"股票列表: {stock_count[0]} 只")
    
    # 日线数据数量
    daily_count = db.fetch_one("SELECT COUNT(*) FROM stock_daily")
    logger.info(f"日线数据: {daily_count[0]} 条")
    
    # 指数数据数量
    index_count = db.fetch_one("SELECT COUNT(*) FROM stock_daily WHERE code = '000001'")
    logger.info(f"上证指数: {index_count[0]} 条")
    
    # 数据日期范围
    date_range = db.fetch_one(
        "SELECT MIN(trade_date), MAX(trade_date) FROM stock_daily WHERE code = '000001'"
    )
    if date_range and date_range[0]:
        logger.info(f"数据范围: {date_range[0]} 至 {date_range[1]}")


def main():
    """主函数"""
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level: <8} | {message}")
    
    logger.info("🚀 iQuant 数据同步工具")
    logger.info("")
    
    # 初始化
    if not init_database():
        return
    
    logger.info("")
    
    # 同步股票列表
    sync_stock_list()
    
    logger.info("")
    
    # 同步指数数据
    sync_index_data()
    
    logger.info("")
    
    # 同步示例股票
    sync_sample_stocks()
    
    logger.info("")
    
    # 验证数据
    verify_data()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ 数据同步完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
