"""市场数据生成器

提供示例/模拟市场数据生成功能，用于开发和测试。
注意：生产环境应使用真实市场数据。
"""
import pandas as pd
from datetime import datetime


def create_sample_market_data(days: int = 300) -> pd.DataFrame:
    """创建示例市场数据（用于开发和测试）

    生成模拟的指数数据，包含趋势和波动性，适用于：
    - 策略开发和测试
    - 回测引擎验证
    - UI 演示

    Args:
        days: 生成的天数，默认 300 天

    Returns:
        包含 OHLCV 数据的 DataFrame，列包括：
        - trade_date: 交易日期
        - index_code: 指数代码（固定为 000001.SH）
        - open_price: 开盘价
        - high_price: 最高价
        - low_price: 最低价
        - close_price: 收盘价
        - volume: 成交量
        - amount: 成交额
    """
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
