"""数据获取模块 - 统一数据接口"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from loguru import logger

from config.settings import settings


class DataSource(ABC):
    """数据源抽象基类"""
    
    @abstractmethod
    def get_daily_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取日线数据"""
        pass
    
    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        pass
    
    @abstractmethod
    def get_index_data(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取指数数据"""
        pass


class TushareDataSource(DataSource):
    """Tushare数据源"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.tushare_token
        self.pro = None
        if self.token:
            self._init_client()
    
    def _init_client(self):
        """初始化Tushare客户端"""
        try:
            import tushare as ts
            self.pro = ts.pro_api(self.token)
            logger.info("Tushare客户端初始化成功")
        except Exception as e:
            logger.error(f"Tushare客户端初始化失败: {e}")
            self.pro = None
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return self.pro is not None
    
    def get_daily_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取日线数据"""
        if not self.is_available():
            logger.warning("Tushare未配置，返回空数据")
            return pd.DataFrame()
        
        try:
            # 转换股票代码格式
            ts_code = self._convert_code(stock_code)
            
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
            )
            
            if df.empty:
                return df
            
            # 标准化列名
            df = df.rename(columns={
                "ts_code": "stock_code",
                "trade_date": "trade_date",
                "open": "open_price",
                "high": "high_price",
                "low": "low_price",
                "close": "close_price",
                "vol": "volume",
                "amount": "amount",
            })
            
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            df["stock_code"] = df["stock_code"].apply(self._normalize_code)
            
            return df.sort_values("trade_date")
            
        except Exception as e:
            logger.error(f"获取日线数据失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        if not self.is_available():
            return pd.DataFrame()
        
        try:
            df = self.pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,list_date",
            )
            
            df = df.rename(columns={
                "ts_code": "stock_code",
                "symbol": "stock_symbol",
                "name": "stock_name",
                "area": "province",
                "industry": "industry",
                "list_date": "list_date",
            })
            
            df["stock_code"] = df["stock_code"].apply(self._normalize_code)
            df["list_date"] = pd.to_datetime(df["list_date"]).dt.date
            
            return df
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_index_data(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取指数数据"""
        if not self.is_available():
            return pd.DataFrame()
        
        try:
            df = self.pro.index_daily(
                ts_code=index_code,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
            )
            
            if df.empty:
                return df
            
            df = df.rename(columns={
                "ts_code": "index_code",
                "trade_date": "trade_date",
                "open": "open_price",
                "high": "high_price",
                "low": "low_price",
                "close": "close_price",
                "vol": "volume",
                "amount": "amount",
            })
            
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            
            return df.sort_values("trade_date")
            
        except Exception as e:
            logger.error(f"获取指数数据失败 {index_code}: {e}")
            return pd.DataFrame()
    
    def _convert_code(self, code: str) -> str:
        """转换为Tushare代码格式"""
        code = code.strip().upper()
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        elif code.startswith(("4", "8")):
            return f"{code}.BJ"
        return code
    
    def _normalize_code(self, ts_code: str) -> str:
        """标准化代码格式"""
        return ts_code.split(".")[0]


class AkshareDataSource(DataSource):
    """AkShare数据源"""
    
    def __init__(self):
        self._init_client()
    
    def _init_client(self):
        """初始化AkShare"""
        try:
            import akshare as ak
            self.ak = ak
            logger.info("AkShare客户端初始化成功")
        except Exception as e:
            logger.error(f"AkShare客户端初始化失败: {e}")
            self.ak = None
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return self.ak is not None
    
    def get_daily_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取日线数据"""
        if not self.is_available():
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",  # 前复权
            )
            
            if df.empty:
                return df
            
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
            
            df["stock_code"] = stock_code
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            
            return df.sort_values("trade_date")
            
        except Exception as e:
            logger.error(f"获取日线数据失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        if not self.is_available():
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_zh_a_spot_em()
            
            df = df[["代码", "名称", "所属行业", "地区"]].copy()
            df.columns = ["stock_code", "stock_name", "industry", "province"]
            
            return df
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_index_data(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取指数数据"""
        if not self.is_available():
            return pd.DataFrame()
        
        try:
            # 转换指数代码
            symbol = self._convert_index_code(index_code)
            
            df = self.ak.index_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
            )
            
            if df.empty:
                return df
            
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
            
            df["index_code"] = index_code
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            
            return df.sort_values("trade_date")
            
        except Exception as e:
            logger.error(f"获取指数数据失败 {index_code}: {e}")
            return pd.DataFrame()
    
    def _convert_index_code(self, code: str) -> str:
        """转换指数代码"""
        index_map = {
            "000001.SH": "000001",
            "399001.SZ": "399001",
            "399006.SZ": "399006",
            "000300.SH": "000300",
            "000905.SH": "000905",
        }
        return index_map.get(code, code)


class DataFetcher:
    """统一数据获取器"""
    
    def __init__(self):
        self.tushare = TushareDataSource()
        self.akshare = AkshareDataSource()
        self._primary_source: Optional[DataSource] = None
        self._determine_primary_source()
    
    def _determine_primary_source(self):
        """确定主数据源"""
        if self.tushare.is_available():
            self._primary_source = self.tushare
            logger.info("使用Tushare作为主数据源")
        elif self.akshare.is_available():
            self._primary_source = self.akshare
            logger.info("使用AkShare作为主数据源")
        else:
            logger.warning("无可用数据源")
    
    def get_daily_data(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取日线数据"""
        if self._primary_source is None:
            return pd.DataFrame()
        
        # 默认日期范围
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        return self._primary_source.get_daily_data(stock_code, start_date, end_date)
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        if self._primary_source is None:
            return pd.DataFrame()
        return self._primary_source.get_stock_list()
    
    def get_index_data(
        self,
        index_code: str = "000001.SH",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取指数数据"""
        if self._primary_source is None:
            return pd.DataFrame()
        
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        return self._primary_source.get_index_data(index_code, start_date, end_date)


# 全局数据获取器实例
data_fetcher = DataFetcher()
