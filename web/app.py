"""Web应用"""
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_restx import Api
from loguru import logger

from config.settings import settings
from core.backtest_engine import BacktestEngine
from core.cache import cache_manager
from core.database import db
from core.strategy_manager import StrategyManager
from strategies.registry import get_strategy_or_default, list_strategies
from web.namespaces import status_ns, strategies_ns, backtest_ns, trading_ns, risk_ns, data_ns, diagnosis_ns, database_ns, stock_selection_ns

app = Flask(__name__)

# 创建API实例
api = Api(app, version='1.0', title='iQuant API',
          description='iQuant 量化交易系统API文档',
          doc='/swagger/')

# 注册命名空间
api.add_namespace(status_ns, path='/api')
api.add_namespace(database_ns, path='/api/database')
api.add_namespace(strategies_ns, path='/api/strategies')
api.add_namespace(backtest_ns, path='/api')
api.add_namespace(trading_ns, path='/api/trading')
api.add_namespace(risk_ns, path='/api/risk')
api.add_namespace(data_ns, path='/api/data')
api.add_namespace(diagnosis_ns, path='/api')
api.add_namespace(stock_selection_ns, path='/api')

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


# ========== 静态文件服务 ==========

@app.route('/reports/<path:filename>')
def serve_report(filename):
    """提供报告文件访问"""
    from flask import send_from_directory
    import os
    reports_dir = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), 'reports')
    return send_from_directory(reports_dir, filename)


def create_app():
    """创建应用"""
    init_strategies()
    return app


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
