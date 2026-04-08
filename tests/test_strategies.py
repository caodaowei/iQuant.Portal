#!/usr/bin/env python3
"""策略测试"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

import pandas as pd
from loguru import logger

from core.strategy_manager import StrategyManager
from strategies.timing import (
    BollingerStrategy,
    MACDStrategy,
    MATrendStrategy,
    RSIStrategy,
)


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


def test_ma_strategy():
    """测试均线策略"""
    logger.info("=" * 50)
    logger.info("测试均线趋势策略")
    logger.info("=" * 50)
    
    data = create_sample_data(100)
    strategy = MATrendStrategy()
    
    # 计算指标
    data_with_indicators = strategy.calculate_indicators(data)
    
    # 获取最新信号
    signal = strategy.get_latest_signal(data_with_indicators)
    
    if signal:
        logger.info(f"✅ 信号日期: {signal.trade_date}")
        logger.info(f"   信号类型: {signal.signal_type}")
        logger.info(f"   信号强度: {signal.strength:.2f}")
        logger.info(f"   指数收盘: {signal.index_close:.2f}")
        logger.info(f"   信号原因: {signal.reason}")
    else:
        logger.warning("⚠️ 未生成信号")
    
    return signal


def test_macd_strategy():
    """测试MACD策略"""
    logger.info("=" * 50)
    logger.info("测试MACD信号策略")
    logger.info("=" * 50)
    
    data = create_sample_data(100)
    strategy = MACDStrategy()
    
    data_with_indicators = strategy.calculate_indicators(data)
    signal = strategy.get_latest_signal(data_with_indicators)
    
    if signal:
        logger.info(f"✅ 信号日期: {signal.trade_date}")
        logger.info(f"   信号类型: {signal.signal_type}")
        logger.info(f"   信号强度: {signal.strength:.2f}")
        logger.info(f"   指数收盘: {signal.index_close:.2f}")
        logger.info(f"   信号原因: {signal.reason}")
    else:
        logger.warning("⚠️ 未生成信号")
    
    return signal


def test_rsi_strategy():
    """测试RSI策略"""
    logger.info("=" * 50)
    logger.info("测试RSI均值回归策略")
    logger.info("=" * 50)
    
    data = create_sample_data(100)
    strategy = RSIStrategy()
    
    data_with_indicators = strategy.calculate_indicators(data)
    signal = strategy.get_latest_signal(data_with_indicators)
    
    if signal:
        logger.info(f"✅ 信号日期: {signal.trade_date}")
        logger.info(f"   信号类型: {signal.signal_type}")
        logger.info(f"   信号强度: {signal.strength:.2f}")
        logger.info(f"   指数收盘: {signal.index_close:.2f}")
        logger.info(f"   信号原因: {signal.reason}")
        logger.info(f"   RSI值: {signal.indicators.get('RSI', 'N/A')}")
    else:
        logger.warning("⚠️ 未生成信号")
    
    return signal


def test_boll_strategy():
    """测试布林带策略"""
    logger.info("=" * 50)
    logger.info("测试布林带突破策略")
    logger.info("=" * 50)
    
    data = create_sample_data(100)
    strategy = BollingerStrategy()
    
    data_with_indicators = strategy.calculate_indicators(data)
    signal = strategy.get_latest_signal(data_with_indicators)
    
    if signal:
        logger.info(f"✅ 信号日期: {signal.trade_date}")
        logger.info(f"   信号类型: {signal.signal_type}")
        logger.info(f"   信号强度: {signal.strength:.2f}")
        logger.info(f"   指数收盘: {signal.index_close:.2f}")
        logger.info(f"   信号原因: {signal.reason}")
        logger.info(f"   布林带位置: {signal.indicators.get('BOLL_POSITION', 'N/A'):.1%}")
    else:
        logger.warning("⚠️ 未生成信号")
    
    return signal


def test_strategy_manager():
    """测试策略管理器"""
    logger.info("=" * 50)
    logger.info("测试策略管理器")
    logger.info("=" * 50)
    
    manager = StrategyManager()
    
    # 注册所有策略
    manager.register_strategy("MA_TREND")
    manager.register_strategy("MACD_SIGNAL")
    manager.register_strategy("RSI_MEAN_REVERT")
    manager.register_strategy("BOLL_BREAKOUT")
    
    # 列出策略
    strategies = manager.list_strategies()
    logger.info(f"已注册 {len(strategies)} 个策略:")
    for s in strategies:
        status = "✅ 激活" if s["active"] else "⏸️ 暂停"
        logger.info(f"   {s['code']}: {s['name']} ({status})")
    
    # 运行所有策略
    data = create_sample_data(100)
    results = manager.run_all(data)
    
    logger.info("策略运行结果:")
    for code, signals in results.items():
        logger.info(f"   {code}: {len(signals)} 个信号")
    
    # 获取共识信号
    consensus = manager.get_consensus_signal(data, method="majority")
    if consensus:
        logger.info(f"共识信号: {consensus.signal_type} (强度: {consensus.strength:.2f})")
        logger.info(f"共识原因: {consensus.reason}")
    
    return manager


def main():
    """主函数"""
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level: <8} | {message}")
    
    logger.info("🚀 iQuant 策略测试")
    logger.info("")
    
    # 测试各个策略
    test_ma_strategy()
    logger.info("")
    
    test_macd_strategy()
    logger.info("")
    
    test_rsi_strategy()
    logger.info("")
    
    test_boll_strategy()
    logger.info("")
    
    # 测试策略管理器
    test_strategy_manager()
    
    logger.info("")
    logger.info("=" * 50)
    logger.info("✅ 所有策略测试完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
