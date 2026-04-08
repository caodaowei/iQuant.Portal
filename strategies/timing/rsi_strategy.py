"""RSI均值回归策略"""
from datetime import date
from typing import Optional

import pandas as pd
from loguru import logger

from strategies.timing.base import TimingSignal, TimingStrategy


class RSIStrategy(TimingStrategy):
    """RSI均值回归策略
    
    基于RSI超买超卖产生信号：
    - RSI < 超卖线：买入信号
    - RSI > 超买线：卖出信号
    """
    
    def __init__(self, params: Optional[dict] = None):
        default_params = {
            "period": 14,
            "overbought": 70,
            "oversold": 30,
            "middle": 50,
        }
        if params:
            default_params.update(params)
        
        super().__init__("RSI均值回归", "RSI_MEAN_REVERT", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算RSI指标"""
        df = data.copy()
        period = self.params["period"]
        
        # 计算价格变化
        delta = df["close_price"].diff()
        
        # 分离涨跌
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        # 计算平均涨跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 计算RS和RSI
        rs = avg_gain / avg_loss
        df["RSI"] = 100 - (100 / (1 + rs))
        
        # 计算RSI变化
        df["RSI_change"] = df["RSI"].diff()
        
        # 计算RSI斜率（趋势）
        df["RSI_slope"] = df["RSI"].rolling(window=5).apply(
            lambda x: (x.iloc[-1] - x.iloc[0]) / 5, raw=False
        )
        
        return df
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TimingSignal]:
        """生成交易信号"""
        if len(data) < 2:
            return None
        
        current = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else current
        
        rsi = current.get("RSI")
        prev_rsi = prev.get("RSI")
        rsi_slope = current.get("RSI_slope")
        
        if pd.isna(rsi):
            return None
        
        overbought = self.params["overbought"]
        oversold = self.params["oversold"]
        middle = self.params["middle"]
        
        # 判断信号
        if prev_rsi < oversold and rsi > prev_rsi:
            # 超卖区反弹
            signal_type = "buy"
            strength = min((oversold - rsi) / 20 + 0.3, 1.0)
            reason = f"RSI超卖反弹，RSI从{prev_rsi:.1f}上升至{rsi:.1f}"
        
        elif prev_rsi > overbought and rsi < prev_rsi:
            # 超买区回落
            signal_type = "sell"
            strength = min((rsi - overbought) / 20 + 0.3, 1.0)
            reason = f"RSI超买回落，RSI从{prev_rsi:.1f}下降至{rsi:.1f}"
        
        elif rsi < oversold:
            # 超卖区
            signal_type = "strong_buy"
            strength = min((oversold - rsi) / 10, 1.0)
            reason = f"RSI严重超卖({rsi:.1f} < {oversold})，建议买入"
        
        elif rsi > overbought:
            # 超买区
            signal_type = "strong_sell"
            strength = min((rsi - overbought) / 10, 1.0)
            reason = f"RSI严重超买({rsi:.1f} > {overbought})，建议卖出"
        
        elif rsi_slope and rsi_slope > 0 and rsi > middle:
            # RSI上升趋势
            signal_type = "hold"
            strength = min((rsi - middle) / 30, 0.6)
            reason = f"RSI上升趋势({rsi_slope:.2f})，维持多头"
        
        elif rsi_slope and rsi_slope < 0 and rsi < middle:
            # RSI下降趋势
            signal_type = "hold"
            strength = min((middle - rsi) / 30, 0.6)
            reason = f"RSI下降趋势({rsi_slope:.2f})，维持空头"
        
        else:
            signal_type = "hold"
            strength = 0.0
            reason = f"RSI中性区域({rsi:.1f})，维持观望"
        
        return TimingSignal(
            trade_date=current.get("trade_date", date.today()),
            signal_type=signal_type,
            strength=strength,
            market_index=current.get("index_code", "000001.SH"),
            index_close=current.get("close_price", 0),
            reason=reason,
            indicators={
                "RSI": float(rsi),
                "RSI_change": float(current.get("RSI_change", 0)),
                "RSI_slope": float(rsi_slope) if rsi_slope else 0,
            }
        )
