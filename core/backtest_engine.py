"""回测引擎"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from config.settings import settings
from core.database import db
from strategies.timing import TimingSignal, TimingStrategy


@dataclass
class Position:
    """持仓"""
    stock_code: str
    stock_name: str
    volume: int = 0
    avg_cost: float = 0.0
    total_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    floating_pnl: float = 0.0
    floating_pnl_rate: float = 0.0


@dataclass
class BacktestState:
    """回测状态"""
    date: date
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    total_value: float = 0.0
    total_return: float = 0.0
    daily_return: float = 0.0
    drawdown: float = 0.0


class BacktestEngine:
    """回测引擎
    
    事件驱动的回测框架，支持择时策略回测
    """
    
    def __init__(
        self,
        initial_capital: float = 1000000.0,
        commission_rate: float = 0.00025,
        slippage: float = 0.001,
        position_limit: float = 1.0,
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.position_limit = position_limit
        
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.history: List[BacktestState] = []
        self.trades: List[dict] = []
        
        self.start_date: Optional[date] = None
        self.end_date: Optional[date] = None
        self.current_date: Optional[date] = None
        
        self.strategy: Optional[TimingStrategy] = None
        self.market_data: Optional[pd.DataFrame] = None
        
        self.max_value = initial_capital
        self.max_drawdown = 0.0
        
        logger.info(f"回测引擎初始化，初始资金: {initial_capital:,.2f}")
    
    def set_strategy(self, strategy: TimingStrategy) -> None:
        """设置策略"""
        self.strategy = strategy
        logger.info(f"设置回测策略: {strategy.name}")
    
    def set_market_data(self, data: pd.DataFrame) -> None:
        """设置市场数据"""
        self.market_data = data.copy()
        if not data.empty:
            self.start_date = data["trade_date"].min()
            self.end_date = data["trade_date"].max()
            logger.info(f"设置市场数据: {self.start_date} 到 {self.end_date}, 共 {len(data)} 条")
    
    def run(self) -> dict:
        """运行回测"""
        if self.strategy is None:
            raise ValueError("未设置策略")
        
        if self.market_data is None or self.market_data.empty:
            raise ValueError("未设置市场数据")
        
        logger.info("开始回测...")
        
        # 按日期遍历
        for date in sorted(self.market_data["trade_date"].unique()):
            self.current_date = date
            self._on_bar(date)
        
        # 计算回测结果
        results = self._calculate_results()
        
        logger.info("回测完成")
        return results
    
    def _on_bar(self, trade_date: date) -> None:
        """处理每个交易日"""
        # 获取当日数据
        day_data = self.market_data[self.market_data["trade_date"] == trade_date]
        if day_data.empty:
            return
        
        # 获取历史数据到当前日期
        hist_data = self.market_data[self.market_data["trade_date"] <= trade_date]
        
        # 生成信号
        signal = None
        if self.strategy:
            signal = self.strategy.get_latest_signal(hist_data)
        
        # 执行交易逻辑
        if signal:
            self._execute_signal(signal, day_data.iloc[-1])
        
        # 更新持仓市值
        self._update_positions(day_data.iloc[-1])
        
        # 记录状态
        self._record_state(trade_date)
    
    def _execute_signal(self, signal: TimingSignal, bar: pd.Series) -> None:
        """执行信号"""
        # 简化的交易逻辑
        if signal.signal_type in ("buy", "strong_buy"):
            # 买入信号 - 满仓买入
            if self.cash > 1000:  # 保留少量现金
                self._buy(bar["index_code"], bar["close_price"], int(self.cash * 0.99 / bar["close_price"]))
        
        elif signal.signal_type in ("sell", "strong_sell"):
            # 卖出信号 - 清仓
            for code, pos in list(self.positions.items()):
                if pos.volume > 0:
                    self._sell(code, bar["close_price"], pos.volume)
    
    def _buy(self, stock_code: str, price: float, volume: int) -> None:
        """买入"""
        if volume <= 0:
            return
        
        # 计算成本（含滑点和佣金）
        executed_price = price * (1 + self.slippage)
        amount = executed_price * volume
        commission = amount * self.commission_rate
        total_cost = amount + commission
        
        if total_cost > self.cash:
            return
        
        # 更新现金
        self.cash -= total_cost
        
        # 更新持仓
        if stock_code not in self.positions:
            self.positions[stock_code] = Position(
                stock_code=stock_code,
                stock_name=stock_code,
                volume=volume,
                avg_cost=executed_price,
                total_cost=total_cost,
            )
        else:
            pos = self.positions[stock_code]
            new_volume = pos.volume + volume
            new_cost = pos.total_cost + total_cost
            pos.volume = new_volume
            pos.avg_cost = new_cost / new_volume
            pos.total_cost = new_cost
        
        # 记录交易
        self.trades.append({
            "date": self.current_date,
            "code": stock_code,
            "type": "buy",
            "price": executed_price,
            "volume": volume,
            "amount": amount,
            "commission": commission,
        })
        
        logger.debug(f"买入 {stock_code} {volume}股 @ {executed_price:.2f}")
    
    def _sell(self, stock_code: str, price: float, volume: int) -> None:
        """卖出"""
        if stock_code not in self.positions:
            return
        
        pos = self.positions[stock_code]
        volume = min(volume, pos.volume)
        
        if volume <= 0:
            return
        
        # 计算收入（扣除滑点和佣金）
        executed_price = price * (1 - self.slippage)
        amount = executed_price * volume
        commission = amount * self.commission_rate
        stamp_tax = amount * 0.001  # 印花税
        net_amount = amount - commission - stamp_tax
        
        # 计算盈亏
        cost = pos.avg_cost * volume
        pnl = net_amount - cost
        
        # 更新现金
        self.cash += net_amount
        
        # 更新持仓
        pos.volume -= volume
        if pos.volume == 0:
            del self.positions[stock_code]
        else:
            pos.total_cost = pos.avg_cost * pos.volume
        
        # 记录交易
        self.trades.append({
            "date": self.current_date,
            "code": stock_code,
            "type": "sell",
            "price": executed_price,
            "volume": volume,
            "amount": amount,
            "commission": commission + stamp_tax,
            "pnl": pnl,
        })
        
        logger.debug(f"卖出 {stock_code} {volume}股 @ {executed_price:.2f}, 盈亏: {pnl:.2f}")
    
    def _update_positions(self, bar: pd.Series) -> None:
        """更新持仓市值"""
        price = bar["close_price"]
        
        for pos in self.positions.values():
            pos.current_price = price
            pos.market_value = pos.volume * price
            pos.floating_pnl = pos.market_value - pos.total_cost
            if pos.total_cost > 0:
                pos.floating_pnl_rate = pos.floating_pnl / pos.total_cost
    
    def _record_state(self, trade_date: date) -> None:
        """记录状态"""
        # 计算总市值
        position_value = sum(pos.market_value for pos in self.positions.values())
        total_value = self.cash + position_value
        
        # 计算回撤
        if total_value > self.max_value:
            self.max_value = total_value
        drawdown = (self.max_value - total_value) / self.max_value if self.max_value > 0 else 0
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        # 计算日收益
        daily_return = 0
        if self.history:
            prev_value = self.history[-1].total_value
            if prev_value > 0:
                daily_return = (total_value - prev_value) / prev_value
        
        state = BacktestState(
            date=trade_date,
            cash=self.cash,
            positions=self.positions.copy(),
            total_value=total_value,
            total_return=(total_value - self.initial_capital) / self.initial_capital,
            daily_return=daily_return,
            drawdown=drawdown,
        )
        
        self.history.append(state)
    
    def _calculate_results(self) -> dict:
        """计算回测结果"""
        if not self.history:
            return {}
        
        final_state = self.history[-1]
        total_return = final_state.total_return
        
        # 计算年化收益
        days = (self.end_date - self.start_date).days if self.start_date and self.end_date else 1
        years = days / 365
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 计算夏普比率（简化版，假设无风险利率为3%）
        daily_returns = [s.daily_return for s in self.history if s.daily_return != 0]
        if daily_returns:
            avg_return = sum(daily_returns) / len(daily_returns)
            std_return = (sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5
            sharpe_ratio = (avg_return * 252 - 0.03) / (std_return * (252 ** 0.5)) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 准备图表数据
        nav_data = [
            {
                "date": str(state.date),
                "nav": state.total_value / self.initial_capital,
                "total_value": state.total_value,
                "daily_return": state.daily_return,
                "drawdown": state.drawdown,
            }
            for state in self.history
        ]
        
        return {
            "initial_capital": self.initial_capital,
            "final_capital": final_state.total_value,
            "total_return": total_return,
            "annualized_return": annualized_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "total_trades": len(self.trades),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "history": self.history,
            "trades": self.trades,
            "nav_data": nav_data,
        }
