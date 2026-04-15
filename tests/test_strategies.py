#!/usr/bin/env python3
"""策略单元测试（Pytest 版本）"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from strategies.timing.base import TimingStrategy, TimingSignal
from strategies.timing.ma_strategy import MATrendStrategy
from strategies.timing.macd_strategy import MACDStrategy
from strategies.timing.rsi_strategy import RSIStrategy
from strategies.timing.boll_strategy import BollingerStrategy


def create_sample_data(days: int = 200) -> pd.DataFrame:
    """创建示例数据"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

    # 生成模拟价格数据（带趋势和波动）
    base_price = 3000
    prices = []
    for i in range(days):
        # 添加趋势和周期性波动
        trend = i * 1.5
        cycle = 50 * (i % 20 - 10) / 10  # 20天周期
        noise = (i % 7 - 3) * 5
        price = base_price + trend + cycle + noise
        prices.append(max(price, 1000))  # 确保价格为正

    df = pd.DataFrame({
        "trade_date": dates.date,
        "index_code": "000001.SH",
        "open_price": [p - abs((i % 5) - 2) * 5 for i, p in enumerate(prices)],
        "high_price": [p + abs((i % 5) - 2) * 8 for i, p in enumerate(prices)],
        "low_price": [p - abs((i % 5) - 2) * 8 for i, p in enumerate(prices)],
        "close_price": prices,
        "volume": [1000000 + i * 1000 for i in range(days)],
        "amount": [p * 1000000 for p in prices],
    })

    return df


class TestMATrendStrategy:
    """均线策略测试"""

    @pytest.fixture
    def strategy(self):
        return MATrendStrategy()

    @pytest.fixture
    def sample_data(self):
        return create_sample_data(100)

    def test_strategy_name(self, strategy):
        assert strategy.name == "MA_TREND"

    def test_calculate_indicators(self, strategy, sample_data):
        data_with_indicators = strategy.calculate_indicators(sample_data)

        assert "ma_short" in data_with_indicators.columns
        assert "ma_long" in data_with_indicators.columns
        assert len(data_with_indicators) == len(sample_data)

    def test_get_latest_signal(self, strategy, sample_data):
        data_with_indicators = strategy.calculate_indicators(sample_data)
        signal = strategy.get_latest_signal(data_with_indicators)

        if signal:
            assert hasattr(signal, 'signal_type')
            assert hasattr(signal, 'strength')
            assert hasattr(signal, 'reason')

    def test_run_full_strategy(self, strategy, sample_data):
        signals = strategy.run(sample_data)
        assert isinstance(signals, list)
        assert len(signals) == len(sample_data)


class TestMACDStrategy:
    """MACD 策略测试"""

    @pytest.fixture
    def strategy(self):
        return MACDStrategy()

    @pytest.fixture
    def sample_data(self):
        return create_sample_data(100)

    def test_strategy_name(self, strategy):
        assert strategy.name == "MACD_SIGNAL"

    def test_calculate_indicators(self, strategy, sample_data):
        data_with_indicators = strategy.calculate_indicators(sample_data)

        assert "macd" in data_with_indicators.columns
        assert "macd_signal" in data_with_indicators.columns
        assert "macd_hist" in data_with_indicators.columns

    def test_get_latest_signal(self, strategy, sample_data):
        data_with_indicators = strategy.calculate_indicators(sample_data)
        signal = strategy.get_latest_signal(data_with_indicators)

        if signal:
            assert signal.signal_type in ["buy", "sell", "hold"]


class TestRSIStrategy:
    """RSI 策略测试"""

    @pytest.fixture
    def strategy(self):
        return RSIStrategy()

    @pytest.fixture
    def sample_data(self):
        return create_sample_data(100)

    def test_strategy_name(self, strategy):
        assert strategy.name == "RSI_MEAN_REVERT"

    def test_calculate_indicators(self, strategy, sample_data):
        data_with_indicators = strategy.calculate_indicators(sample_data)

        assert "rsi" in data_with_indicators.columns
        # RSI 应该在 0-100 之间
        rsi_values = data_with_indicators["rsi"].dropna()
        if not rsi_values.empty:
            assert rsi_values.between(0, 100).all()

    def test_get_latest_signal(self, strategy, sample_data):
        data_with_indicators = strategy.calculate_indicators(sample_data)
        signal = strategy.get_latest_signal(data_with_indicators)

        if signal:
            assert signal.signal_type in ["buy", "sell", "hold"]


class TestBollingerStrategy:
    """布林带策略测试"""

    @pytest.fixture
    def strategy(self):
        return BollingerStrategy()

    @pytest.fixture
    def sample_data(self):
        return create_sample_data(100)

    def test_strategy_name(self, strategy):
        assert strategy.name == "BOLL_BREAKOUT"

    def test_calculate_indicators(self, strategy, sample_data):
        data_with_indicators = strategy.calculate_indicators(sample_data)

        assert "boll_upper" in data_with_indicators.columns
        assert "boll_middle" in data_with_indicators.columns
        assert "boll_lower" in data_with_indicators.columns

    def test_get_latest_signal(self, strategy, sample_data):
        data_with_indicators = strategy.calculate_indicators(sample_data)
        signal = strategy.get_latest_signal(data_with_indicators)

        if signal:
            assert signal.signal_type in ["buy", "sell", "hold"]


class TestStrategyManager:
    """策略管理器测试"""

    def test_register_and_list(self):
        from core.strategy_manager import StrategyManager

        manager = StrategyManager()
        manager.register_strategy("MA_TREND")
        manager.register_strategy("MACD_SIGNAL")

        strategies = manager.list_strategies()
        assert len(strategies) >= 2

        for s in strategies:
            assert "code" in s
            assert "name" in s
            assert "active" in s

    def test_run_all_strategies(self):
        from core.strategy_manager import StrategyManager

        manager = StrategyManager()
        manager.register_strategy("MA_TREND")
        manager.register_strategy("MACD_SIGNAL")

        data = create_sample_data(100)
        results = manager.run_all(data)

        assert isinstance(results, dict)
        for code, signals in results.items():
            assert isinstance(signals, list)

    def test_consensus_signal(self):
        from core.strategy_manager import StrategyManager

        manager = StrategyManager()
        manager.register_strategy("MA_TREND")
        manager.register_strategy("MACD_SIGNAL")

        data = create_sample_data(100)
        consensus = manager.get_consensus_signal(data, method="majority")

        if consensus:
            assert hasattr(consensus, 'signal_type')
            assert hasattr(consensus, 'strength')


class TestStrategyEdgeCases:
    """策略边界情况测试"""

    def test_insufficient_data(self):
        """测试数据不足的情况"""
        strategy = MATrendStrategy()

        # 只有 5 条数据
        dates = pd.date_range(end=datetime.now(), periods=5, freq="D")
        df = pd.DataFrame({
            "trade_date": dates.date,
            "close_price": [100, 101, 102, 103, 104],
            "open_price": [100, 101, 102, 103, 104],
            "high_price": [101, 102, 103, 104, 105],
            "low_price": [99, 100, 101, 102, 103],
            "volume": [1000000] * 5,
        })

        signals = strategy.run(df)
        assert len(signals) == 5

    def test_constant_price(self):
        """测试价格不变的情况"""
        strategy = MACDStrategy()

        dates = pd.date_range(end=datetime.now(), periods=50, freq="D")
        df = pd.DataFrame({
            "trade_date": dates.date,
            "close_price": [100.0] * 50,
            "open_price": [100.0] * 50,
            "high_price": [100.0] * 50,
            "low_price": [100.0] * 50,
            "volume": [1000000] * 50,
        })

        signals = strategy.run(df)
        assert len(signals) == 50

    def test_extreme_volatility(self):
        """测试极端波动情况"""
        strategy = RSIStrategy()

        dates = pd.date_range(end=datetime.now(), periods=50, freq="D")
        prices = [100 * (1.1 ** i if i % 2 == 0 else 0.9 ** i) for i in range(50)]

        df = pd.DataFrame({
            "trade_date": dates.date,
            "close_price": prices,
            "open_price": prices,
            "high_price": [p * 1.02 for p in prices],
            "low_price": [p * 0.98 for p in prices],
            "volume": [1000000] * 50,
        })

        signals = strategy.run(df)
        assert len(signals) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
