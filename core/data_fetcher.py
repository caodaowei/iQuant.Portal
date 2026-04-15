"""数据获取模块 - 统一数据接口"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import pandas as pd
from loguru import logger

from config.settings import settings
from core.cache import cache_manager


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
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, any]]:
        """获取实时行情（可选实现）"""
        return None


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
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, any]]:
        """获取实时行情（Tushare 实时接口）"""
        try:
            ts_code = self._convert_code(stock_code)
            
            # 使用 Tushare 实时行情接口
            df = self.pro.rt_tick(ts_code=ts_code)
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    "current_price": float(latest.get("price", 0)),
                    "change": float(latest.get("change", 0)),
                    "change_pct": float(latest.get("pct_chg", 0)),
                    "volume": int(latest.get("vol", 0)),
                    "amount": float(latest.get("amount", 0)),
                }
            
            return None
        except Exception as e:
            logger.debug(f"Tushare 实时行情获取失败 {stock_code}: {e}")
            return None
    
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
        """获取日线数据（带缓存）"""
        if self._primary_source is None:
            return pd.DataFrame()

        # 默认日期范围
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # 生成缓存键
        cache_key = f"{stock_code}_{start_date}_{end_date}"

        # 尝试从缓存获取
        cached_data = cache_manager.get_pickle("daily_data", cache_key)
        if cached_data is not None:
            logger.debug(f"缓存命中: {cache_key}")
            return cached_data

        # 从数据源获取
        df = self._primary_source.get_daily_data(stock_code, start_date, end_date)

        # 写入缓存（如果数据不为空）
        if not df.empty:
            cache_manager.set_pickle("daily_data", cache_key, df)
            logger.debug(f"缓存写入: {cache_key}")

        return df
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表（带缓存）"""
        # 尝试从缓存获取
        cached_data = cache_manager.get_pickle("stock_list", "all_stocks")
        if cached_data is not None:
            logger.debug("股票列表缓存命中")
            return cached_data

        if self._primary_source is None:
            return pd.DataFrame()

        df = self._primary_source.get_stock_list()

        # 写入缓存
        if not df.empty:
            cache_manager.set_pickle("stock_list", "all_stocks", df)
            logger.debug("股票列表已缓存")

        return df
    
    def get_index_data(
        self,
        index_code: str = "000001.SH",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取指数数据（带缓存）"""
        if self._primary_source is None:
            return pd.DataFrame()

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # 生成缓存键
        cache_key = f"{index_code}_{start_date}_{end_date}"

        # 尝试从缓存获取
        cached_data = cache_manager.get_pickle("index_data", cache_key)
        if cached_data is not None:
            logger.debug(f"指数数据缓存命中: {cache_key}")
            return cached_data

        # 从数据源获取
        df = self._primary_source.get_index_data(index_code, start_date, end_date)

        # 写入缓存
        if not df.empty:
            cache_manager.set_pickle("index_data", cache_key, df)
            logger.debug(f"指数数据已缓存: {cache_key}")

        return df
    
    def get_realtime_quote(self, stock_code: str) -> Dict[str, any]:
        """获取单只股票的实时行情
        
        Args:
            stock_code: 股票代码，如 '000001.SZ'
        
        Returns:
            包含 current_price, change, change_pct 等的字典
        """
        try:
            # 优先从 Tushare 获取实时行情
            if self._primary_source.source_type == "tushare":
                quote = self._primary_source.get_realtime_quote(stock_code)
                if quote:
                    return quote
            
            # 降级：从缓存的最新日线数据获取
            cache_key = f"{stock_code}_1d"
            cached_df = cache_manager.get_pickle("daily_data", cache_key)
            
            if cached_df is not None and not cached_df.empty:
                latest = cached_df.iloc[-1]
                return {
                    "current_price": float(latest.get("close_price", 0)),
                    "change": 0,
                    "change_pct": 0,
                    "volume": int(latest.get("volume", 0)),
                    "amount": float(latest.get("amount", 0)),
                }
            
            # 最后降级：返回空
            logger.warning(f"无法获取 {stock_code} 的实时行情")
            return {
                "current_price": 0,
                "change": 0,
                "change_pct": 0,
                "volume": 0,
                "amount": 0,
            }
            
        except Exception as e:
            logger.error(f"获取实时行情失败 {stock_code}: {e}")
            return {
                "current_price": 0,
                "change": 0,
                "change_pct": 0,
                "volume": 0,
                "amount": 0,
            }
    
    def get_realtime_quotes(self, stock_codes: List[str]) -> Dict[str, Dict[str, any]]:
        """批量获取多只股票的实时行情
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            {stock_code: quote_dict} 字典
        """
        result = {}
        for code in stock_codes:
            result[code] = self.get_realtime_quote(code)
        return result


# 全局数据获取器实例
data_fetcher = DataFetcher()
