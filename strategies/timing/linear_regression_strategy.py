"""线性回归斜率策略"""
import pandas as pd
import numpy as np
from loguru import logger

from strategies.timing.base import TimingStrategy, TimingSignal


class LinearRegressionStrategy(TimingStrategy):
    """基于线性回归斜率的择时策略"""
    
    def __init__(self, params: dict = None):
        super().__init__("线性回归斜率策略", "LR_SLOPE", params)
        self.window = self.params.get("window", 20)  # 回归窗口
        self.threshold = self.params.get("threshold", 0.001)  # 斜率阈值
        self.confidence_threshold = self.params.get("confidence_threshold", 0.5)  # 置信度阈值
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算线性回归斜率和相关指标"""
        if len(data) < self.window:
            return data
        
        # 确保数据按日期排序
        data = data.sort_index()
        
        # 计算线性回归斜率
        slopes = []
        r_squared = []
        
        for i in range(len(data)):
            if i < self.window - 1:
                slopes.append(0)
                r_squared.append(0)
                continue
            
            # 获取窗口数据
            window_data = data.iloc[i - self.window + 1:i + 1]
            x = np.arange(self.window)
            y = window_data['close'].values
            
            # 线性回归
            slope, intercept = np.polyfit(x, y, 1)
            slopes.append(slope)
            
            # 计算R²
            correlation = np.corrcoef(x, y)[0, 1]
            r_squared.append(correlation ** 2)
        
        data['lr_slope'] = slopes
        data['r_squared'] = r_squared
        
        # 标准化斜率
        if len(data['lr_slope']) > 0:
            slope_mean = data['lr_slope'].mean()
            slope_std = data['lr_slope'].std()
            if slope_std > 0:
                data['lr_slope_norm'] = (data['lr_slope'] - slope_mean) / slope_std
        
        return data
    
    def generate_signal(self, data: pd.DataFrame) -> TimingSignal:
        """基于线性回归斜率生成交易信号"""
        if len(data) < self.window:
            return TimingSignal(
                trade_date=data.index[-1].date(),
                signal_type='hold',
                strength=0.5,
                market_index='000001.SH',
                index_close=data['close'].iloc[-1],
                reason="数据不足",
                indicators={}
            )
        
        latest = data.iloc[-1]
        slope = latest['lr_slope']
        r2 = latest['r_squared']
        
        # 计算信号强度
        strength = abs(slope) / (abs(slope) + 0.01) * r2
        strength = min(max(strength, 0), 1)
        
        # 生成信号
        if slope > self.threshold and r2 > self.confidence_threshold:
            signal_type = 'strong_buy' if slope > self.threshold * 2 else 'buy'
            reason = f"线性回归斜率为正 ({slope:.4f})，R²={r2:.2f}"
        elif slope < -self.threshold and r2 > self.confidence_threshold:
            signal_type = 'strong_sell' if slope < -self.threshold * 2 else 'sell'
            reason = f"线性回归斜率为负 ({slope:.4f})，R²={r2:.2f}"
        else:
            signal_type = 'hold'
            reason = f"线性回归斜率接近零 ({slope:.4f})，R²={r2:.2f}"
        
        return TimingSignal(
            trade_date=data.index[-1].date(),
            signal_type=signal_type,
            strength=strength,
            market_index='000001.SH',
            index_close=latest['close'],
            reason=reason,
            indicators={
                'lr_slope': slope,
                'r_squared': r2,
                'window': self.window,
                'threshold': self.threshold
            }
        )