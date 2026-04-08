#!/usr/bin/env python3
"""回测引擎测试"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

import pandas as pd
from loguru import logger

from core.backtest_engine import BacktestEngine
from strategies.timing import MATrendStrategy


def create_sample_market_data(days: int = 300) -> pd.DataFrame:
    """创建示例市场数据"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    
    # 生成模拟指数数据（带趋势和波动）
    base_price = 3000
    prices = []
    
    for i in range(days):
        # 添加趋势和周期性波动
        trend = i * 0.5  # 缓慢上升趋势
        cycle = 100 * (i % 60 - 30) / 30  # 60天周期
        noise = (i % 7 - 3) * 10
        
        # 添加一些趋势反转
        if i > days * 0.3 and i < days * 0.5:
            trend = -i * 0.3  # 下跌段
        elif i > days * 0.7:
            trend = i * 0.8  # 加速上涨
        
        price = base_price + trend + cycle + noise
        prices.append(max(price, 2000))
    
    df = pd.DataFrame({
        "trade_date": dates.date,
        "index_code": "000001.SH",
        "open_price": [p - abs((i % 5) - 2) * 5 for i, p in enumerate(prices)],
        "high_price": [p + abs((i % 5) - 2) * 10 for i, p in enumerate(prices)],
        "low_price": [p - abs((i % 5) - 2) * 10 for i, p in enumerate(prices)],
        "close_price": prices,
        "volume": [100000000 + i * 10000 for i in range(days)],
        "amount": [p * 1000000 for p in prices],
    })
    
    return df


def test_backtest():
    """测试回测引擎"""
    logger.info("=" * 60)
    logger.info("测试回测引擎")
    logger.info("=" * 60)
    
    # 创建市场数据
    market_data = create_sample_market_data(300)
    logger.info(f"生成市场数据: {len(market_data)} 条")
    logger.info(f"日期范围: {market_data['trade_date'].min()} 到 {market_data['trade_date'].max()}")
    logger.info(f"价格范围: {market_data['close_price'].min():.2f} - {market_data['close_price'].max():.2f}")
    
    # 创建回测引擎
    engine = BacktestEngine(
        initial_capital=1000000.0,
        commission_rate=0.00025,
        slippage=0.001,
    )
    
    # 设置策略
    strategy = MATrendStrategy()
    engine.set_strategy(strategy)
    engine.set_market_data(market_data)
    
    # 运行回测
    logger.info("开始回测...")
    results = engine.run()
    
    # 输出结果
    logger.info("")
    logger.info("=" * 60)
    logger.info("回测结果")
    logger.info("=" * 60)
    logger.info(f"初始资金: {results['initial_capital']:,.2f}")
    logger.info(f"最终资金: {results['final_capital']:,.2f}")
    logger.info(f"总收益率: {results['total_return']*100:.2f}%")
    logger.info(f"年化收益: {results['annualized_return']*100:.2f}%")
    logger.info(f"最大回撤: {results['max_drawdown']*100:.2f}%")
    logger.info(f"夏普比率: {results['sharpe_ratio']:.2f}")
    logger.info(f"交易次数: {results['total_trades']}")
    
    # 输出交易记录
    if results['trades']:
        logger.info("")
        logger.info("交易记录 (前10条):")
        for trade in results['trades'][:10]:
            pnl_info = f", 盈亏: {trade.get('pnl', 0):.2f}" if 'pnl' in trade else ""
            logger.info(f"  {trade['date']}: {trade['type'].upper()} {trade['code']} "
                       f"{trade['volume']}股 @ {trade['price']:.2f}{pnl_info}")
    
    return results


def main():
    """主函数"""
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level: <8} | {message}")
    
    logger.info("🚀 iQuant 回测引擎测试")
    logger.info("")
    
    results = test_backtest()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ 回测引擎测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
