"""交易执行模块"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from config.settings import settings
from core.database import db
from core.risk_engine import RiskCheckReport, risk_engine


@dataclass
class Order:
    """订单"""
    order_no: str
    account_id: int
    stock_code: str
    stock_name: str
    trade_type: str  # 'buy', 'sell'
    order_type: str  # 'market', 'limit'
    volume: int
    price: float
    status: str = "pending"  # 'pending', 'submitted', 'filled', 'cancelled', 'rejected'


@dataclass
class Trade:
    """成交"""
    trade_no: str
    order_no: str
    stock_code: str
    trade_type: str
    volume: int
    price: float
    amount: float
    commission: float
    trade_time: datetime


class TradingExecutor:
    """交易执行器"""
    
    def __init__(self, account_id: int = 1):
        self.account_id = account_id
        self.commission_rate = settings.commission_rate
        self.slippage = settings.slippage
        logger.info(f"交易执行器初始化，账户ID: {account_id}")
    
    def get_account_info(self) -> dict:
        """获取账户信息"""
        try:
            result = db.fetch_one(
                "SELECT total_capital, available_cash FROM trading_accounts WHERE id = :id",
                {"id": self.account_id}
            )
            
            if result:
                return {
                    "total_capital": result[0],
                    "available_cash": result[1],
                }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
        
        return {"total_capital": 0, "available_cash": 0}
    
    def get_position(self, stock_code: str) -> dict:
        """获取持仓"""
        try:
            result = db.fetch_one(
                """SELECT total_volume, available_volume, avg_cost 
                   FROM position_details 
                   WHERE account_id = :account_id AND stock_code = :code""",
                {"account_id": self.account_id, "code": stock_code}
            )
            
            if result:
                return {
                    "total_volume": result[0],
                    "available_volume": result[1],
                    "avg_cost": result[2],
                }
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
        
        return {"total_volume": 0, "available_volume": 0, "avg_cost": 0}
    
    def check_risk(
        self,
        stock_code: str,
        trade_type: str,
        volume: int,
        price: float,
    ) -> RiskCheckReport:
        """风险检查"""
        # 获取账户信息
        account = self.get_account_info()
        position = self.get_position(stock_code)
        
        # 计算持仓比例
        position_value = position["total_volume"] * price
        position_ratio = float(position_value) / float(account["total_capital"]) if account["total_capital"] > 0 else 0
        
        # 计算现金比例
        cash_ratio = float(account["available_cash"]) / float(account["total_capital"]) if account["total_capital"] > 0 else 0
        
        context = {
            "account_id": self.account_id,
            "total_capital": account["total_capital"],
            "available_cash": account["available_cash"],
            "position_value": position_value,
            "position_ratio": position_ratio,
            "cash_ratio": cash_ratio,
            "check_type": "pre_trade",
        }
        
        return risk_engine.check_trade(stock_code, trade_type, volume, price, context)
    
    def submit_order(
        self,
        stock_code: str,
        trade_type: str,
        volume: int,
        price: Optional[float] = None,
        order_type: str = "market",
    ) -> Optional[Order]:
        """提交订单"""
        # 生成订单号
        order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"
        
        # 获取当前价格（如果是市价单）
        if price is None or order_type == "market":
            price = self._get_current_price(stock_code)
        
        # 风险检查
        risk_report = self.check_risk(stock_code, trade_type, volume, price)
        
        if not risk_engine.can_trade(risk_report):
            logger.warning(f"订单 {order_no} 未通过风控检查")
            return None
        
        # 创建订单
        order = Order(
            order_no=order_no,
            account_id=self.account_id,
            stock_code=stock_code,
            stock_name=stock_code,  # TODO: 查询股票名称
            trade_type=trade_type,
            order_type=order_type,
            volume=volume,
            price=price,
            status="submitted",
        )
        
        # 保存到数据库
        try:
            db.execute("""
                INSERT INTO trade_orders 
                (order_no, account_id, stock_code, stock_name, trade_type, order_type, 
                 order_volume, order_price, status, submit_time)
                VALUES (:order_no, :account_id, :code, :name, :trade_type, :order_type,
                        :volume, :price, :status, CURRENT_TIMESTAMP)
            """, {
                "order_no": order.order_no,
                "account_id": order.account_id,
                "code": order.stock_code,
                "name": order.stock_name,
                "trade_type": order.trade_type,
                "order_type": order.order_type,
                "volume": order.volume,
                "price": order.price,
                "status": order.status,
            })
            
            logger.info(f"提交订单: {order_no} {trade_type} {stock_code} {volume}股 @ {price}")
            return order
            
        except Exception as e:
            logger.error(f"保存订单失败: {e}")
            return None
    
    def execute_order(self, order: Order) -> Optional[Trade]:
        """执行订单（模拟成交）"""
        # 模拟成交价格（考虑滑点）
        if order.trade_type == "buy":
            executed_price = order.price * (1 + self.slippage)
        else:
            executed_price = order.price * (1 - self.slippage)
        
        amount = executed_price * order.volume
        commission = amount * self.commission_rate
        
        # 印花税（卖出时）
        stamp_tax = amount * 0.001 if order.trade_type == "sell" else 0
        
        # 生成成交号
        trade_no = f"TRD{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"
        
        trade = Trade(
            trade_no=trade_no,
            order_no=order.order_no,
            stock_code=order.stock_code,
            trade_type=order.trade_type,
            volume=order.volume,
            price=executed_price,
            amount=amount,
            commission=commission + stamp_tax,
            trade_time=datetime.now(),
        )
        
        # 保存成交记录
        try:
            total_cost = trade.amount + trade.commission
            db.execute("""
                INSERT INTO trade_fills
                (fill_no, order_id, account_id, stock_code, trade_type, fill_volume, 
                 fill_price, fill_amount, commission, total_cost, fill_time)
                VALUES (:fill_no, (SELECT id FROM trade_orders WHERE order_no = :order_no), 
                        :account_id, :code, :trade_type, :volume,
                        :price, :amount, :commission, :total_cost, CURRENT_TIMESTAMP)
            """, {
                "fill_no": trade.trade_no,
                "order_no": trade.order_no,
                "account_id": self.account_id,
                "code": trade.stock_code,
                "trade_type": trade.trade_type,
                "volume": trade.volume,
                "price": trade.price,
                "amount": trade.amount,
                "commission": trade.commission,
                "total_cost": total_cost,
            })
            
            # 更新订单状态
            db.execute("""
                UPDATE trade_orders 
                SET status = 'filled', filled_volume = :volume, filled_amount = :amount,
                    commission = :commission, filled_time = CURRENT_TIMESTAMP
                WHERE order_no = :order_no
            """, {
                "volume": order.volume,
                "amount": amount,
                "commission": commission + stamp_tax,
                "order_no": order.order_no,
            })
            
            # 更新持仓
            self._update_position(order, trade)
            
            logger.info(f"订单成交: {trade_no} {order.stock_code} {order.volume}股 @ {executed_price:.2f}")
            return trade
            
        except Exception as e:
            logger.error(f"保存成交记录失败: {e}")
            return None
    
    def _update_position(self, order: Order, trade: Trade) -> None:
        """更新持仓"""
        try:
            if order.trade_type == "buy":
                # 买入 - 增加持仓
                db.execute("""
                    INSERT INTO position_details 
                    (account_id, stock_code, stock_name, total_volume, available_volume, 
                     avg_cost, total_cost, open_date)
                    VALUES (:account_id, :code, :name, :volume, :volume, :price, :cost, CURRENT_DATE)
                    ON CONFLICT (account_id, stock_code) DO UPDATE SET
                        total_volume = position_details.total_volume + EXCLUDED.total_volume,
                        available_volume = position_details.available_volume + EXCLUDED.available_volume,
                        total_cost = position_details.total_cost + EXCLUDED.total_cost,
                        avg_cost = (position_details.total_cost + EXCLUDED.total_cost) / 
                                   (position_details.total_volume + EXCLUDED.total_volume),
                        updated_at = CURRENT_TIMESTAMP
                """, {
                    "account_id": self.account_id,
                    "code": order.stock_code,
                    "name": order.stock_name,
                    "volume": order.volume,
                    "price": trade.price,
                    "cost": trade.amount + trade.commission,
                })
            else:
                # 卖出 - 减少持仓
                db.execute("""
                    UPDATE position_details 
                    SET total_volume = total_volume - :volume,
                        available_volume = available_volume - :volume,
                        total_cost = avg_cost * (total_volume - :volume),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE account_id = :account_id AND stock_code = :code
                """, {
                    "volume": order.volume,
                    "account_id": self.account_id,
                    "code": order.stock_code,
                })
                
                # 如果持仓为0，标记为已清仓
                db.execute("""
                    UPDATE position_details 
                    SET is_closed = TRUE
                    WHERE account_id = :account_id AND stock_code = :code AND total_volume = 0
                """, {
                    "account_id": self.account_id,
                    "code": order.stock_code,
                })
        except Exception as e:
            logger.error(f"更新持仓失败: {e}")
    
    def _get_current_price(self, stock_code: str) -> float:
        """获取当前价格（模拟）"""
        # TODO: 从行情数据获取实时价格
        return 10.0
    
    def get_orders(self, status: Optional[str] = None) -> List[dict]:
        """获取订单列表"""
        try:
            if status:
                results = db.fetch_all(
                    """SELECT order_no, stock_code, trade_type, order_volume, order_price, 
                              filled_volume, status, created_at
                       FROM trade_orders 
                       WHERE account_id = :account_id AND status = :status
                       ORDER BY created_at DESC""",
                    {"account_id": self.account_id, "status": status}
                )
            else:
                results = db.fetch_all(
                    """SELECT order_no, stock_code, trade_type, order_volume, order_price,
                              filled_volume, status, created_at
                       FROM trade_orders 
                       WHERE account_id = :account_id
                       ORDER BY created_at DESC LIMIT 100""",
                    {"account_id": self.account_id}
                )
            
            return [
                {
                    "order_no": row[0],
                    "stock_code": row[1],
                    "trade_type": row[2],
                    "order_volume": row[3],
                    "order_price": row[4],
                    "filled_volume": row[5],
                    "status": row[6],
                    "created_at": str(row[7]),
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"获取订单列表失败: {e}")
            return []
    
    def get_positions(self) -> List[dict]:
        """获取持仓列表"""
        try:
            results = db.fetch_all(
                """SELECT stock_code, stock_name, total_volume, available_volume, 
                          avg_cost, current_price, market_value, floating_pnl
                   FROM position_details 
                   WHERE account_id = :account_id AND total_volume > 0
                   ORDER BY market_value DESC""",
                {"account_id": self.account_id}
            )
            
            return [
                {
                    "stock_code": row[0],
                    "stock_name": row[1],
                    "total_volume": row[2],
                    "available_volume": row[3],
                    "avg_cost": row[4],
                    "current_price": row[5],
                    "market_value": row[6],
                    "floating_pnl": row[7],
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"获取持仓列表失败: {e}")
            return []


# 全局交易执行器实例
trading_executor = TradingExecutor()
