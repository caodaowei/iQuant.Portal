"""Web应用"""
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from loguru import logger

from config.settings import settings
from core.backtest_engine import BacktestEngine
from core.cache import cache_manager
from core.database import db
from core.strategy_manager import StrategyManager
from strategies.registry import get_strategy_or_default, list_strategies

app = Flask(__name__)

# 全局策略管理器
strategy_manager = StrategyManager()


def init_strategies():
    """初始化策略"""
    strategy_manager.register_strategy("MA_TREND")
    strategy_manager.register_strategy("MACD_SIGNAL")
    strategy_manager.register_strategy("RSI_MEAN_REVERT")
    strategy_manager.register_strategy("BOLL_BREAKOUT")


@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    """仪表盘"""
    return render_template("pages/dashboard.html")


@app.route("/strategies")
def strategies_page():
    """策略管理页面"""
    return render_template("pages/strategies.html")


@app.route("/backtest")
def backtest_page():
    """回测页面"""
    return render_template("pages/backtest.html")


@app.route("/trading")
def trading_page():
    """交易管理页面"""
    return render_template("pages/trading.html")


@app.route("/positions")
def positions_page():
    """持仓管理页面"""
    return render_template("pages/positions.html")


@app.route("/risk")
def risk_page():
    """风控管理页面"""
    return render_template("pages/risk.html")


@app.route("/data")
def data_page():
    """数据管理页面"""
    return render_template("pages/data.html")


@app.route("/api/status")
def api_status():
    """系统状态"""
    db_status = db.health_check()
    redis_status = cache_manager.health_check()

    return jsonify({
        "status": "ok" if db_status else "error",
        "database": "connected" if db_status else "disconnected",
        "redis": "connected" if redis_status else "disconnected",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/cache/stats")
def api_cache_stats():
    """获取缓存统计信息"""
    stats = cache_manager.get_stats()
    return jsonify(stats)


@app.route("/api/cache/clear", methods=["POST"])
def api_cache_clear():
    """清除缓存"""
    data = request.get_json() or {}
    namespace = data.get("namespace")

    if namespace:
        count = cache_manager.clear_namespace(namespace)
        return jsonify({"message": f"已清除 {namespace} 命名空间，删除 {count} 个键"})
    else:
        # 清除所有命名空间
        namespaces = ["daily_data", "stock_list", "index_data", "ai_diagnosis", "backtest_result", "strategy_signal"]
        total_count = 0
        for ns in namespaces:
            count = cache_manager.clear_namespace(ns)
            total_count += count

        return jsonify({"message": f"已清除所有缓存，共删除 {total_count} 个键"})


@app.route("/api/strategies")
def api_strategies():
    """获取策略列表"""
    strategies = strategy_manager.list_strategies()
    return jsonify({
        "strategies": strategies,
        "count": len(strategies),
    })


@app.route("/api/strategies/<code>/run", methods=["POST"])
def api_run_strategy(code):
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
        strategy = strategy_manager.strategies.get(code)
        if not strategy:
            return jsonify({"error": f"策略不存在: {code}"}), 404
        
        signals = strategy.run(market_data)
        latest = strategy.get_latest_signal(market_data)
        
        return jsonify({
            "strategy": code,
            "signal_count": len(signals),
            "latest_signal": {
                "date": str(latest.trade_date) if latest else None,
                "type": latest.signal_type if latest else None,
                "strength": latest.strength if latest else None,
                "reason": latest.reason if latest else None,
            },
        })
    
    except Exception as e:
        logger.error(f"运行策略失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    """运行回测（带缓存）"""
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
        cached_result = cache_manager.get("backtest_result", cache_key)
        if cached_result is not None:
            logger.info(f"回测结果缓存命中: {cache_key}")
            return jsonify(cached_result)

        # 生成示例数据
        from core.data_generator import create_sample_market_data
        market_data = create_sample_market_data(days)

        # 创建策略（使用注册表）
        strategy_class = get_strategy_or_default(strategy_code)
        strategy = strategy_class()

        # 运行回测
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
        cache_manager.set("backtest_result", cache_key, response_data, ttl=604800)
        logger.info(f"回测结果已缓存: {cache_key}")

        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"回测失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/database/tables")
def api_database_tables():
    """获取数据库表列表"""
    try:
        result = db.fetch_all("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in result]
        
        return jsonify({
            "tables": tables,
            "count": len(tables),
        })
    
    except Exception as e:
        logger.error(f"获取数据库表失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/data/sync", methods=["POST"])
def api_data_sync():
    """同步数据"""
    try:
        from core.data_sync import data_sync
        
        data = request.get_json() or {}
        sync_type = data.get("type", "all")
        
        if sync_type == "stock_list":
            count = data_sync.sync_stock_list()
            return jsonify({"type": "stock_list", "count": count})
        
        elif sync_type == "index":
            index_code = data.get("index_code", "000001")
            count = data_sync.sync_index_data(index_code)
            return jsonify({"type": "index", "code": index_code, "count": count})
        
        elif sync_type == "stock":
            stock_code = data.get("stock_code", "000001")
            count = data_sync.sync_stock_daily(stock_code)
            return jsonify({"type": "stock", "code": stock_code, "count": count})
        
        else:
            results = data_sync.sync_all()
            return jsonify({"type": "all", "results": results})
    
    except Exception as e:
        logger.error(f"数据同步失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/risk/rules")
def api_risk_rules():
    """获取风控规则"""
    try:
        from core.risk_engine import risk_engine
        
        rules = risk_engine.get_rules()
        return jsonify({"rules": rules, "count": len(rules)})
    
    except Exception as e:
        logger.error(f"获取风控规则失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/risk/check", methods=["POST"])
def api_risk_check():
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
        
        return jsonify({
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
        })
    
    except Exception as e:
        logger.error(f"风控检查失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/trading/orders")
def api_trading_orders():
    """获取订单列表"""
    try:
        from core.trading_executor import trading_executor
        
        status = request.args.get("status")
        orders = trading_executor.get_orders(status)
        
        return jsonify({"orders": orders, "count": len(orders)})
    
    except Exception as e:
        logger.error(f"获取订单列表失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/trading/positions")
def api_trading_positions():
    """获取持仓列表"""
    try:
        from core.trading_executor import trading_executor
        
        positions = trading_executor.get_positions()
        
        return jsonify({"positions": positions, "count": len(positions)})
    
    except Exception as e:
        logger.error(f"获取持仓列表失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/trading/order", methods=["POST"])
def api_trading_order():
    """提交交易订单"""
    try:
        from core.trading_executor import TradingExecutor
        
        data = request.get_json() or {}
        
        stock_code = data.get("stock_code")
        trade_type = data.get("trade_type")
        volume = data.get("volume")
        price = data.get("price")
        
        if not all([stock_code, trade_type, volume]):
            return jsonify({"error": "缺少必要参数"}), 400
        
        executor = TradingExecutor()
        
        # 提交订单
        order = executor.submit_order(stock_code, trade_type, volume, price)
        
        if order:
            # 模拟成交
            trade = executor.execute_order(order)
            
            return jsonify({
                "success": True,
                "order_no": order.order_no,
                "status": order.status,
                "trade": {
                    "trade_no": trade.trade_no if trade else None,
                    "price": trade.price if trade else None,
                    "amount": trade.amount if trade else None,
                    "commission": trade.commission if trade else None,
                } if trade else None,
            })
        else:
            return jsonify({"success": False, "error": "订单未通过风控检查"})
    
    except Exception as e:
        logger.error(f"提交订单失败: {e}")
        return jsonify({"error": str(e)}), 500


# ========== 新增：选股策略 API ==========

@app.route("/api/stock-selection", methods=["POST"])
def api_stock_selection():
    """多因子选股"""
    try:
        from core.stock_selector import StockSelector
        
        data = request.get_json() or {}
        date = data.get("date")
        top_n = data.get("top_n", 20)
        
        selector = StockSelector()
        results = selector.select(date=date, top_n=top_n)
        
        return jsonify({
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
        })
    
    except Exception as e:
        logger.error(f"选股失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/diagnosis/<code>", methods=["GET"])
def api_diagnosis(code):
    """AI多智能体诊断"""
    try:
        from core.agents import MultiAgentSystem
        
        system = MultiAgentSystem()
        result = system.diagnose(code)
        
        # 简化输出
        final_decision = result.get("final_decision")
        
        return jsonify({
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
        })
    
    except Exception as e:
        logger.error(f"诊断失败: {e}")
        return jsonify({"error": str(e)}), 500


# ========== 静态文件服务 ==========

@app.route('/reports/<path:filename>')
def serve_report(filename):
    """提供报告文件访问"""
    from flask import send_from_directory
    import os
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
    return send_from_directory(reports_dir, filename)


def create_app():
    """创建应用"""
    init_strategies()
    return app
# ========== 新增：可配置多智能体 API ==========

@app.route("/api/v2/diagnosis/<code>", methods=["GET"])
def api_v2_diagnosis(code):
    """可配置多智能体诊断 - 合并报告"""
    try:
        from core.configurable_agents import ConfigurableAgentSystem
        
        # 可选：指定配置文件路径
        config_path = request.args.get("config")
        
        system = ConfigurableAgentSystem(config_path)
        result = system.diagnose(code)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"可配置诊断失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/agents", methods=["GET"])
def api_v2_agents():
    """获取当前配置的 Agent 列表"""
    try:
        from core.configurable_agents import ConfigurableAgentSystem
        
        config_path = request.args.get("config")
        system = ConfigurableAgentSystem(config_path)
        
        agents_info = []
        for agent in system.agents:
            agents_info.append({
                "name": agent.name,
                "type": agent.agent_type,
                "enabled": agent.is_enabled(),
                "weight": agent.weight,
                "params": agent.params
            })
        
        return jsonify({
            "agents": agents_info,
            "count": len(agents_info),
            "config_path": str(system.config_path)
        })
    
    except Exception as e:
        logger.error(f"获取 Agent 列表失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/reports/<code>", methods=["GET"])
def api_v2_report_html(code):
    """获取合并后的 HTML 报告"""
    try:
        from core.configurable_agents import ConfigurableAgentSystem
        
        config_path = request.args.get("config")
        system = ConfigurableAgentSystem(config_path)
        result = system.diagnose(code)
        
        merged = result.get("merged_report", {})
        
        # 生成简单 HTML 报告
        html_sections = ""
        for section in merged.get('sections', []):
            score_color = "#4caf50" if section.get('score', 0) >= 70 else "#ff9800" if section.get('score', 0) >= 50 else "#f44336"
            html_sections += f"""
<div class=\"section\">
    <h2>{section.get('agent_name')} <span style=\"color: {score_color}\">({section.get('score', 0)}分)</span></h2>
    <pre>{section.get('content', '')}</pre>
</div>
"""
        
        risk_html = ""
        if merged.get('risk_warnings'):
            risk_html = '<div class=\"section\"><h2>风险提示</h2>' + ''.join([f'<div class=\"risk\">• {r}</div>' for r in merged.get('risk_warnings', [])]) + '</div>'
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset=\"UTF-8\"><title>{code} 分析报告</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
.score {{ font-size: 48px; font-weight: bold; }}
.decision {{ display: inline-block; padding: 10px 20px; border-radius: 20px; font-weight: bold; margin-top: 10px; background: {'#4caf50' if merged.get('decision') == 'BUY' else '#f44336' if merged.get('decision') == 'SELL' else '#ff9800' if merged.get('decision') == 'HOLD' else '#2196f3'}; }}
.section {{ background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.section h2 {{ margin-top: 0; color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
.action-plan {{ background: #e3f2fd; padding: 15px; border-radius: 8px; }}
.risk {{ color: #f44336; }}
pre {{ white-space: pre-wrap; font-family: inherit; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
th {{ background: #f5f5f5; }}
</style></head><body>
<div class=\"header\">
    <h1>{merged.get('title', code)}</h1>
    <div class=\"score\">{merged.get('overall_score', 0)}/100</div>
    <div class=\"decision\">{merged.get('decision', 'HOLD')}</div>
    <p>置信度: {merged.get('confidence', 0)}%</p>
</div>
<div class=\"section\">
    <h2>执行方案</h2>
    <div class=\"action-plan\">
        <table>
            <tr><th>项目</th><th>数值</th></tr>
            <tr><td>决策</td><td><strong>{merged.get('action_plan', {}).get('decision', 'N/A')}</strong></td></tr>
            <tr><td>当前价格</td><td>{merged.get('action_plan', {}).get('current_price', 'N/A')}</td></tr>
            <tr><td>目标价格</td><td>{merged.get('action_plan', {}).get('target_price', 'N/A')}</td></tr>
            <tr><td>止损价格</td><td>{merged.get('action_plan', {}).get('stop_loss', 'N/A')}</td></tr>
            <tr><td>建议仓位</td><td>{merged.get('action_plan', {}).get('position_size', 'N/A')}</td></tr>
            <tr><td>持有周期</td><td>{merged.get('action_plan', {}).get('time_horizon', 'N/A')}</td></tr>
        </table>
    </div>
</div>
<div class=\"section\">
    <h2>分析摘要</h2>
    <p>{merged.get('summary', '').replace(chr(10), '<br>')}</p>
</div>
{html_sections}
{risk_html}
<div class=\"section\" style=\"text-align: center; color: #999;\">
    <small>生成时间: {result.get('timestamp', '')}</small><br>
    <small>参与分析: {', '.join(merged.get('contributing_agents', []))}</small>
</div>
</body></html>"""
        
        from flask import Response
        return Response(html, mimetype='text/html')
    
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== 简单认证 API（用于本地测试）====================

# 模拟用户数据库（仅用于测试）
USERS_DB = {
    "admin": {
        "username": "admin",
        "email": "admin@iquant.com",
        "password": "admin123",
        "role": "admin",
    },
    "trader1": {
        "username": "trader1",
        "email": "trader1@iquant.com",
        "password": "trader123",
        "role": "trader",
    },
}


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    """用户登录 API"""
    try:
        data = request.get_json() or {}
        username = data.get("username") or data.get("email")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "请输入用户名和密码"}), 400

        # 查找用户
        user = None
        for u in USERS_DB.values():
            if (u["username"] == username or u["email"] == username) and u["password"] == password:
                user = u
                break

        if not user:
            return jsonify({"error": "用户名或密码错误"}), 401

        # 返回简单的 token（实际生产环境应使用 JWT）
        import base64
        import time
        token_data = f"{user['username']}:{user['role']}:{int(time.time())}"
        token = base64.b64encode(token_data.encode()).decode()

        return jsonify({
            "success": True,
            "token": token,
            "user": {
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
            }
        })

    except Exception as e:
        logger.error(f"登录失败: {e}")
        return jsonify({"error": str(e)}), 500
