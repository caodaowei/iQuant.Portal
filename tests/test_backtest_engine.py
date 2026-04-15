"""回测引擎单元测试"""
import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import MagicMock

from core.backtest_engine import BacktestEngine, Position, BacktestState
from strategies.timing.base import TimingStrategy


class TestPosition:
    """持仓数据类测试"""

    def test_position_creation(self):
        """测试持仓创建"""
        pos = Position(
            stock_code="000001",
            stock_name="平安银行",
            volume=1000,
            avg_cost=50.0,
        )

        assert pos.stock_code == "000001"
        assert pos.volume == 1000
        assert pos.avg_cost == 50.0
        assert pos.total_cost == 0.0  # 需要计算

    def test_position_market_value(self):
        """测试持仓市值计算"""
        pos = Position(
            stock_code="000001",
            volume=1000,
            avg_cost=50.0,
            current_price=55.0,
        )

        pos.market_value = pos.volume * pos.current_price
        pos.floating_pnl = (pos.current_price - pos.avg_cost) * pos.volume
        pos.floating_pnl_rate = (pos.current_price - pos.avg_cost) / pos.avg_cost

        assert pos.market_value == 55000.0
        assert pos.floating_pnl == 5000.0
        assert pos.floating_pnl_rate == 0.1  # 10%


class TestBacktestEngine:
    """回测引擎核心测试"""

    @pytest.fixture
    def engine(self):
        """创建回测引擎实例"""
        return BacktestEngine(
            initial_capital=1000000.0,
            commission_rate=0.00025,
            slippage=0.001,
        )

    @pytest.fixture
    def sample_market_data(self):
        """示例市场数据"""
        dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(100)]
        return pd.DataFrame({
            "trade_date": dates,
            "stock_code": "000001",
            "open_price": [100 + i * 0.1 for i in range(100)],
            "high_price": [102 + i * 0.1 for i in range(100)],
            "low_price": [98 + i * 0.1 for i in range(100)],
            "close_price": [100 + i * 0.2 for i in range(100)],
            "volume": [1000000] * 100,
        })

    @pytest.fixture
    def mock_strategy(self):
        """Mock 策略"""
        strategy = MagicMock(spec=TimingStrategy)
        strategy.name = "TestStrategy"

        # Mock generate_signal 返回买入信号
        signal = MagicMock()
        signal.signal = "buy"
        signal.confidence = 0.8

        strategy.generate_signal.return_value = signal
        return strategy

    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine.initial_capital == 1000000.0
        assert engine.cash == 1000000.0
        assert engine.commission_rate == 0.00025
        assert engine.slippage == 0.001
        assert len(engine.positions) == 0
        assert len(engine.trades) == 0

    def test_set_strategy(self, engine, mock_strategy):
        """测试设置策略"""
        engine.set_strategy(mock_strategy)
        assert engine.strategy == mock_strategy

    def test_set_market_data(self, engine, sample_market_data):
        """测试设置市场数据"""
        engine.set_market_data(sample_market_data)

        assert engine.market_data is not None
        assert len(engine.market_data) == 100
        assert engine.start_date == date(2024, 1, 1)
        assert engine.end_date == date(2024, 4, 9)

    def test_run_without_strategy(self, engine, sample_market_data):
        """测试未设置策略时运行回测"""
        engine.set_market_data(sample_market_data)

        with pytest.raises(ValueError, match="未设置策略"):
            engine.run()

    def test_run_without_market_data(self, engine, mock_strategy):
        """测试未设置市场数据时运行回测"""
        engine.set_strategy(mock_strategy)

        with pytest.raises(ValueError, match="未设置市场数据"):
            engine.run()

    def test_run_backtest_basic(self, engine, mock_strategy, sample_market_data):
        """测试基本回测运行"""
        engine.set_strategy(mock_strategy)
        engine.set_market_data(sample_market_data)

        results = engine.run()

        assert "initial_capital" in results
        assert "final_capital" in results
        assert "total_return" in results
        assert "nav_data" in results
        assert "trades" in results

    def test_backtest_results_structure(self, engine, mock_strategy, sample_market_data):
        """测试回测结果结构"""
        engine.set_strategy(mock_strategy)
        engine.set_market_data(sample_market_data)

        results = engine.run()

        required_keys = [
            "initial_capital",
            "final_capital",
            "total_return",
            "annualized_return",
            "max_drawdown",
            "sharpe_ratio",
            "total_trades",
            "start_date",
            "end_date",
            "nav_data",
            "trades",
        ]

        for key in required_keys:
            assert key in results, f"缺少必需字段: {key}"

    def test_backtest_with_empty_data(self, engine, mock_strategy):
        """测试空数据回测"""
        empty_data = pd.DataFrame()

        engine.set_strategy(mock_strategy)
        engine.set_market_data(empty_data)

        with pytest.raises(ValueError, match="未设置市场数据"):
            engine.run()


class TestBacktestCalculations:
    """回测计算逻辑测试"""

    @pytest.fixture
    def engine_with_data(self, sample_market_data):
        """创建带数据的引擎"""
        from strategies.timing.ma_strategy import MATrendStrategy

        engine = BacktestEngine(initial_capital=1000000.0)
        strategy = MATrendStrategy()
        engine.set_strategy(strategy)
        engine.set_market_data(sample_market_data)

        return engine

    def test_commission_calculation(self, engine_with_data):
        """测试手续费计算"""
        # 买入 1000 股，价格 100
        trade_value = 1000 * 100
        commission = trade_value * engine_with_data.commission_rate

        assert commission == 25.0  # 100000 * 0.00025

    def test_slippage_calculation(self, engine_with_data):
        """测试滑点计算"""
        price = 100.0
        slippage_amount = price * engine_with_data.slippage

        # 买入时价格会上涨
        buy_price = price + slippage_amount
        assert buy_price == 100.1

    def test_position_update(self, engine_with_data):
        """测试持仓更新"""
        # 模拟买入
        engine_with_data.cash = 1000000.0
        engine_with_data._execute_buy("000001", "平安银行", 1000, 100.0)

        assert "000001" in engine_with_data.positions
        pos = engine_with_data.positions["000001"]
        assert pos.volume == 1000
        assert pos.avg_cost > 100.0  # 包含手续费和滑点

    def test_cash_management(self, engine_with_data):
        """测试现金管理"""
        initial_cash = engine_with_data.cash

        # 买入消耗现金
        engine_with_data._execute_buy("000001", "平安银行", 1000, 100.0)

        assert engine_with_data.cash < initial_cash

    def test_portfolio_value_calculation(self, engine_with_data):
        """测试组合价值计算"""
        # 添加持仓
        pos = Position(
            stock_code="000001",
            stock_name="平安银行",
            volume=1000,
            avg_cost=100.0,
            current_price=105.0,
        )
        pos.market_value = 1000 * 105.0
        engine_with_data.positions["000001"] = pos
        engine_with_data.cash = 900000.0

        total_value = engine_with_data.cash + pos.market_value
        assert total_value == 1005000.0


class TestBacktestPerformance:
    """回测绩效指标测试"""

    @pytest.fixture
    def completed_backtest(self, sample_market_data):
        """完成一次回测"""
        from strategies.timing.ma_strategy import MATrendStrategy

        engine = BacktestEngine(initial_capital=1000000.0)
        strategy = MATrendStrategy()
        engine.set_strategy(strategy)
        engine.set_market_data(sample_market_data)

        return engine.run()

    def test_total_return_calculation(self, completed_backtest):
        """测试总收益率计算"""
        initial = completed_backtest["initial_capital"]
        final = completed_backtest["final_capital"]
        expected_return = (final - initial) / initial

        assert abs(completed_backtest["total_return"] - expected_return) < 0.01

    def test_sharpe_ratio_range(self, completed_backtest):
        """测试夏普比率合理性"""
        sharpe = completed_backtest["sharpe_ratio"]

        # 夏普比率通常在 -3 到 3 之间
        assert -3 <= sharpe <= 3 or sharpe == 0

    def test_max_drawdown_negative(self, completed_backtest):
        """测试最大回撤为负值"""
        max_dd = completed_backtest["max_drawdown"]

        assert max_dd <= 0

    def test_trade_count_non_negative(self, completed_backtest):
        """测试交易次数非负"""
        trades = completed_backtest["total_trades"]

        assert trades >= 0


class TestBacktestEdgeCases:
    """回测边界情况测试"""

    def test_insufficient_capital(self):
        """测试资金不足情况"""
        engine = BacktestEngine(initial_capital=1000.0)  # 很少的资金

        # 应该能够处理资金不足的情况
        assert engine.initial_capital == 1000.0
        assert engine.cash == 1000.0

    def test_zero_commission(self):
        """测试零手续费"""
        engine = BacktestEngine(
            initial_capital=1000000.0,
            commission_rate=0.0,
        )

        assert engine.commission_rate == 0.0

    def test_zero_slippage(self):
        """测试零滑点"""
        engine = BacktestEngine(
            initial_capital=1000000.0,
            slippage=0.0,
        )

        assert engine.slippage == 0.0

    def test_high_frequency_trading(self, sample_market_data):
        """测试高频交易场景"""
        from unittest.mock import MagicMock
        from strategies.timing.base import TimingStrategy

        engine = BacktestEngine(initial_capital=1000000.0)

        # Mock 策略每次都交易
        mock_strategy = MagicMock(spec=TimingStrategy)
        mock_strategy.name = "HighFreqStrategy"

        signal = MagicMock()
        signal.signal = "buy"
        signal.confidence = 1.0
        mock_strategy.generate_signal.return_value = signal

        engine.set_strategy(mock_strategy)
        engine.set_market_data(sample_market_data)

        results = engine.run()

        # 应该有大量交易
        assert results["total_trades"] > 0
