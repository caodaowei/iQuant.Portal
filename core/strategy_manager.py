"""策略管理器"""
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from strategies.timing import (
    BollingerStrategy,
    MACDStrategy,
    MATrendStrategy,
    RSIStrategy,
    LinearRegressionStrategy,
    SlopeVolumeStrategy,
    TimingSignal,
    TimingStrategy,
)


class StrategyManager:
    """策略管理器
    
    统一管理多个择时策略，支持策略组合和信号聚合
    """
    
    # 策略注册表
    STRATEGY_REGISTRY = {
        "MA_TREND": MATrendStrategy,
        "MACD_SIGNAL": MACDStrategy,
        "RSI_MEAN_REVERT": RSIStrategy,
        "BOLL_BREAKOUT": BollingerStrategy,
        "LR_SLOPE": LinearRegressionStrategy,
        "SLOPE_VOL": SlopeVolumeStrategy,
    }
    
    def __init__(self):
        self.strategies: Dict[str, TimingStrategy] = {}
        self.active_strategies: List[str] = []
        logger.info("策略管理器初始化")
    
    def register_strategy(
        self,
        strategy_code: str,
        params: Optional[dict] = None,
        active: bool = True,
    ) -> TimingStrategy:
        """注册策略"""
        if strategy_code not in self.STRATEGY_REGISTRY:
            raise ValueError(f"未知策略: {strategy_code}")
        
        strategy_class = self.STRATEGY_REGISTRY[strategy_code]
        strategy = strategy_class(params)
        
        self.strategies[strategy_code] = strategy
        
        if active:
            if strategy_code not in self.active_strategies:
                self.active_strategies.append(strategy_code)
        
        logger.info(f"注册策略: {strategy_code} ({strategy.name})")
        return strategy
    
    def unregister_strategy(self, strategy_code: str) -> None:
        """注销策略"""
        if strategy_code in self.strategies:
            del self.strategies[strategy_code]
        
        if strategy_code in self.active_strategies:
            self.active_strategies.remove(strategy_code)
        
        logger.info(f"注销策略: {strategy_code}")
    
    def set_strategy_active(self, strategy_code: str, active: bool) -> None:
        """设置策略激活状态"""
        if strategy_code not in self.strategies:
            raise ValueError(f"策略未注册: {strategy_code}")
        
        if active and strategy_code not in self.active_strategies:
            self.active_strategies.append(strategy_code)
        elif not active and strategy_code in self.active_strategies:
            self.active_strategies.remove(strategy_code)
        
        logger.info(f"设置策略 {strategy_code} 激活状态: {active}")
    
    def run_all(
        self,
        market_data: pd.DataFrame,
    ) -> Dict[str, List[TimingSignal]]:
        """运行所有激活的策略"""
        results = {}
        
        for strategy_code in self.active_strategies:
            strategy = self.strategies.get(strategy_code)
            if strategy:
                signals = strategy.run(market_data)
                results[strategy_code] = signals
                logger.debug(f"策略 {strategy_code} 生成 {len(signals)} 个信号")
        
        return results
    
    def get_consensus_signal(
        self,
        market_data: pd.DataFrame,
        method: str = "majority",
    ) -> Optional[TimingSignal]:
        """获取共识信号
        
        Args:
            market_data: 市场数据
            method: 聚合方法，可选 'majority'(多数表决), 'weighted'(加权平均)
        
        Returns:
            聚合后的信号
        """
        if not self.active_strategies:
            logger.warning("没有激活的策略")
            return None
        
        # 获取所有策略的最新信号
        latest_signals = []
        for strategy_code in self.active_strategies:
            strategy = self.strategies.get(strategy_code)
            if strategy:
                signal = strategy.get_latest_signal(market_data)
                if signal:
                    latest_signals.append((strategy_code, signal))
        
        if not latest_signals:
            logger.warning("没有生成信号")
            return None
        
        if method == "majority":
            return self._majority_vote(latest_signals)
        elif method == "weighted":
            return self._weighted_average(latest_signals)
        else:
            raise ValueError(f"未知的聚合方法: {method}")
    
    def _majority_vote(
        self,
        signals: List[tuple],
    ) -> Optional[TimingSignal]:
        """多数表决"""
        from collections import Counter
        
        # 统计信号类型
        signal_types = [s.signal_type for _, s in signals]
        type_counts = Counter(signal_types)
        
        # 找出最多的信号类型
        majority_type, count = type_counts.most_common(1)[0]
        
        # 如果多数是hold，检查是否有强烈的买卖信号
        if majority_type == "hold" and len(signals) >= 3:
            buy_signals = [s for _, s in signals if s.signal_type in ("buy", "strong_buy")]
            sell_signals = [s for _, s in signals if s.signal_type in ("sell", "strong_sell")]
            
            if len(buy_signals) >= 2:
                majority_type = "buy"
            elif len(sell_signals) >= 2:
                majority_type = "sell"
        
        # 计算平均强度
        avg_strength = sum(s.strength for _, s in signals) / len(signals)
        
        # 获取参考信号（第一个多数信号）
        ref_signal = next(s for _, s in signals if s.signal_type == majority_type)
        
        # 构建共识信号
        return TimingSignal(
            trade_date=ref_signal.trade_date,
            signal_type=majority_type,
            strength=avg_strength,
            market_index=ref_signal.market_index,
            index_close=ref_signal.index_close,
            reason=f"多数表决结果 ({count}/{len(signals)} 策略一致)",
            indicators={"consensus": True, "strategy_count": len(signals)},
        )
    
    def _weighted_average(
        self,
        signals: List[tuple],
    ) -> Optional[TimingSignal]:
        """加权平均"""
        # 简单平均权重
        weights = {code: 1.0 for code, _ in signals}
        
        # 信号类型映射到数值
        type_values = {
            "strong_buy": 2,
            "buy": 1,
            "hold": 0,
            "sell": -1,
            "strong_sell": -2,
        }
        
        # 计算加权平均值
        total_weight = sum(weights.values())
        weighted_sum = sum(
            type_values.get(s.signal_type, 0) * weights.get(code, 1.0)
            for code, s in signals
        )
        avg_value = weighted_sum / total_weight
        
        # 映射回信号类型
        if avg_value >= 1.5:
            signal_type = "strong_buy"
        elif avg_value >= 0.5:
            signal_type = "buy"
        elif avg_value <= -1.5:
            signal_type = "strong_sell"
        elif avg_value <= -0.5:
            signal_type = "sell"
        else:
            signal_type = "hold"
        
        # 计算平均强度
        avg_strength = sum(s.strength for _, s in signals) / len(signals)
        
        ref_signal = signals[0][1]
        
        return TimingSignal(
            trade_date=ref_signal.trade_date,
            signal_type=signal_type,
            strength=avg_strength,
            market_index=ref_signal.market_index,
            index_close=ref_signal.index_close,
            reason=f"加权平均结果 (平均值: {avg_value:.2f})",
            indicators={"consensus": True, "weighted_avg": avg_value},
        )
    
    def list_strategies(self) -> List[dict]:
        """列出所有策略"""
        return [
            {
                "code": code,
                "name": strategy.name,
                "type": strategy.code,
                "active": code in self.active_strategies,
                "params": strategy.params,
            }
            for code, strategy in self.strategies.items()
        ]


# 全局策略管理器实例
strategy_manager = StrategyManager()
