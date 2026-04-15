"""Celery 任务测试"""
import pytest
from unittest.mock import patch, MagicMock

from core.tasks import (
    sync_stock_data,
    run_backtest,
    run_ai_diagnosis,
    batch_sync_stocks,
)


class TestCeleryTasks:
    """Celery 任务测试"""

    @patch('core.tasks.data_fetcher')
    def test_sync_stock_data_success(self, mock_fetcher):
        """测试股票数据同步成功"""
        import pandas as pd
        from datetime import date

        # Mock 返回数据
        mock_df = pd.DataFrame({
            "trade_date": [date(2024, 1, 1), date(2024, 1, 2)],
            "close": [100.0, 101.0],
            "volume": [1000, 1100],
        })
        mock_fetcher.get_daily_data.return_value = mock_df

        # 执行任务
        result = sync_stock_data("000001", days=365)

        assert result["status"] == "success"
        assert result["stock_code"] == "000001"
        assert result["records_synced"] == 2

    @patch('core.tasks.data_fetcher')
    def test_sync_stock_data_empty(self, mock_fetcher):
        """测试股票数据同步失败（空数据）"""
        import pandas as pd

        mock_fetcher.get_daily_data.return_value = pd.DataFrame()

        result = sync_stock_data("INVALID", days=365)

        assert result["status"] == "failed"
        assert "未获取到" in result["message"]

    @patch('core.tasks.create_sample_market_data')
    @patch('core.tasks.BacktestEngine')
    def test_run_backtest_success(self, mock_engine_class, mock_create_data):
        """测试回测任务成功"""
        import pandas as pd

        # Mock 市场数据
        mock_data = pd.DataFrame({
            "trade_date": pd.date_range("2024-01-01", periods=100),
            "close": [100 + i for i in range(100)],
            "open": [100 + i for i in range(100)],
            "high": [101 + i for i in range(100)],
            "low": [99 + i for i in range(100)],
            "volume": [1000] * 100,
        })
        mock_create_data.return_value = mock_data

        # Mock 回测引擎
        mock_engine = MagicMock()
        mock_engine.run.return_value = {
            "initial_capital": 1000000,
            "final_capital": 1100000,
            "total_return": 0.1,
            "annualized_return": 0.15,
            "max_drawdown": -0.05,
            "sharpe_ratio": 1.5,
            "total_trades": 10,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "nav_data": [],
            "trades": [],
        }
        mock_engine_class.return_value = mock_engine

        with patch('core.tasks.create_backtest_chart', return_value={}):
            result = run_backtest("MA_TREND", days=300, initial_capital=1000000)

        assert result["status"] == "completed"
        assert result["strategy"] == "MA_TREND"
        assert result["total_return"] == 0.1

    @patch('core.tasks.MultiAgentSystem')
    def test_run_ai_diagnosis_success(self, mock_system_class):
        """测试 AI 诊断任务成功"""
        # Mock 诊断系统
        mock_system = MagicMock()
        mock_system.diagnose.return_value = {
            "code": "000001",
            "decision": {"decision": "buy", "confidence": 80},
        }
        mock_system_class.return_value = mock_system

        result = run_ai_diagnosis("000001")

        assert result["status"] == "completed"
        assert result["stock_code"] == "000001"
        assert "diagnosis" in result

    @patch('core.tasks.sync_stock_data')
    def test_batch_sync_stocks(self, mock_sync):
        """测试批量同步股票"""
        mock_sync.return_value = {
            "status": "success",
            "stock_code": "000001",
            "records_synced": 100,
        }

        stock_codes = ["000001", "000002", "000003"]
        result = batch_sync_stocks(stock_codes, days=365)

        assert result["status"] == "completed"
        assert result["total"] == 3
        assert result["success"] == 3
        assert result["failed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
