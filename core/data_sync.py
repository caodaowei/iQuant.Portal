"""数据同步服务"""
from datetime import date, datetime, timedelta
from typing import List, Optional

import pandas as pd
from loguru import logger

from config.settings import settings
from core.database import db
from core.data_fetcher import data_fetcher


class DataSyncService:
    """数据同步服务
    
    负责从数据源同步股票数据到本地数据库
    """
    
    def __init__(self):
        self.data_fetcher = data_fetcher
        logger.info("数据同步服务初始化")
    
    def sync_stock_list(self) -> int:
        """同步股票列表"""
        logger.info("开始同步股票列表...")
        
        try:
            # 从AkShare获取股票列表
            df = self.data_fetcher.akshare.get_stock_list()
            
            if df.empty:
                logger.warning("获取股票列表为空")
                return 0
            
            # 插入数据库
            count = 0
            for _, row in df.iterrows():
                try:
                    db.execute("""
                        INSERT INTO stock_info (stock_code, stock_name, industry, province)
                        VALUES (:code, :name, :industry, :province)
                        ON CONFLICT (stock_code) DO UPDATE SET
                            stock_name = EXCLUDED.stock_name,
                            industry = EXCLUDED.industry,
                            province = EXCLUDED.province,
                            updated_at = CURRENT_TIMESTAMP
                    """, {
                        "code": row["stock_code"],
                        "name": row["stock_name"],
                        "industry": row.get("industry", ""),
                        "province": row.get("province", ""),
                    })
                    count += 1
                except Exception as e:
                    logger.warning(f"插入股票 {row['stock_code']} 失败: {e}")
            
            logger.info(f"同步股票列表完成，共 {count} 只")
            return count
            
        except Exception as e:
            logger.error(f"同步股票列表失败: {e}")
            return 0
    
    def sync_index_data(
        self,
        index_code: str = "000001",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """同步指数数据"""
        logger.info(f"开始同步指数数据: {index_code}")
        
        try:
            # 默认日期范围
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            
            # 从AkShare获取指数数据
            import akshare as ak
            
            df = ak.index_zh_a_hist(
                symbol=index_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
            )
            
            if df.empty:
                logger.warning(f"获取指数 {index_code} 数据为空")
                return 0
            
            # 重命名列
            df = df.rename(columns={
                "日期": "trade_date",
                "开盘": "open_price",
                "最高": "high_price",
                "最低": "low_price",
                "收盘": "close_price",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "change_pct",
                "涨跌额": "change_amount",
            })
            
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            df["index_code"] = index_code
            
            # 插入数据库
            count = 0
            for _, row in df.iterrows():
                try:
                    db.execute("""
                        INSERT INTO stock_daily 
                        (code, trade_date, open, high, low, close, volume, amount)
                        VALUES (:code, :date, :open, :high, :low, :close, :volume, :amount)
                        ON CONFLICT (code, trade_date) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            amount = EXCLUDED.amount,
                            updated_at = CURRENT_TIMESTAMP
                    """, {
                        "code": index_code,
                        "date": row["trade_date"],
                        "open": row["open_price"],
                        "high": row["high_price"],
                        "low": row["low_price"],
                        "close": row["close_price"],
                        "volume": int(row["volume"]),
                        "amount": float(row["amount"]),
                    })
                    count += 1
                except Exception as e:
                    logger.warning(f"插入数据 {row['trade_date']} 失败: {e}")
            
            logger.info(f"同步指数 {index_code} 数据完成，共 {count} 条")
            return count
            
        except Exception as e:
            logger.error(f"同步指数数据失败: {e}")
            return 0
    
    def sync_stock_daily(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """同步个股日线数据"""
        logger.info(f"开始同步股票 {stock_code} 日线数据")
        
        try:
            # 默认日期范围
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            
            # 从AkShare获取数据
            import akshare as ak
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",  # 前复权
            )
            
            if df.empty:
                logger.warning(f"获取股票 {stock_code} 数据为空")
                return 0
            
            # 重命名列
            df = df.rename(columns={
                "日期": "trade_date",
                "开盘": "open_price",
                "最高": "high_price",
                "最低": "low_price",
                "收盘": "close_price",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "change_pct",
                "涨跌额": "change_amount",
                "换手率": "turnover",
            })
            
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            
            # 插入数据库
            count = 0
            for _, row in df.iterrows():
                try:
                    db.execute("""
                        INSERT INTO stock_daily 
                        (code, trade_date, open, high, low, close, volume, amount)
                        VALUES (:code, :date, :open, :high, :low, :close, :volume, :amount)
                        ON CONFLICT (code, trade_date) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            amount = EXCLUDED.amount,
                            updated_at = CURRENT_TIMESTAMP
                    """, {
                        "code": stock_code,
                        "date": row["trade_date"],
                        "open": row["open_price"],
                        "high": row["high_price"],
                        "low": row["low_price"],
                        "close": row["close_price"],
                        "volume": int(row["volume"]),
                        "amount": float(row["amount"]),
                    })
                    count += 1
                except Exception as e:
                    logger.warning(f"插入数据 {row['trade_date']} 失败: {e}")
            
            logger.info(f"同步股票 {stock_code} 数据完成，共 {count} 条")
            return count
            
        except Exception as e:
            logger.error(f"同步股票数据失败: {e}")
            return 0
    
    def get_latest_data_date(self, stock_code: str) -> Optional[date]:
        """获取最新数据日期"""
        try:
            result = db.fetch_one(
                "SELECT MAX(trade_date) FROM stock_daily WHERE stock_code = :code",
                {"code": stock_code}
            )
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"获取最新数据日期失败: {e}")
            return None
    
    def sync_all(self) -> dict:
        """同步所有数据"""
        logger.info("开始全量数据同步...")
        
        results = {
            "stock_list": 0,
            "index_data": 0,
            "errors": [],
        }
        
        # 同步股票列表
        try:
            results["stock_list"] = self.sync_stock_list()
        except Exception as e:
            results["errors"].append(f"股票列表: {str(e)}")
        
        # 同步上证指数
        try:
            results["index_data"] = self.sync_index_data("000001")
        except Exception as e:
            results["errors"].append(f"上证指数: {str(e)}")
        
        logger.info("全量数据同步完成")
        return results


# 全局数据同步服务实例
data_sync = DataSyncService()
