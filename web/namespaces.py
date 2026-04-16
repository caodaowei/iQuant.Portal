"""API命名空间定义"""
from loguru import logger
from flask import jsonify
from datetime import datetime
from flask_restx import Namespace, Resource, fields
from flask import request

# 创建命名空间
status_ns = Namespace('status', description='系统状态相关操作')
database_ns = Namespace('database', description='数据库相关操作')
strategies_ns = Namespace('strategies', description='策略相关操作')
backtest_ns = Namespace('backtest', description='回测相关操作')
trading_ns = Namespace('trading', description='交易相关操作')
risk_ns = Namespace('risk', description='风控相关操作')
data_ns = Namespace('data', description='数据同步相关操作')
diagnosis_ns = Namespace('diagnosis', description='AI诊断相关操作')
stock_selection_ns = Namespace('stock-selection', description='选股策略相关操作')

# 响应模型
status_model = status_ns.model('Status', {
    'status': fields.String(description='系统状态'),
    'database': fields.String(description='数据库状态'),
    'redis': fields.String(description='Redis状态'),
    'version': fields.String(description='系统版本'),
    'timestamp': fields.String(description='时间戳')
})

strategy_model = strategies_ns.model('Strategy', {
    'code': fields.String(description='策略代码'),
    'name': fields.String(description='策略名称'),
    'type': fields.String(description='策略类型'),
    'active': fields.Boolean(description='是否激活')
})

backtest_params_model = backtest_ns.model('BacktestParams', {
    'strategy': fields.String(description='策略代码'),
    'days': fields.Integer(description='回测天数'),
    'initial_capital': fields.Integer(description='初始资金')
})

backtest_result_model = backtest_ns.model('BacktestResult', {
    'strategy': fields.String(description='策略代码'),
    'initial_capital': fields.Integer(description='初始资金'),
    'final_capital': fields.Float(description='最终资金'),
    'total_return': fields.Float(description='总收益率'),
    'annualized_return': fields.Float(description='年化收益率'),
    'max_drawdown': fields.Float(description='最大回撤'),
    'sharpe_ratio': fields.Float(description='夏普比率'),
    'total_trades': fields.Integer(description='总交易次数'),
    'start_date': fields.String(description='开始日期'),
    'end_date': fields.String(description='结束日期'),
    'chart': fields.Raw(description='图表数据')
})

order_model = trading_ns.model('Order', {
    'stock_code': fields.String(description='股票代码'),
    'trade_type': fields.String(description='交易类型'),
    'volume': fields.Integer(description='交易数量'),
    'price': fields.Float(description='交易价格')
})

# 状态相关资源


@status_ns.route('/status')
class StatusResource(Resource):
    @status_ns.marshal_with(status_model)
    def get(self):
        """获取系统状态"""
        from core.cache import cache_manager
        from core.database import db

        db_status = db.health_check()
        redis_status = cache_manager.health_check()

        return {
            "status": "ok" if db_status else "error",
            "database": "connected" if db_status else "disconnected",
            "redis": "connected" if redis_status else "disconnected",
            "version": "0.1.0",
            "timestamp": datetime.now().isoformat(),
        }

# 缓存相关资源


@status_ns.route('/cache/stats')
class CacheStatsResource(Resource):
    def get(self):
        """获取缓存统计信息"""
        from core.cache import cache_manager
        stats = cache_manager.get_stats()
        return stats


@status_ns.route('/cache/clear')
class CacheClearResource(Resource):
    def post(self):
        """清除缓存"""
        from core.cache import cache_manager
        data = request.get_json() or {}
        namespace = data.get("namespace")

        if namespace:
            count = cache_manager.clear_namespace(namespace)
            return {"message": f"已清除 {namespace} 命名空间，删除 {count} 个键"}
        else:
            # 清除所有命名空间
            namespaces = ["daily_data", "stock_list", "index_data",
                          "ai_diagnosis", "backtest_result", "strategy_signal"]
            total_count = 0
            for ns in namespaces:
                count = cache_manager.clear_namespace(ns)
                total_count += count

            return {"message": f"已清除所有缓存，共删除 {total_count} 个键"}

# 策略相关资源


@strategies_ns.route('')
class StrategiesResource(Resource):
    def get(self):
        """获取策略列表"""
        from core.strategy_manager import StrategyManager
        strategy_manager = StrategyManager()
        strategies = strategy_manager.list_strategies()
        return {
            "strategies": strategies,
            "count": len(strategies),
        }


@strategies_ns.route('/<code>/run')
class RunStrategyResource(Resource):
    def post(self, code):
        """运行策略"""
        try:
            import pandas as pd

            # 获取参数
            data = request.get_json() or {}
            days = data.get("days", 200)

            # 生成示例数据
            from tests.test_strategies import create_sample_data
            market_data = create_sample_data(days)

            # 运行策略
            from core.strategy_manager import StrategyManager
            strategy_manager = StrategyManager()
            strategy = strategy_manager.strategies.get(code)
            if not strategy:
                return {"error": f"策略不存在: {code}"}, 404

            signals = strategy.run(market_data)
            latest = strategy.get_latest_signal(market_data)

            return {
                "strategy": code,
                "signal_count": len(signals),
                "latest_signal": {
                    "date": str(latest.trade_date) if latest else None,
                    "type": latest.signal_type if latest else None,
                    "strength": latest.strength if latest else None,
                    "reason": latest.reason if latest else None,
                },
            }

        except Exception as e:
            logger.error(f"运行策略失败: {e}")
            return {"error": str(e)}, 500

# 回测相关资源


@backtest_ns.route('/backtest')
class BacktestResource(Resource):
    @backtest_ns.expect(backtest_params_model)
    def post(self):
        """运行回测"""
        try:
            import pandas as pd

            # 获取参数
            data = request.get_json() or {}
            strategy_code = data.get("strategy", "MA_TREND")
            days = data.get("days", 300)
            initial_capital = data.get("initial_capital", 1000000)

            # 生成缓存键
            cache_key = f"{strategy_code}_{days}_{initial_capital}"

            # 尝试从缓存获取
            from core.cache import cache_manager
            cached_result = cache_manager.get("backtest_result", cache_key)
            if cached_result is not None:
                logger.info(f"回测结果缓存命中: {cache_key}")
                return cached_result

            # 生成示例数据
            from core.data_generator import create_sample_market_data
            market_data = create_sample_market_data(days)

            # 创建策略（使用注册表）
            from strategies.registry import get_strategy_or_default
            strategy_class = get_strategy_or_default(strategy_code)
            strategy = strategy_class()

            # 运行回测
            from core.backtest_engine import BacktestEngine
            engine = BacktestEngine(
                initial_capital=initial_capital,
                commission_rate=0.00025,
                slippage=0.001,
            )
            engine.set_strategy(strategy)
            engine.set_market_data(market_data)

            results = engine.run()

            # 生成图表
            from core.visualization import create_backtest_chart
            chart_json = create_backtest_chart(
                nav_data=results.get("nav_data", []),
                trades=results.get("trades", []),
            )

            response_data = {
                "strategy": strategy_code,
                "initial_capital": results["initial_capital"],
                "final_capital": results["final_capital"],
                "total_return": results["total_return"],
                "annualized_return": results["annualized_return"],
                "max_drawdown": results["max_drawdown"],
                "sharpe_ratio": results["sharpe_ratio"],
                "total_trades": results["total_trades"],
                "start_date": str(results["start_date"]),
                "end_date": str(results["end_date"]),
                "chart": chart_json,
            }

            # 写入缓存（7天过期）
            cache_manager.set("backtest_result", cache_key,
                              response_data, ttl=604800)
            logger.info(f"回测结果已缓存: {cache_key}")

            return response_data

        except Exception as e:
            logger.error(f"回测失败: {e}")
            return {"error": str(e)}, 500

# 数据库相关资源


@database_ns.route('/tables')
class DatabaseTablesResource(Resource):
    def get(self):
        """获取数据库表列表"""
        try:
            from core.database import db
            result = db.fetch_all("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            tables = [row[0] for row in result]

            return {
                "tables": tables,
                "count": len(tables),
            }

        except Exception as e:
            logger.error(f"获取数据库表失败: {e}")
            return {"error": str(e)}, 500

# 数据同步相关资源


@data_ns.route('/sync')
class DataSyncResource(Resource):
    def post(self):
        """同步数据"""
        try:
            from core.data_sync import data_sync

            data = request.get_json() or {}
            sync_type = data.get("type", "all")

            if sync_type == "stock_list":
                count = data_sync.sync_stock_list()
                return {"type": "stock_list", "count": count}

            elif sync_type == "index":
                index_code = data.get("index_code", "000001")
                count = data_sync.sync_index_data(index_code)
                return {"type": "index", "code": index_code, "count": count}

            elif sync_type == "stock":
                stock_code = data.get("stock_code", "000001")
                count = data_sync.sync_stock_daily(stock_code)
                return {"type": "stock", "code": stock_code, "count": count}

            else:
                results = data_sync.sync_all()
                return {"type": "all", "results": results}

        except Exception as e:
            logger.error(f"数据同步失败: {e}")
            return {"error": str(e)}, 500

# 风控相关资源


@risk_ns.route('/rules')
class RiskRulesResource(Resource):
    def get(self):
        """获取风控规则"""
        try:
            from core.risk_engine import risk_engine

            rules = risk_engine.get_rules()
            return {"rules": rules, "count": len(rules)}

        except Exception as e:
            logger.error(f"获取风控规则失败: {e}")
            return {"error": str(e)}, 500


@risk_ns.route('/check')
class RiskCheckResource(Resource):
    def post(self):
        """执行风控检查"""
        try:
            from core.risk_engine import risk_engine

            data = request.get_json() or {}

            context = {
                "position_ratio": data.get("position_ratio", 0),
                "drawdown": data.get("drawdown", 0),
                "daily_loss_ratio": data.get("daily_loss_ratio", 0),
                "cash_ratio": data.get("cash_ratio", 0.1),
                "stock_code": data.get("stock_code", ""),
                "check_type": "manual",
            }

            report = risk_engine.check_all(context)

            return {
                "overall_status": report.overall_status,
                "violation_count": report.violation_count,
                "warning_count": report.warning_count,
                "results": [
                    {
                        "rule_code": r.rule_code,
                        "rule_name": r.rule_name,
                        "passed": r.passed,
                        "current_value": r.current_value,
                        "threshold_value": r.threshold_value,
                        "message": r.message,
                        "level": r.level,
                    }
                    for r in report.results
                ],
            }

        except Exception as e:
            logger.error(f"风控检查失败: {e}")
            return {"error": str(e)}, 500

# 交易相关资源


@trading_ns.route('/orders')
class TradingOrdersResource(Resource):
    def get(self):
        """获取订单列表"""
        try:
            from core.trading_executor import trading_executor

            status = request.args.get("status")
            orders = trading_executor.get_orders(status)

            return {"orders": orders, "count": len(orders)}

        except Exception as e:
            logger.error(f"获取订单列表失败: {e}")
            return {"error": str(e)}, 500


@trading_ns.route('/positions')
class TradingPositionsResource(Resource):
    def get(self):
        """获取持仓列表"""
        try:
            from core.trading_executor import trading_executor

            positions = trading_executor.get_positions()

            return {"positions": positions, "count": len(positions)}

        except Exception as e:
            logger.error(f"获取持仓列表失败: {e}")
            return {"error": str(e)}, 500


@trading_ns.route('/order')
class TradingOrderResource(Resource):
    @trading_ns.expect(order_model)
    def post(self):
        """提交交易订单"""
        try:
            from core.trading_executor import TradingExecutor

            data = request.get_json() or {}

            stock_code = data.get("stock_code")
            trade_type = data.get("trade_type")
            volume = data.get("volume")
            price = data.get("price")

            if not all([stock_code, trade_type, volume]):
                return {"error": "缺少必要参数"}, 400

            executor = TradingExecutor()

            # 提交订单
            order = executor.submit_order(
                stock_code, trade_type, volume, price)

            if order:
                # 模拟成交
                trade = executor.execute_order(order)

                return {
                    "success": True,
                    "order_no": order.order_no,
                    "status": order.status,
                    "trade": {
                        "trade_no": trade.trade_no if trade else None,
                        "price": trade.price if trade else None,
                        "amount": trade.amount if trade else None,
                        "commission": trade.commission if trade else None,
                    } if trade else None,
                }
            else:
                return {"success": False, "error": "订单未通过风控检查"}

        except Exception as e:
            logger.error(f"提交订单失败: {e}")
            return {"error": str(e)}, 500

# 选股策略相关资源


@stock_selection_ns.route('')
class StockSelectionResource(Resource):
    def post(self):
        """多因子选股"""
        try:
            from core.stock_selector import StockSelector

            data = request.get_json() or {}
            date = data.get("date")
            top_n = data.get("top_n", 20)

            selector = StockSelector()
            results = selector.select(date=date, top_n=top_n)

            return {
                "count": len(results),
                "stocks": [
                    {
                        "rank": s.rank,
                        "code": s.code,
                        "name": s.name,
                        "industry": s.industry,
                        "total_score": round(s.total_score, 2),
                        "factor_scores": {
                            "value": round(s.factor_scores.get("value", 0), 2),
                            "quality": round(s.factor_scores.get("quality", 0), 2),
                            "momentum": round(s.factor_scores.get("momentum", 0), 2),
                            "volatility": round(s.factor_scores.get("volatility", 0), 2),
                        }
                    }
                    for s in results
                ]
            }

        except Exception as e:
            logger.error(f"选股失败: {e}")
            return {"error": str(e)}, 500

# AI诊断相关资源


@diagnosis_ns.route('/<code>')
class DiagnosisResource(Resource):
    def get(self, code):
        """AI多智能体诊断"""
        try:
            from core.agents import MultiAgentSystem

            system = MultiAgentSystem()
            result = system.diagnose(code)

            # 简化输出
            final_decision = result.get("final_decision")

            return {
                "code": code,
                "decision": final_decision.decision.value if final_decision else "unknown",
                "confidence": final_decision.confidence if final_decision else 0,
                "action_plan": final_decision.action_plan if final_decision else {},
                "reports": {
                    "market": {
                        "score": result["reports"]["market"].score,
                        "key_points": result["reports"]["market"].key_points[:3],
                    },
                    "fundamentals": {
                        "score": result["reports"]["fundamentals"].score,
                        "key_points": result["reports"]["fundamentals"].key_points[:3],
                    },
                    "news": {
                        "score": result["reports"]["news"].score,
                        "key_points": result["reports"]["news"].key_points[:3],
                    },
                },
                "reasoning": final_decision.reasoning[:500] + "..." if final_decision and len(final_decision.reasoning) > 500 else (final_decision.reasoning if final_decision else ""),
            }

        except Exception as e:
            logger.error(f"诊断失败: {e}")
            return {"error": str(e)}, 500


# 导入必要的模块
