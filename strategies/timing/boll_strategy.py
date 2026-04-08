"""布林带突破策略"""
from datetime import date
from typing import Optional

import pandas as pd
from loguru import logger

from strategies.timing.base import TimingSignal, TimingStrategy


class BollingerStrategy(TimingStrategy):
    """布林带突破策略
    
    基于布林带上下轨突破产生信号：
    - 价格上穿上轨：强势买入信号
    - 价格下穿下轨：弱势卖出信号
    - 价格回到中轨：趋势可能反转
    """
    
    def __init__(self, params: Optional[dict] = None):
        default_params = {
            "period": 20,
            "std": 2,
        }
        if params:
            default_params.update(params)
        
        super().__init__("布林带突破", "BOLL_BREAKOUT", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算布林带指标"""
        df = data.copy()
        period = self.params["period"]
        std_multiplier = self.params["std"]
        
        # 计算中轨（移动平均线）
        df["BOLL_MIDDLE"] = df["close_price"].rolling(window=period).mean()
        
        # 计算标准差
        df["BOLL_STD"] = df["close_price"].rolling(window=period).std()
        
        # 计算上下轨
        df["BOLL_UPPER"] = df["BOLL_MIDDLE"] + std_multiplier * df["BOLL_STD"]
        df["BOLL_LOWER"] = df["BOLL_MIDDLE"] - std_multiplier * df["BOLL_STD"]
        
        # 计算带宽（波动率）
        df["BOLL_WIDTH"] = (df["BOLL_UPPER"] - df["BOLL_LOWER"]) / df["BOLL_MIDDLE"]
        
        # 计算价格在布林带中的位置
        df["BOLL_POSITION"] = (df["close_price"] - df["BOLL_LOWER"]) / (df["BOLL_UPPER"] - df["BOLL_LOWER"])
        
        # 计算突破状态
        df["break_upper"] = df["close_price"] > df["BOLL_UPPER"]
        df["break_lower"] = df["close_price"] < df["BOLL_LOWER"]
        
        return df
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TimingSignal]:
        """生成交易信号"""
        if len(data) < 2:
            return None
        
        current = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else current
        
        close = current.get("close_price")
        upper = current.get("BOLL_UPPER")
        lower = current.get("BOLL_LOWER")
        middle = current.get("BOLL_MIDDLE")
        width = current.get("BOLL_WIDTH")
        position = current.get("BOLL_POSITION")
        
        if pd.isna(upper) or pd.isna(lower) or pd.isna(middle):
            return None
        
        prev_close = prev.get("close_price")
        prev_upper = prev.get("BOLL_UPPER")
        prev_lower = prev.get("BOLL_LOWER")
        
        # 判断突破
        break_upper = prev_close <= prev_upper and close > upper
        break_lower = prev_close >= prev_lower and close < lower
        
        # 判断带宽（波动率）
        is_squeeze = width < 0.05 if not pd.isna(width) else False
        is_expanding = width > 0.1 if not pd.isna(width) else False
        
        # 生成信号
        if break_upper:
            signal_type = "strong_buy"
            strength = min((close - upper) / upper * 50 + 0.5, 1.0)
            reason = f"突破布林上轨({close:.2f} > {upper:.2f})，强势上涨"
        
        elif break_lower:
            signal_type = "strong_sell"
            strength = min((lower - close) / lower * 50 + 0.5, 1.0)
            reason = f"跌破布林下轨({close:.2f} < {lower:.2f})，弱势下跌"
        
        elif close > upper:
            # 在上轨上方运行
            signal_type = "buy"
            strength = 0.7
            reason = f"价格运行在上轨上方({close:.2f} > {upper:.2f})，维持强势"
        
        elif close < lower:
            # 在下轨下方运行
            signal_type = "sell"
            strength = 0.7
            reason = f"价格运行在下轨下方({close:.2f} < {lower:.2f})，维持弱势"
        
        elif is_squeeze and position > 0.4 and position < 0.6:
            # 布林带收窄且价格在中轨附近，可能即将突破
            signal_type = "hold"
            strength = 0.5
            reason = f"布林带收窄({width:.2%})，价格在中轨附近，等待突破"
        
        elif position > 0.8:
            # 接近上轨
            signal_type = "hold"
            strength = 0.4
            reason = f"价格接近上轨({position:.1%})，注意回调风险"
        
        elif position < 0.2:
            # 接近下轨
            signal_type = "hold"
            strength = 0.4
            reason = f"价格接近下轨({position:.1%})，关注反弹机会"
        
        else:
            signal_type = "hold"
            strength = 0.0
            reason = f"价格在布林带中轨附近运行({position:.1%})，维持观望"
        
        return TimingSignal(
            trade_date=current.get("trade_date", date.today()),
            signal_type=signal_type,
            strength=strength,
            market_index=current.get("index_code", "000001.SH"),
            index_close=close,
            reason=reason,
            indicators={
                "BOLL_UPPER": float(upper),
                "BOLL_MIDDLE": float(middle),
                "BOLL_LOWER": float(lower),
                "BOLL_WIDTH": float(width) if not pd.isna(width) else 0,
                "BOLL_POSITION": float(position) if not pd.isna(position) else 0.5,
            }
        )
