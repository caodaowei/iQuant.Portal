"""斜率+成交量组合信号策略"""
import pandas as pd
import numpy as np
from loguru import logger

from strategies.timing.base import TimingStrategy, TimingSignal


class SlopeVolumeStrategy(TimingStrategy):
    """基于线性回归斜率和成交量的组合信号策略"""
    
    def __init__(self, params: dict = None):
        super().__init__("斜率成交量组合策略", "SLOPE_VOL", params)
        self.slope_window = self.params.get("slope_window", 20)  # 回归窗口
        self.volume_window = self.params.get("volume_window", 10)  # 成交量窗口
        self.slope_threshold = self.params.get("slope_threshold", 0.001)  # 斜率阈值
        self.volume_threshold = self.params.get("volume_threshold", 1.5)  # 成交量阈值（倍数）
        self.confidence_threshold = self.params.get("confidence_threshold", 0.5)  # 置信度阈值
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算线性回归斜率和成交量相关指标"""
        if len(data) < max(self.slope_window, self.volume_window):
            return data
        
        # 确保数据按日期排序
        data = data.sort_index()
        
        # 计算线性回归斜率
        slopes = []
        r_squared = []
        
        for i in range(len(data)):
            if i < self.slope_window - 1:
                slopes.append(0)
                r_squared.append(0)
                continue
            
            # 获取窗口数据
            window_data = data.iloc[i - self.slope_window + 1:i + 1]
            x = np.arange(self.slope_window)
            y = window_data['close'].values
            
            # 线性回归
            slope, intercept = np.polyfit(x, y, 1)
            slopes.append(slope)
            
            # 计算R²
            correlation = np.corrcoef(x, y)[0, 1]
            r_squared.append(correlation ** 2)
        
        data['lr_slope'] = slopes
        data['r_squared'] = r_squared
        
        # 计算成交量指标
        data['volume_ma'] = data['volume'].rolling(window=self.volume_window).mean()
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        
        # 标准化斜率
        if len(data['lr_slope']) > 0:
            slope_mean = data['lr_slope'].mean()
            slope_std = data['lr_slope'].std()
            if slope_std > 0:
                data['lr_slope_norm'] = (data['lr_slope'] - slope_mean) / slope_std
        
        return data
    
    def generate_signal(self, data: pd.DataFrame) -> TimingSignal:
        """基于斜率和成交量生成交易信号"""
        if len(data) < max(self.slope_window, self.volume_window):
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
        volume_ratio = latest['volume_ratio']
        
        # 计算信号强度
        slope_strength = abs(slope) / (abs(slope) + 0.01) * r2
        volume_strength = min(volume_ratio / (volume_ratio + 1), 1)
        strength = (slope_strength * 0.6 + volume_strength * 0.4)  # 斜率权重60%，成交量权重40%
        strength = min(max(strength, 0), 1)
        
        # 生成信号
        if slope > self.slope_threshold and r2 > self.confidence_threshold:
            if volume_ratio > self.volume_threshold:
                signal_type = 'strong_buy'
                reason = f"斜率为正 ({slope:.4f})，成交量放大 ({volume_ratio:.2f}倍)，R²={r2:.2f}"
            else:
                signal_type = 'buy'
                reason = f"斜率为正 ({slope:.4f})，成交量正常 ({volume_ratio:.2f}倍)，R²={r2:.2f}"
        elif slope < -self.slope_threshold and r2 > self.confidence_threshold:
            if volume_ratio > self.volume_threshold:
                signal_type = 'strong_sell'
                reason = f"斜率为负 ({slope:.4f})，成交量放大 ({volume_ratio:.2f}倍)，R²={r2:.2f}"
            else:
                signal_type = 'sell'
                reason = f"斜率为负 ({slope:.4f})，成交量正常 ({volume_ratio:.2f}倍)，R²={r2:.2f}"
        else:
            signal_type = 'hold'
            reason = f"斜率接近零 ({slope:.4f})，成交量 ({volume_ratio:.2f}倍)，R²={r2:.2f}"
        
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
                'volume_ratio': volume_ratio,
                'slope_window': self.slope_window,
                'volume_window': self.volume_window,
                'slope_threshold': self.slope_threshold,
                'volume_threshold': self.volume_threshold
            }
        )