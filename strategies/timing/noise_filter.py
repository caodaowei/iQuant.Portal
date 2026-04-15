"""分钟级噪声过滤方法"""
import pandas as pd
import numpy as np
from loguru import logger


def filter_minute_noise(data: pd.DataFrame, method: str = 'ma', **kwargs) -> pd.DataFrame:
    """
    分钟级数据噪声过滤
    
    Args:
        data: 分钟级数据，包含'close'列
        method: 过滤方法，可选 'ma'（移动平均）、'ema'（指数移动平均）、'kalman'（卡尔曼滤波）
        **kwargs: 方法参数
            - window: 移动平均窗口大小，默认10
            - alpha: EMA平滑系数，默认0.1
    
    Returns:
        过滤后的数据
    """
    if data.empty:
        return data
    
    # 确保数据按时间排序
    data = data.sort_index()
    
    if method == 'ma':
        # 简单移动平均过滤
        window = kwargs.get('window', 10)
        data['filtered_close'] = data['close'].rolling(window=window).mean()
        data['noise'] = data['close'] - data['filtered_close']
        
    elif method == 'ema':
        # 指数移动平均过滤
        alpha = kwargs.get('alpha', 0.1)
        data['filtered_close'] = data['close'].ewm(alpha=alpha).mean()
        data['noise'] = data['close'] - data['filtered_close']
        
    elif method == 'kalman':
        # 卡尔曼滤波
        data['filtered_close'] = kalman_filter(data['close'].values)
        data['noise'] = data['close'] - data['filtered_close']
        
    else:
        logger.warning(f"未知的过滤方法: {method}，使用默认的移动平均方法")
        window = kwargs.get('window', 10)
        data['filtered_close'] = data['close'].rolling(window=window).mean()
        data['noise'] = data['close'] - data['filtered_close']
    
    # 计算噪声强度
    if len(data) > 0:
        data['noise_strength'] = abs(data['noise']) / data['close']
    
    return data


def kalman_filter(data: np.ndarray) -> np.ndarray:
    """
    卡尔曼滤波器
    
    Args:
        data: 输入数据
    
    Returns:
        过滤后的数据
    """
    n = len(data)
    filtered_data = np.zeros(n)
    
    # 初始化
    x = data[0]
    P = 1.0
    Q = 0.01  # 过程噪声协方差
    R = 0.1   # 测量噪声协方差
    
    for i in range(n):
        # 预测
        x_pred = x
        P_pred = P + Q
        
        # 更新
        K = P_pred / (P_pred + R)
        x = x_pred + K * (data[i] - x_pred)
        P = (1 - K) * P_pred
        
        filtered_data[i] = x
    
    return filtered_data


def detect_anomalies(data: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
    """
    检测分钟级数据中的异常点
    
    Args:
        data: 包含'noise'列的数据
        threshold: 异常阈值（标准差倍数）
    
    Returns:
        标记了异常点的数据
    """
    if 'noise' not in data.columns:
        data = filter_minute_noise(data)
    
    # 计算噪声的均值和标准差
    noise_mean = data['noise'].mean()
    noise_std = data['noise'].std()
    
    # 标记异常点
    data['is_anomaly'] = abs(data['noise'] - noise_mean) > threshold * noise_std
    
    return data


def smooth_minute_data(data: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    平滑分钟级数据
    
    Args:
        data: 分钟级数据
        window: 平滑窗口
    
    Returns:
        平滑后的数据
    """
    # 对所有数值列进行平滑
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        data[f'{col}_smoothed'] = data[col].rolling(window=window).mean()
    
    return data