"""策略注册表

统一管理所有可用策略，避免重复定义。
提供策略查找和注册功能。
"""
from typing import Dict, Type, Optional

from strategies.timing.base import TimingStrategy
from strategies.timing.ma_strategy import MATrendStrategy
from strategies.timing.macd_strategy import MACDStrategy
from strategies.timing.rsi_strategy import RSIStrategy
from strategies.timing.boll_strategy import BollingerStrategy
from strategies.timing.linear_regression_strategy import LinearRegressionStrategy
from strategies.timing.slope_volume_strategy import SlopeVolumeStrategy


# 策略注册表：策略代码 -> 策略类映射
STRATEGY_REGISTRY: Dict[str, Type[TimingStrategy]] = {
    "MA_TREND": MATrendStrategy,
    "MACD_SIGNAL": MACDStrategy,
    "RSI_MEAN_REVERT": RSIStrategy,
    "BOLL_BREAKOUT": BollingerStrategy,
    "LR_SLOPE": LinearRegressionStrategy,
    "SLOPE_VOL": SlopeVolumeStrategy,
}

# 策略元数据：用于 UI 展示和文档
STRATEGY_METADATA: Dict[str, Dict[str, str]] = {
    "MA_TREND": {
        "name": "均线趋势策略",
        "description": "基于移动平均线的趋势跟踪策略",
        "type": "trend_following",
    },
    "MACD_SIGNAL": {
        "name": "MACD 信号策略",
        "description": "基于 MACD 指标的交易信号策略",
        "type": "momentum",
    },
    "RSI_MEAN_REVERT": {
        "name": "RSI 均值回归策略",
        "description": "基于 RSI 指标的均值回归策略",
        "type": "mean_reversion",
    },
    "BOLL_BREAKOUT": {
        "name": "布林带突破策略",
        "description": "基于布林带的突破交易策略",
        "type": "breakout",
    },
    "LR_SLOPE": {
        "name": "线性回归斜率策略",
        "description": "基于线性回归斜率的趋势判断策略",
        "type": "statistical",
    },
    "SLOPE_VOL": {
        "name": "斜率成交量策略",
        "description": "结合价格斜率和成交量的综合策略",
        "type": "volume_price",
    },
}


def get_strategy(strategy_code: str) -> Optional[Type[TimingStrategy]]:
    """根据策略代码获取策略类

    Args:
        strategy_code: 策略代码（如 "MA_TREND"）

    Returns:
        策略类，如果不存在则返回 None
    """
    return STRATEGY_REGISTRY.get(strategy_code)


def get_strategy_or_default(strategy_code: str, default: Type[TimingStrategy] = MATrendStrategy) -> Type[TimingStrategy]:
    """根据策略代码获取策略类，如果不存在则返回默认策略

    Args:
        strategy_code: 策略代码
        default: 默认策略类（默认为 MA_TREND）

    Returns:
        策略类
    """
    return STRATEGY_REGISTRY.get(strategy_code, default)


def list_strategies() -> list:
    """列出所有可用策略

    Returns:
        策略信息列表，每个元素包含 code, name, description, type
    """
    strategies = []
    for code, metadata in STRATEGY_METADATA.items():
        strategies.append({
            "code": code,
            **metadata,
        })
    return strategies


def register_strategy(code: str, strategy_class: Type[TimingStrategy], metadata: Dict[str, str] = None):
    """动态注册新策略（用于插件扩展）

    Args:
        code: 策略代码
        strategy_class: 策略类
        metadata: 策略元数据（可选）
    """
    STRATEGY_REGISTRY[code] = strategy_class
    if metadata:
        STRATEGY_METADATA[code] = metadata
