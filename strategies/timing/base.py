"""择时策略基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import pandas as pd
from loguru import logger


@dataclass
class TimingSignal:
    """择时信号"""
    trade_date: date
    signal_type: str  # 'buy', 'sell', 'hold', 'strong_buy', 'strong_sell'
    strength: float  # 0-1
    market_index: str
    index_close: float
    reason: str
    indicators: dict


class TimingStrategy(ABC):
    """择时策略基类"""
    
    def __init__(self, name: str, code: str, params: Optional[dict] = None):
        self.name = name
        self.code = code
        self.params = params or {}
        self.is_initialized = False
        logger.info(f"初始化策略: {name} ({code})")
    
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        pass
    
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Optional[TimingSignal]:
        """生成交易信号"""
        pass
    
    def run(self, market_data: pd.DataFrame) -> List[TimingSignal]:
        """运行策略"""
        if market_data.empty:
            logger.warning("市场数据为空")
            return []
        
        # 计算指标
        data_with_indicators = self.calculate_indicators(market_data.copy())
        
        # 生成信号 - 遍历所有数据点
        signals = []
        for i in range(1, len(data_with_indicators)):
            # 使用前i+1条数据来生成信号，这样可以使用历史数据计算指标
            row = data_with_indicators.iloc[:i+1]
            signal = self.generate_signal(row)
            if signal:
                signals.append(signal)
        
        return signals
    
    def get_latest_signal(self, market_data: pd.DataFrame) -> Optional[TimingSignal]:
        """获取最新信号"""
        signals = self.run(market_data)
        return signals[-1] if signals else None
