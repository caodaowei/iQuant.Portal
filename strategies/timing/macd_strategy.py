"""MACD策略"""
from datetime import date
from typing import Optional

import pandas as pd
from loguru import logger

from strategies.timing.base import TimingSignal, TimingStrategy


class MACDStrategy(TimingStrategy):
    """MACD信号策略
    
    基于MACD金叉死叉产生信号：
    - MACD上穿信号线：买入信号
    - MACD下穿信号线：卖出信号
    """
    
    def __init__(self, params: Optional[dict] = None):
        default_params = {
            "fast": 12,
            "slow": 26,
            "signal": 9,
        }
        if params:
            default_params.update(params)
        
        super().__init__("MACD信号策略", "MACD_SIGNAL", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算MACD指标"""
        df = data.copy()
        
        fast = self.params["fast"]
        slow = self.params["slow"]
        signal_period = self.params["signal"]
        
        # 计算EMA
        ema_fast = df["close_price"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close_price"].ewm(span=slow, adjust=False).mean()
        
        # 计算MACD
        df["MACD"] = ema_fast - ema_slow
        df["MACD_SIGNAL"] = df["MACD"].ewm(span=signal_period, adjust=False).mean()
        df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]
        
        # 计算MACD变化
        df["MACD_change"] = df["MACD_HIST"].diff()
        
        return df
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TimingSignal]:
        """生成交易信号"""
        if len(data) < 2:
            return None
        
        current = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else current
        
        macd = current.get("MACD")
        signal = current.get("MACD_SIGNAL")
        hist = current.get("MACD_HIST")
        prev_hist = prev.get("MACD_HIST")
        
        if pd.isna(macd) or pd.isna(signal) or pd.isna(hist):
            return None
        
        # 判断金叉死叉
        if prev_hist < 0 and hist > 0:
            # 金叉
            signal_type = "buy"
            strength = min(abs(hist) * 5, 1.0)
            reason = f"MACD金叉，MACD({macd:.3f})上穿信号线({signal:.3f})"
        
        elif prev_hist > 0 and hist < 0:
            # 死叉
            signal_type = "sell"
            strength = min(abs(hist) * 5, 1.0)
            reason = f"MACD死叉，MACD({macd:.3f})下穿信号线({signal:.3f})"
        
        elif hist > 0 and hist > prev_hist:
            # 多头增强
            signal_type = "hold"
            strength = min(hist * 3, 0.7)
            reason = f"多头趋势增强，柱状图扩大({hist:.3f})"
        
        elif hist < 0 and hist < prev_hist:
            # 空头增强
            signal_type = "hold"
            strength = min(abs(hist) * 3, 0.7)
            reason = f"空头趋势增强，柱状图扩大({hist:.3f})"
        
        else:
            signal_type = "hold"
            strength = 0.0
            reason = "MACD趋势平稳，维持观望"
        
        return TimingSignal(
            trade_date=current.get("trade_date", date.today()),
            signal_type=signal_type,
            strength=strength,
            market_index=current.get("index_code", "000001.SH"),
            index_close=current.get("close_price", 0),
            reason=reason,
            indicators={
                "MACD": float(macd),
                "MACD_SIGNAL": float(signal),
                "MACD_HIST": float(hist),
            }
        )
