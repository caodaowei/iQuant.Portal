"""均线趋势策略"""
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from strategies.timing.base import TimingSignal, TimingStrategy


class MATrendStrategy(TimingStrategy):
    """均线趋势策略
    
    基于多条均线判断趋势方向：
    - 短期均线上穿长期均线：买入信号
    - 短期均线下穿长期均线：卖出信号
    """
    
    def __init__(self, params: Optional[dict] = None):
        default_params = {
            "short_ma": 5,
            "medium_ma": 20,
            "long_ma": 60,
            "threshold": 0.02,  # 信号阈值
        }
        if params:
            default_params.update(params)
        
        super().__init__("均线趋势策略", "MA_TREND", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算均线指标"""
        df = data.copy()
        
        short_period = self.params["short_ma"]
        medium_period = self.params["medium_ma"]
        long_period = self.params["long_ma"]
        
        # 计算均线
        df[f"MA{short_period}"] = df["close_price"].rolling(window=short_period).mean()
        df[f"MA{medium_period}"] = df["close_price"].rolling(window=medium_period).mean()
        df[f"MA{long_period}"] = df["close_price"].rolling(window=long_period).mean()
        
        # 计算均线差值
        df["MA_diff_short_medium"] = df[f"MA{short_period}"] - df[f"MA{medium_period}"]
        df["MA_diff_medium_long"] = df[f"MA{medium_period}"] - df[f"MA{long_period}"]
        
        # 计算趋势强度
        df["trend_strength"] = (df[f"MA{short_period}"] - df[f"MA{long_period}"]) / df[f"MA{long_period}"]
        
        return df
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TimingSignal]:
        """生成交易信号"""
        if len(data) < 2:
            return None
        
        current = data.iloc[-1]
        
        # 检查必要字段
        short_period = self.params["short_ma"]
        medium_period = self.params["medium_ma"]
        long_period = self.params["long_ma"]
        
        ma_short = current.get(f"MA{short_period}")
        ma_medium = current.get(f"MA{medium_period}")
        ma_long = current.get(f"MA{long_period}")
        
        if pd.isna(ma_short) or pd.isna(ma_medium) or pd.isna(ma_long):
            return None
        
        # 判断趋势
        trend_strength = current.get("trend_strength", 0)
        threshold = self.params["threshold"]
        
        # 生成信号
        if ma_short > ma_medium > ma_long and trend_strength > threshold:
            signal_type = "strong_buy" if trend_strength > threshold * 2 else "buy"
            strength = min(abs(trend_strength) * 10, 1.0)
            reason = f"多头排列，短期MA{short_period}({ma_short:.2f}) > 中期MA{medium_period}({ma_medium:.2f}) > 长期MA{long_period}({ma_long:.2f})"
        
        elif ma_short < ma_medium < ma_long and trend_strength < -threshold:
            signal_type = "strong_sell" if trend_strength < -threshold * 2 else "sell"
            strength = min(abs(trend_strength) * 10, 1.0)
            reason = f"空头排列，短期MA{short_period}({ma_short:.2f}) < 中期MA{medium_period}({ma_medium:.2f}) < 长期MA{long_period}({ma_long:.2f})"
        
        else:
            signal_type = "hold"
            strength = 0.0
            reason = "趋势不明，维持观望"
        
        return TimingSignal(
            trade_date=current.get("trade_date", date.today()),
            signal_type=signal_type,
            strength=strength,
            market_index=current.get("index_code", "000001.SH"),
            index_close=current.get("close_price", 0),
            reason=reason,
            indicators={
                f"MA{short_period}": float(ma_short),
                f"MA{medium_period}": float(ma_medium),
                f"MA{long_period}": float(ma_long),
                "trend_strength": float(trend_strength),
            }
        )
