"""数据获取模块单元测试"""
import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from core.data_fetcher import DataFetcher, TushareDataSource, AkshareDataSource


class TestTushareDataSource:
    """Tushare 数据源测试"""

    @pytest.fixture
    def tushare_source(self):
        """创建 Tushare 数据源实例"""
        with patch('core.data_fetcher.settings') as mock_settings:
            mock_settings.tushare_token = "test_token"
            source = TushareDataSource()
            return source

    def test_init_with_token(self, tushare_source):
        """测试初始化带 Token"""
        assert tushare_source.token == "test_token"

    def test_convert_code_sh(self, tushare_source):
        """测试上海股票代码转换"""
        assert tushare_source._convert_code("600000") == "600000.SH"

    def test_convert_code_sz(self, tushare_source):
        """测试深圳股票代码转换"""
        assert tushare_source._convert_code("000001") == "000001.SZ"
        assert tushare_source._convert_code("300001") == "300001.SZ"

    def test_normalize_code(self, tushare_source):
        """测试代码标准化"""
        assert tushare_source._normalize_code("000001.SZ") == "000001"
        assert tushare_source._normalize_code("600000.SH") == "600000"


class TestAkshareDataSource:
    """AkShare 数据源测试"""

    @pytest.fixture
    def akshare_source(self):
        """创建 AkShare 数据源实例"""
        return AkshareDataSource()

    def test_convert_index_code(self, akshare_source):
        """测试指数代码转换"""
        assert akshare_source._convert_index_code("000001.SH") == "000001"
        assert akshare_source._convert_index_code("399001.SZ") == "399001"

    def test_convert_unknown_index_code(self, akshare_source):
        """测试未知指数代码"""
        assert akshare_source._convert_index_code("UNKNOWN") == "UNKNOWN"


class TestDataFetcher:
    """统一数据获取器测试"""

    @pytest.fixture
    def data_fetcher(self):
        """创建数据获取器实例"""
        with patch('core.data_fetcher.TushareDataSource') as mock_tushare, \
             patch('core.data_fetcher.AkshareDataSource') as mock_akshare:

            # Mock Tushare 可用
            mock_tushare_instance = MagicMock()
            mock_tushare_instance.is_available.return_value = True
            mock_tushare.return_value = mock_tushare_instance

            fetcher = DataFetcher()
            return fetcher

    def test_determine_primary_source_tushare(self, data_fetcher):
        """测试主数据源选择 Tushare"""
        assert data_fetcher._primary_source is not None

    def test_get_daily_data_with_cache(self, data_fetcher, mock_cache_manager):
        """测试获取日线数据（带缓存）"""
        sample_df = pd.DataFrame({
            "trade_date": [date(2024, 1, 1), date(2024, 1, 2)],
            "close": [100.0, 101.0],
        })

        # 第一次调用：缓存未命中，从数据源获取
        data_fetcher._primary_source.get_daily_data.return_value = sample_df
        mock_cache_manager.get_pickle.return_value = None

        result = data_fetcher.get_daily_data("000001", "2024-01-01", "2024-01-31")

        assert not result.empty
        data_fetcher._primary_source.get_daily_data.assert_called_once()
        mock_cache_manager.set_pickle.assert_called_once()

    def test_get_daily_data_cache_hit(self, data_fetcher, mock_cache_manager):
        """测试获取日线数据（缓存命中）"""
        sample_df = pd.DataFrame({
            "trade_date": [date(2024, 1, 1)],
            "close": [100.0],
        })

        # 缓存命中
        mock_cache_manager.get_pickle.return_value = sample_df

        result = data_fetcher.get_daily_data("000001", "2024-01-01", "2024-01-31")

        assert not result.empty
        data_fetcher._primary_source.get_daily_data.assert_not_called()

    def test_get_stock_list_with_cache(self, data_fetcher, mock_cache_manager):
        """测试获取股票列表（带缓存）"""
        sample_df = pd.DataFrame({
            "stock_code": ["000001", "000002"],
            "stock_name": ["平安银行", "万科A"],
        })

        data_fetcher._primary_source.get_stock_list.return_value = sample_df
        mock_cache_manager.get_pickle.return_value = None

        result = data_fetcher.get_stock_list()

        assert not result.empty
        mock_cache_manager.set_pickle.assert_called_once()

    def test_get_index_data_with_cache(self, data_fetcher, mock_cache_manager):
        """测试获取指数数据（带缓存）"""
        sample_df = pd.DataFrame({
            "trade_date": [date(2024, 1, 1)],
            "close": [3000.0],
        })

        data_fetcher._primary_source.get_index_data.return_value = sample_df
        mock_cache_manager.get_pickle.return_value = None

        result = data_fetcher.get_index_data("000001.SH", "2024-01-01", "2024-01-31")

        assert not result.empty
        mock_cache_manager.set_pickle.assert_called_once()


class TestDataFetcherEdgeCases:
    """数据获取器边界情况测试"""

    @pytest.fixture
    def data_fetcher_no_source(self):
        """创建无可用数据源的获取器"""
        with patch('core.data_fetcher.TushareDataSource') as mock_tushare, \
             patch('core.data_fetcher.AkshareDataSource') as mock_akshare:

            mock_tushare_instance = MagicMock()
            mock_tushare_instance.is_available.return_value = False
            mock_tushare.return_value = mock_tushare_instance

            mock_akshare_instance = MagicMock()
            mock_akshare_instance.is_available.return_value = False
            mock_akshare.return_value = mock_akshare_instance

            return DataFetcher()

    def test_no_available_source(self, data_fetcher_no_source):
        """测试无可用数据源"""
        assert data_fetcher_no_source._primary_source is None

    def test_get_daily_data_no_source(self, data_fetcher_no_source):
        """测试无数据源时获取日线数据"""
        result = data_fetcher_no_source.get_daily_data("000001")
        assert result.empty

    def test_get_stock_list_no_source(self, data_fetcher_no_source):
        """测试无数据源时获取股票列表"""
        result = data_fetcher_no_source.get_stock_list()
        assert result.empty

    def test_empty_dataframe_not_cached(self, data_fetcher, mock_cache_manager):
        """测试空 DataFrame 不写入缓存"""
        empty_df = pd.DataFrame()

        data_fetcher._primary_source.get_daily_data.return_value = empty_df
        mock_cache_manager.get_pickle.return_value = None

        result = data_fetcher.get_daily_data("000001")

        assert result.empty
        mock_cache_manager.set_pickle.assert_not_called()


class TestDataFetcherDefaultDates:
    """默认日期范围测试"""

    @pytest.fixture
    def data_fetcher(self):
        """创建数据获取器实例"""
        with patch('core.data_fetcher.TushareDataSource') as mock_tushare:
            mock_tushare_instance = MagicMock()
            mock_tushare_instance.is_available.return_value = True
            mock_tushare.return_value = mock_tushare_instance

            return DataFetcher()

    def test_default_end_date(self, data_fetcher):
        """测试默认结束日期为今天"""
        from datetime import datetime

        data_fetcher.get_daily_data("000001")

        call_args = data_fetcher._primary_source.get_daily_data.call_args
        end_date = call_args[0][2]

        assert end_date == datetime.now().strftime("%Y-%m-%d")

    def test_default_start_date(self, data_fetcher):
        """测试默认开始日期为一年前"""
        from datetime import datetime, timedelta

        data_fetcher.get_daily_data("000001")

        call_args = data_fetcher._primary_source.get_daily_data.call_args
        start_date = call_args[0][1]

        expected = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        assert start_date == expected
