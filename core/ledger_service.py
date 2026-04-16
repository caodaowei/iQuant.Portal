"""投资账本服务

提供投资组合分析、盈亏统计、资产历史等功能
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
from decimal import Decimal

from loguru import logger
from sqlalchemy import text, func

from core.database_router import get_db_router


class LedgerService:
    """投资账本服务类"""
    
    def __init__(self):
        self.router = get_db_router()
    
    def get_accounts(self) -> List[Dict]:
        """获取所有交易账户列表"""
        with self.router.read_session() as session:
            query = text("""
                SELECT 
                    id,
                    account_code,
                    account_name,
                    account_type,
                    total_capital,
                    available_cash,
                    market_value,
                    total_pnl,
                    status,
                    is_default,
                    created_at
                FROM trading_accounts
                WHERE status = 'active'
                ORDER BY is_default DESC, created_at DESC
            """)
            
            result = session.execute(query)
            accounts = []
            for row in result.fetchall():
                accounts.append({
                    "id": row[0],
                    "account_code": row[1],
                    "account_name": row[2],
                    "account_type": row[3],
                    "total_capital": float(row[4]) if row[4] else 0,
                    "available_cash": float(row[5]) if row[5] else 0,
                    "market_value": float(row[6]) if row[6] else 0,
                    "total_pnl": float(row[7]) if row[7] else 0,
                    "status": row[8],
                    "is_default": row[9],
                    "created_at": row[10].isoformat() if row[10] else None,
                })
            
            return accounts
    
    def get_account_summary(self, account_id: int) -> Dict:
        """获取账户概览信息"""
        with self.router.read_session() as session:
            query = text("""
                SELECT 
                    id,
                    account_name,
                    account_type,
                    total_capital,
                    available_cash,
                    market_value,
                    total_pnl,
                    frozen_cash
                FROM trading_accounts
                WHERE id = :account_id
            """)
            
            result = session.execute(query, {"account_id": account_id})
            row = result.fetchone()
            
            if not row:
                raise ValueError(f"账户 {account_id} 不存在")
            
            return {
                "id": row[0],
                "account_name": row[1],
                "account_type": row[2],
                "total_capital": float(row[3]) if row[3] else 0,
                "available_cash": float(row[4]) if row[4] else 0,
                "market_value": float(row[5]) if row[5] else 0,
                "total_pnl": float(row[6]) if row[6] else 0,
                "frozen_cash": float(row[7]) if row[7] else 0,
            }
    
    def create_account(self, account_name: str, account_type: str, initial_capital: float, is_default: bool = False) -> Dict:
        """创建新交易账户"""
        with self.router.write_session() as session:
            # 如果设置为默认账户，先将其他账户设为非默认
            if is_default:
                session.execute(
                    text("UPDATE trading_accounts SET is_default = FALSE WHERE is_default = TRUE")
                )
            
            # 生成账户编码
            import uuid
            account_code = f"ACC-{uuid.uuid4().hex[:8].upper()}"
            
            # 插入新账户
            query = text("""
                INSERT INTO trading_accounts (
                    account_code,
                    account_name,
                    account_type,
                    total_capital,
                    available_cash,
                    market_value,
                    total_pnl,
                    status,
                    is_default,
                    created_at
                ) VALUES (
                    :account_code,
                    :account_name,
                    :account_type,
                    :initial_capital,
                    :initial_capital,
                    0,
                    0,
                    'active',
                    :is_default,
                    CURRENT_TIMESTAMP
                ) RETURNING id, account_code, account_name, account_type, total_capital, available_cash, market_value, total_pnl, status, is_default, created_at
            """)
            
            result = session.execute(query, {
                "account_code": account_code,
                "account_name": account_name,
                "account_type": account_type,
                "initial_capital": initial_capital,
                "is_default": is_default,
            })
            
            row = result.fetchone()
            session.commit()
            
            return {
                "id": row[0],
                "account_code": row[1],
                "account_name": row[2],
                "account_type": row[3],
                "total_capital": float(row[4]) if row[4] else 0,
                "available_cash": float(row[5]) if row[5] else 0,
                "market_value": float(row[6]) if row[6] else 0,
                "total_pnl": float(row[7]) if row[7] else 0,
                "status": row[8],
                "is_default": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
            }
    
    def update_account(self, account_id: int, account_name: Optional[str] = None, account_type: Optional[str] = None, is_default: Optional[bool] = None) -> Dict:
        """更新账户信息"""
        with self.router.write_session() as session:
            # 检查账户是否存在
            check_query = text("SELECT id FROM trading_accounts WHERE id = :account_id")
            result = session.execute(check_query, {"account_id": account_id})
            if not result.fetchone():
                raise ValueError(f"账户 {account_id} 不存在")
            
            # 构建更新语句
            update_fields = []
            params = {"account_id": account_id}
            
            if account_name:
                update_fields.append("account_name = :account_name")
                params["account_name"] = account_name
            
            if account_type:
                update_fields.append("account_type = :account_type")
                params["account_type"] = account_type
            
            if is_default is not None:
                # 如果设置为默认账户，先将其他账户设为非默认
                if is_default:
                    session.execute(
                        text("UPDATE trading_accounts SET is_default = FALSE WHERE is_default = TRUE AND id != :account_id"),
                        {"account_id": account_id}
                    )
                update_fields.append("is_default = :is_default")
                params["is_default"] = is_default
            
            if update_fields:
                update_query = text(f"""
                    UPDATE trading_accounts 
                    SET {', '.join(update_fields)}
                    WHERE id = :account_id
                    RETURNING id, account_code, account_name, account_type, total_capital, available_cash, market_value, total_pnl, status, is_default, created_at
                """)
                
                result = session.execute(update_query, params)
                row = result.fetchone()
                session.commit()
                
                return {
                    "id": row[0],
                    "account_code": row[1],
                    "account_name": row[2],
                    "account_type": row[3],
                    "total_capital": float(row[4]) if row[4] else 0,
                    "available_cash": float(row[5]) if row[5] else 0,
                    "market_value": float(row[6]) if row[6] else 0,
                    "total_pnl": float(row[7]) if row[7] else 0,
                    "status": row[8],
                    "is_default": row[9],
                    "created_at": row[10].isoformat() if row[10] else None,
                }
            else:
                # 无更新内容，返回当前账户信息
                return self.get_account_summary(account_id)
    
    def delete_account(self, account_id: int) -> None:
        """删除交易账户"""
        with self.router.write_session() as session:
            # 检查账户是否存在
            check_query = text("SELECT id FROM trading_accounts WHERE id = :account_id")
            result = session.execute(check_query, {"account_id": account_id})
            if not result.fetchone():
                raise ValueError(f"账户 {account_id} 不存在")
            
            # 检查账户是否有持仓
            position_query = text("SELECT COUNT(*) FROM position_details WHERE account_id = :account_id AND is_closed = FALSE")
            position_count = session.execute(position_query, {"account_id": account_id}).scalar()
            if position_count > 0:
                raise ValueError("账户存在持仓，无法删除")
            
            # 检查账户是否有交易记录
            trade_query = text("SELECT COUNT(*) FROM trade_fills WHERE account_id = :account_id")
            trade_count = session.execute(trade_query, {"account_id": account_id}).scalar()
            if trade_count > 0:
                raise ValueError("账户存在交易记录，无法删除")
            
            # 删除账户
            delete_query = text("DELETE FROM trading_accounts WHERE id = :account_id")
            session.execute(delete_query, {"account_id": account_id})
            session.commit()
    
    def get_positions_with_quotes(self, account_id: int) -> List[Dict]:
        """获取持仓列表（含实时行情和盈亏）"""
        from core.data_fetcher import data_fetcher
        
        # 检查账户是否存在
        try:
            self.get_account_summary(account_id)
        except ValueError:
            return []
        
        try:
            with self.router.read_session() as session:
                query = text("""
                    SELECT 
                        pd.stock_code,
                        pd.stock_name,
                        pd.total_volume,
                        pd.available_volume,
                        pd.avg_cost,
                        pd.total_cost,
                        pd.current_price,
                        pd.market_value,
                        pd.floating_pnl,
                        pd.floating_pnl_rate,
                        pd.open_date,
                        pd.last_trade_date
                    FROM position_details pd
                    WHERE pd.account_id = :account_id
                      AND pd.is_closed = FALSE
                      AND pd.total_volume > 0
                    ORDER BY pd.market_value DESC NULLS LAST
                """)
                
                result = session.execute(query, {"account_id": account_id})
                positions = []
                
                for row in result.fetchall():
                    # 尝试获取实时价格
                    current_price = float(row[6]) if row[6] else None
                    
                    # 如果数据库价格为空或需要更新，尝试从数据源获取
                    if not current_price:
                        try:
                            quote = data_fetcher.get_realtime_quote(row[0])
                            current_price = quote.get("current_price")
                        except Exception:
                            current_price = float(row[4]) if row[4] else 0  # 使用成本价作为fallback
                    
                    # 重新计算市值和盈亏
                    total_volume = row[2]
                    avg_cost = float(row[4]) if row[4] else 0
                    market_value = current_price * total_volume if current_price else 0
                    floating_pnl = market_value - (avg_cost * total_volume)
                    floating_pnl_rate = (floating_pnl / (avg_cost * total_volume) * 100) if avg_cost > 0 else 0
                    
                    positions.append({
                        "stock_code": row[0],
                        "stock_name": row[1] or row[0],
                        "total_volume": total_volume,
                        "available_volume": row[3],
                        "avg_cost": avg_cost,
                        "total_cost": float(row[5]) if row[5] else 0,
                        "current_price": current_price,
                        "market_value": market_value,
                        "floating_pnl": floating_pnl,
                        "floating_pnl_rate": round(floating_pnl_rate, 2),
                        "open_date": row[10].isoformat() if row[10] else None,
                        "last_trade_date": row[11].isoformat() if row[11] else None,
                    })
                
                return positions
        except Exception as e:
            # 记录错误并返回空列表
            import logging
            logging.error(f"获取持仓列表失败: {e}")
            return []
    
    def get_trade_history(
        self, 
        account_id: int, 
        limit: int = 100,
        offset: int = 0,
        stock_code: Optional[str] = None,
        trade_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict:
        """获取成交历史记录（支持分页和筛选）"""
        # 检查账户是否存在
        try:
            self.get_account_summary(account_id)
        except ValueError:
            return {
                "trades": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            }
        
        try:
            with self.router.read_session() as session:
                # 构建查询条件
                conditions = ["tf.account_id = :account_id"]
                params = {"account_id": account_id, "limit": limit, "offset": offset}
                
                if stock_code:
                    conditions.append("tf.stock_code = :stock_code")
                    params["stock_code"] = stock_code
                
                if trade_type:
                    conditions.append("tf.trade_type = :trade_type")
                    params["trade_type"] = trade_type
                
                if start_date:
                    conditions.append("tf.fill_time >= :start_date")
                    params["start_date"] = start_date
                
                if end_date:
                    conditions.append("tf.fill_time <= :end_date")
                    params["end_date"] = end_date + " 23:59:59"
                
                where_clause = " AND ".join(conditions)
                
                # 查询总数
                count_query = text(f"""
                    SELECT COUNT(*) FROM trade_fills tf WHERE {where_clause}
                """)
                total_count = session.execute(count_query, params).scalar()
                
                # 查询成交记录
                query = text(f"""
                    SELECT 
                        tf.fill_no,
                        tf.stock_code,
                        tf.trade_type,
                        tf.fill_volume,
                        tf.fill_price,
                        tf.fill_amount,
                        tf.commission,
                        tf.stamp_tax,
                        tf.transfer_fee,
                        tf.other_fees,
                        tf.total_cost,
                        tf.fill_time,
                        tro.order_no,
                        tro.strategy_code
                    FROM trade_fills tf
                    LEFT JOIN trade_orders tro ON tf.order_id = tro.id
                    WHERE {where_clause}
                    ORDER BY tf.fill_time DESC
                    LIMIT :limit OFFSET :offset
                """)
                
                result = session.execute(query, params)
                trades = []
                
                for row in result.fetchall():
                    trades.append({
                        "fill_no": row[0],
                        "stock_code": row[1],
                        "trade_type": row[2],
                        "fill_volume": row[3],
                        "fill_price": float(row[4]) if row[4] else 0,
                        "fill_amount": float(row[5]) if row[5] else 0,
                        "commission": float(row[6]) if row[6] else 0,
                        "stamp_tax": float(row[7]) if row[7] else 0,
                        "transfer_fee": float(row[8]) if row[8] else 0,
                        "other_fees": float(row[9]) if row[9] else 0,
                        "total_cost": float(row[10]) if row[10] else 0,
                        "fill_time": row[11].isoformat() if row[11] else None,
                        "order_no": row[12],
                        "strategy_code": row[13],
                    })
                
                return {
                    "trades": trades,
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                }
        except Exception as e:
            # 记录错误并返回空结果
            import logging
            logging.error(f"获取交易历史失败: {e}")
            return {
                "trades": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            }
    
    def get_asset_history(self, account_id: int, days: int = 90) -> List[Dict]:
        """获取资产历史数据（用于绘制净值曲线）"""
        # 检查账户是否存在
        try:
            self.get_account_summary(account_id)
        except ValueError:
            return []
        
        try:
            with self.router.read_session() as session:
                # 从 capital_flows 表聚合每日资产快照
                # 如果没有足够的历史数据，则基于当前持仓和交易记录推算
                query = text("""
                    WITH daily_snapshots AS (
                        SELECT 
                            DATE(cf.trade_date) as snapshot_date,
                            MAX(cf.balance) as cash_balance,
                            MAX(cf.created_at) as last_update
                        FROM capital_flows cf
                        WHERE cf.account_id = :account_id
                          AND cf.trade_date >= CURRENT_DATE - INTERVAL ':days days'
                        GROUP BY DATE(cf.trade_date)
                    )
                    SELECT 
                        ds.snapshot_date,
                        ds.cash_balance,
                        COALESCE(
                            (SELECT SUM(pd.market_value) 
                             FROM position_details pd 
                             WHERE pd.account_id = :account_id 
                               AND pd.is_closed = FALSE
                               AND DATE(pd.updated_at) <= ds.snapshot_date),
                            0
                        ) as market_value,
                        ds.cash_balance + COALESCE(
                            (SELECT SUM(pd.market_value) 
                             FROM position_details pd 
                             WHERE pd.account_id = :account_id 
                               AND pd.is_closed = FALSE
                               AND DATE(pd.updated_at) <= ds.snapshot_date),
                            0
                        ) as total_asset
                    FROM daily_snapshots ds
                    ORDER BY ds.snapshot_date ASC
                """)
                
                result = session.execute(query, {"account_id": account_id, "days": days})
                history = []
                
                initial_capital = None
                for row in result.fetchall():
                    total_asset = float(row[3]) if row[3] else 0
                    
                    if initial_capital is None:
                        initial_capital = total_asset if total_asset > 0 else 1000000
                    
                    nav = total_asset / initial_capital if initial_capital > 0 else 1.0
                    daily_return = 0  # 需要前一天数据才能计算
                    
                    history.append({
                        "date": row[0].isoformat() if row[0] else None,
                        "cash_balance": float(row[1]) if row[1] else 0,
                        "market_value": float(row[2]) if row[2] else 0,
                        "total_asset": total_asset,
                        "nav": round(nav, 4),
                        "daily_return": daily_return,
                    })
                
                # 如果没有历史数据，生成模拟数据
                if not history:
                    logger.warning(f"账户 {account_id} 没有资产历史数据，生成模拟数据")
                    history = self._generate_mock_asset_history(account_id, days)
                
                return history
        except Exception as e:
            # 记录错误并返回模拟数据
            import logging
            logging.error(f"获取资产历史失败: {e}")
            logger.warning(f"获取资产历史失败，生成模拟数据: {e}")
            return self._generate_mock_asset_history(account_id, days)
    
    def _generate_mock_asset_history(self, account_id: int, days: int) -> List[Dict]:
        """生成模拟的资产历史数据（用于演示）"""
        from core.data_generator import create_sample_market_data
        
        # 获取账户当前状态
        summary = self.get_account_summary(account_id)
        current_asset = summary["total_capital"]
        
        # 生成模拟净值曲线
        history = []
        base_value = current_asset * 0.9  # 假设起始值为当前的90%
        
        for i in range(days):
            d = datetime.now().date() - timedelta(days=days-i-1)
            
            # 模拟波动（随机游走）
            import random
            daily_change = random.uniform(-0.03, 0.03)  # ±3% 日波动
            
            if i == 0:
                value = base_value
            else:
                prev_value = history[-1]["total_asset"]
                value = prev_value * (1 + daily_change)
            
            nav = value / base_value
            
            history.append({
                "date": d.isoformat(),
                "cash_balance": value * 0.3,  # 假设30%现金
                "market_value": value * 0.7,  # 70%持仓
                "total_asset": round(value, 2),
                "nav": round(nav, 4),
                "daily_return": round(daily_change * 100, 2),
            })
        
        return history
    
    def get_pnl_statistics(self, account_id: int) -> Dict:
        """获取盈亏统计数据"""
        # 检查账户是否存在
        try:
            self.get_account_summary(account_id)
        except ValueError:
            return {
                "total_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "realized_pnl": 0,
                "win_rate": 0,
                "avg_pnl_per_trade": 0,
                "max_single_profit": 0,
                "max_single_loss": 0,
                "total_fees": 0,
                "avg_holding_days": 0,
            }
        
        try:
            with self.router.read_session() as session:
                # 统计卖出交易的盈亏
                query = text("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN tf.trade_type = 'sell' THEN 1 ELSE 0 END) as sell_trades,
                        SUM(CASE WHEN tf.trade_type = 'buy' THEN 1 ELSE 0 END) as buy_trades,
                        SUM(CASE WHEN tf.trade_type = 'sell' THEN tf.fill_amount - tf.total_cost ELSE 0 END) as realized_pnl,
                        AVG(CASE WHEN tf.trade_type = 'sell' THEN tf.fill_amount - tf.total_cost ELSE NULL END) as avg_pnl_per_trade,
                        MAX(CASE WHEN tf.trade_type = 'sell' THEN tf.fill_amount - tf.total_cost ELSE NULL END) as max_single_profit,
                        MIN(CASE WHEN tf.trade_type = 'sell' THEN tf.fill_amount - tf.total_cost ELSE NULL END) as max_single_loss,
                        SUM(tf.commission + tf.stamp_tax + tf.transfer_fee + tf.other_fees) as total_fees
                    FROM trade_fills tf
                    WHERE tf.account_id = :account_id
                """)
                
                result = session.execute(query, {"account_id": account_id})
                row = result.fetchone()
                
                if not row or row[0] == 0:
                    return {
                        "total_trades": 0,
                        "buy_trades": 0,
                        "sell_trades": 0,
                        "realized_pnl": 0,
                        "win_rate": 0,
                        "avg_pnl_per_trade": 0,
                        "max_single_profit": 0,
                        "max_single_loss": 0,
                        "total_fees": 0,
                        "avg_holding_days": 0,
                    }
                
                # 计算胜率（盈利交易数 / 总卖出交易数）
                win_rate_query = text("""
                    SELECT 
                        COUNT(CASE WHEN tf.fill_amount - tf.total_cost > 0 THEN 1 END) * 100.0 / 
                        NULLIF(COUNT(*), 0) as win_rate
                    FROM trade_fills tf
                    WHERE tf.account_id = :account_id AND tf.trade_type = 'sell'
                """)
                
                win_rate_row = session.execute(win_rate_query, {"account_id": account_id}).fetchone()
                win_rate = float(win_rate_row[0]) if win_rate_row and win_rate_row[0] else 0
                
                # 计算平均持仓天数（简化版）
                avg_holding_days = 5  # 默认值，实际需要从订单时间计算
                
                return {
                    "total_trades": row[0],
                    "buy_trades": row[2],
                    "sell_trades": row[1],
                    "realized_pnl": float(row[3]) if row[3] else 0,
                    "win_rate": round(win_rate, 2),
                    "avg_pnl_per_trade": float(row[4]) if row[4] else 0,
                    "max_single_profit": float(row[5]) if row[5] else 0,
                    "max_single_loss": float(row[6]) if row[6] else 0,
                    "total_fees": float(row[7]) if row[7] else 0,
                    "avg_holding_days": avg_holding_days,
                }
        except Exception as e:
            # 记录错误并返回默认值
            import logging
            logging.error(f"获取盈亏统计失败: {e}")
            return {
                "total_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "realized_pnl": 0,
                "win_rate": 0,
                "avg_pnl_per_trade": 0,
                "max_single_profit": 0,
                "max_single_loss": 0,
                "total_fees": 0,
                "avg_holding_days": 0,
            }
    
    def get_pnl_by_stock(self, account_id: int) -> List[Dict]:
        """按股票统计盈亏"""
        # 检查账户是否存在
        try:
            self.get_account_summary(account_id)
        except ValueError:
            return []
        
        try:
            with self.router.read_session() as session:
                query = text("""
                    SELECT 
                        tf.stock_code,
                        MAX(pd.stock_name) as stock_name,
                        SUM(CASE WHEN tf.trade_type = 'buy' THEN tf.fill_volume ELSE 0 END) as total_buy_volume,
                        SUM(CASE WHEN tf.trade_type = 'sell' THEN tf.fill_volume ELSE 0 END) as total_sell_volume,
                        SUM(CASE WHEN tf.trade_type = 'buy' THEN tf.fill_amount ELSE 0 END) as total_buy_amount,
                        SUM(CASE WHEN tf.trade_type = 'sell' THEN tf.fill_amount ELSE 0 END) as total_sell_amount,
                        SUM(tf.commission + tf.stamp_tax + tf.transfer_fee + tf.other_fees) as total_fees,
                        SUM(CASE WHEN tf.trade_type = 'sell' THEN tf.fill_amount - tf.total_cost ELSE 0 END) as realized_pnl
                    FROM trade_fills tf
                    LEFT JOIN position_details pd ON tf.account_id = pd.account_id AND tf.stock_code = pd.stock_code
                    WHERE tf.account_id = :account_id
                    GROUP BY tf.stock_code
                    HAVING SUM(CASE WHEN tf.trade_type = 'sell' THEN 1 ELSE 0 END) > 0
                    ORDER BY realized_pnl DESC NULLS LAST
                """)
                
                result = session.execute(query, {"account_id": account_id})
                pnl_by_stock = []
                
                for row in result.fetchall():
                    pnl_by_stock.append({
                        "stock_code": row[0],
                        "stock_name": row[1] or row[0],
                        "total_buy_volume": row[2],
                        "total_sell_volume": row[3],
                        "total_buy_amount": float(row[4]) if row[4] else 0,
                        "total_sell_amount": float(row[5]) if row[5] else 0,
                        "total_fees": float(row[6]) if row[6] else 0,
                        "realized_pnl": float(row[7]) if row[7] else 0,
                    })
                
                return pnl_by_stock
        except Exception as e:
            # 记录错误并返回空列表
            import logging
            logging.error(f"获取股票盈亏统计失败: {e}")
            return []
    
    def get_daily_pnl(self, account_id: int, days: int = 30) -> List[Dict]:
        """获取每日盈亏明细"""
        # 检查账户是否存在
        try:
            self.get_account_summary(account_id)
        except ValueError:
            return []
        
        try:
            with self.router.read_session() as session:
                query = text("""
                    SELECT 
                        DATE(tf.fill_time) as trade_date,
                        SUM(CASE WHEN tf.trade_type = 'sell' THEN tf.fill_amount - tf.total_cost ELSE 0 END) as daily_pnl,
                        COUNT(CASE WHEN tf.trade_type = 'sell' THEN 1 END) as sell_count,
                        SUM(tf.commission + tf.stamp_tax + tf.transfer_fee + tf.other_fees) as daily_fees
                    FROM trade_fills tf
                    WHERE tf.account_id = :account_id
                      AND tf.fill_time >= CURRENT_DATE - INTERVAL ':days days'
                    GROUP BY DATE(tf.fill_time)
                    ORDER BY trade_date ASC
                """)
                
                result = session.execute(query, {"account_id": account_id, "days": days})
                daily_pnl = []
                
                for row in result.fetchall():
                    daily_pnl.append({
                        "date": row[0].isoformat() if row[0] else None,
                        "pnl": float(row[1]) if row[1] else 0,
                        "sell_count": row[2],
                        "fees": float(row[3]) if row[3] else 0,
                    })
                
                return daily_pnl
        except Exception as e:
            # 记录错误并返回空列表
            import logging
            logging.error(f"获取每日盈亏失败: {e}")
            return []
    
    def get_capital_flows(
        self, 
        account_id: int, 
        limit: int = 50,
        flow_type: Optional[str] = None,
    ) -> List[Dict]:
        """获取资金流水记录"""
        # 检查账户是否存在
        try:
            self.get_account_summary(account_id)
        except ValueError:
            return []
        
        with self.router.read_session() as session:
            conditions = ["cf.account_id = :account_id"]
            params = {"account_id": account_id, "limit": limit}
            
            if flow_type:
                conditions.append("cf.flow_type = :flow_type")
                params["flow_type"] = flow_type
            
            where_clause = " AND ".join(conditions)
            
            query = text(f"""
                SELECT 
                    cf.id,
                    cf.flow_type,
                    cf.trade_date,
                    cf.amount,
                    cf.balance,
                    cf.stock_code,
                    cf.description,
                    cf.created_at
                FROM capital_flows cf
                WHERE {where_clause}
                ORDER BY cf.trade_date DESC, cf.created_at DESC
                LIMIT :limit
            """)
            
            result = session.execute(query, params)
            flows = []
            
            for row in result.fetchall():
                flows.append({
                    "id": row[0],
                    "flow_type": row[1],
                    "trade_date": row[2].isoformat() if row[2] else None,
                    "amount": float(row[3]) if row[3] else 0,
                    "balance": float(row[4]) if row[4] else 0,
                    "stock_code": row[5],
                    "description": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                })
            
            return flows


# 全局实例
ledger_service = LedgerService()


def get_ledger_service() -> LedgerService:
    """获取账本服务单例"""
    return ledger_service
