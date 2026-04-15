"""FastAPI 异步 Web 应用"""
import time
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from loguru import logger
from celery.result import AsyncResult
from slowapi.errors import RateLimitExceeded

from config.settings import settings
from core.cache import cache_manager
from core.database import db
from core.task_queue import celery_app
from core.tasks import run_backtest, run_ai_diagnosis, sync_stock_data
from core.rate_limiter import limiter, custom_rate_limit_handler, IPFilterMiddleware
from core.metrics import (
    PrometheusMiddleware,
    create_metrics_endpoint,
    backtest_executions_total,
    ai_diagnosis_total,
    data_sync_total,
    stock_selection_total,
    risk_check_total,
    celery_tasks_total,
    celery_task_duration_seconds,
    update_cache_stats,
    update_db_pool_stats,
    update_redis_status,
    app_uptime_seconds,
)
from strategies.registry import get_strategy_or_default, list_strategies
from web.routes_auth import router as auth_router

# 创建 FastAPI 应用
app = FastAPI(
    title="iQuant API",
    description="iQuant 量化交易系统 API (FastAPI)",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# 记录应用启动时间
APP_START_TIME = time.time()

# ==================== 中间件配置 ====================

# Prometheus 监控中间件（必须在最前面）
app.add_middleware(PrometheusMiddleware)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IP 过滤中间件（黑名单）
app.add_middleware(IPFilterMiddleware)

# 限流器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

# ==================== 路由注册 ====================

# 认证路由
app.include_router(auth_router)

# 投资账本路由
from web.routes_ledger import router as ledger_router
app.include_router(ledger_router)


# ==================== 系统状态 ====================

@app.get("/api/status")
async def api_status():
    """系统状态检查"""
    db_status = db.health_check()
    redis_status = cache_manager.health_check()

    return {
        "status": "ok" if db_status else "degraded",
        "database": "connected" if db_status else "disconnected",
        "redis": "connected" if redis_status else "disconnected",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
    }


# ==================== 策略管理 ====================

@app.get("/api/strategies")
async def get_strategies():
    """获取策略列表"""
    strategies = list_strategies()

    return {
        "strategies": strategies,
        "count": len(strategies),
    }


@app.post("/api/strategies/{strategy_code}/run")
async def run_strategy(strategy_code: str, background_tasks: BackgroundTasks):
    """运行策略（异步）"""
    # TODO: 实现策略执行逻辑
    return {
        "message": f"策略 {strategy_code} 已开始执行",
        "task_id": None,
    }


# ==================== 回测（异步任务）====================

@app.post("/api/backtest/async")
async def start_backtest(
    strategy: str = "MA_TREND",
    days: int = 300,
    initial_capital: float = 1000000.0,
):
    """启动异步回测任务

    立即返回 task_id，客户端通过 /api/tasks/{task_id} 查询结果
    """
    task = run_backtest.delay(
        strategy_code=strategy,
        days=days,
        initial_capital=initial_capital,
    )
    
    # 记录回测执行指标
    backtest_executions_total.labels(strategy=strategy, status='started').inc()

    return {
        "task_id": task.id,
        "status": "pending",
        "message": "回测任务已提交",
    }


@app.post("/api/backtest/sync")
async def run_backtest_sync(
    strategy: str = "MA_TREND",
    days: int = 300,
    initial_capital: float = 1000000.0,
):
    """同步运行回测（直接等待结果）

    适用于快速回测场景
    """
    start_time = time.time()
    try:
        from core.data_generator import create_sample_market_data
        from core.backtest_engine import BacktestEngine
        from core.visualization import create_backtest_chart

        # 生成测试数据
        market_data = create_sample_market_data(days)

        # 创建策略（使用注册表）
        strategy_class = get_strategy_or_default(strategy)
        strategy_obj = strategy_class()

        # 运行回测
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission_rate=0.00025,
            slippage=0.001,
        )
        engine.set_strategy(strategy_obj)
        engine.set_market_data(market_data)

        results = engine.run()

        # 生成图表
        chart_json = create_backtest_chart(
            nav_data=results.get("nav_data", []),
            trades=results.get("trades", []),
        )
        
        # 记录成功指标
        backtest_executions_total.labels(strategy=strategy, status='success').inc()
        celery_task_duration_seconds.labels(task_name='backtest_sync').observe(
            time.time() - start_time
        )

        return {
            "strategy": strategy,
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

    except Exception as e:
        # 记录失败指标
        backtest_executions_total.labels(strategy=strategy, status='failure').inc()
        logger.error(f"回测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI 诊断（异步任务）====================

@app.get("/api/diagnosis/{stock_code}/async")
async def start_diagnosis(stock_code: str):
    """启动异步 AI 诊断"""
    task = run_ai_diagnosis.delay(stock_code=stock_code)
    
    # 记录 AI 诊断指标
    ai_diagnosis_total.labels(stock_code=stock_code, status='started').inc()

    return {
        "task_id": task.id,
        "status": "pending",
        "message": "AI 诊断任务已提交",
    }


@app.get("/api/diagnosis/{stock_code}/sync")
async def diagnose_stock_sync(stock_code: str):
    """同步 AI 诊断（带缓存）

    优先从缓存读取，未命中则实时计算
    """
    try:
        # 尝试从缓存获取
        cached_result = cache_manager.get("ai_diagnosis", stock_code)
        if cached_result is not None:
            logger.info(f"AI 诊断缓存命中: {stock_code}")
            ai_diagnosis_total.labels(stock_code=stock_code, status='cache_hit').inc()
            return {
                **cached_result,
                "from_cache": True,
            }

        # 实时诊断
        from core.agents import MultiAgentSystem
        system = MultiAgentSystem()
        result = system.diagnose(stock_code)

        # 写入缓存
        cache_manager.set("ai_diagnosis", stock_code, result, ttl=21600)
        
        # 记录成功指标
        ai_diagnosis_total.labels(stock_code=stock_code, status='success').inc()

        return {
            **result,
            "from_cache": False,
        }

    except Exception as e:
        # 记录失败指标
        ai_diagnosis_total.labels(stock_code=stock_code, status='failure').inc()
        logger.error(f"AI 诊断失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据同步（异步任务）====================

@app.post("/api/data/sync/{stock_code}")
async def sync_single_stock(stock_code: str, days: int = 365):
    """同步单只股票数据"""
    task = sync_stock_data.delay(stock_code=stock_code, days=days)
    
    # 记录数据同步指标
    data_sync_total.labels(sync_type='single', status='started').inc()

    return {
        "task_id": task.id,
        "status": "pending",
        "message": f"开始同步 {stock_code} 数据",
    }


@app.post("/api/data/sync/batch")
async def sync_batch_stocks(stock_codes: List[str], days: int = 365):
    """批量同步股票数据"""
    from core.tasks import batch_sync_stocks

    task = batch_sync_stocks.delay(stock_codes=stock_codes, days=days)
    
    # 记录批量同步指标
    data_sync_total.labels(sync_type='batch', status='started').inc()

    return {
        "task_id": task.id,
        "status": "pending",
        "message": f"开始批量同步 {len(stock_codes)} 只股票",
    }


# ==================== 任务状态查询 ====================

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询异步任务状态"""
    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.status == "SUCCESS":
        response["result"] = result.result
    elif result.status == "FAILURE":
        response["error"] = str(result.result)
    elif result.status == "PENDING":
        response["message"] = "任务等待中"
    elif result.status == "STARTED":
        response["message"] = "任务执行中"

    return response


@app.delete("/api/tasks/{task_id}")
async def revoke_task(task_id: str):
    """撤销正在执行的任务"""
    celery_app.control.revoke(task_id, terminate=True)

    return {
        "message": f"任务 {task_id} 已撤销",
    }


# ==================== 缓存管理 ====================

@app.get("/api/cache/stats")
async def get_cache_stats():
    """获取缓存统计"""
    stats = cache_manager.get_stats()
    return stats


@app.post("/api/cache/clear")
async def clear_cache(namespace: Optional[str] = None):
    """清除缓存"""
    if namespace:
        count = cache_manager.clear_namespace(namespace)
        return {"message": f"已清除 {namespace} 命名空间，删除 {count} 个键"}
    else:
        namespaces = [
            "daily_data", "stock_list", "index_data",
            "ai_diagnosis", "backtest_result", "strategy_signal"
        ]
        total_count = 0
        for ns in namespaces:
            count = cache_manager.clear_namespace(ns)
            total_count += count

        return {"message": f"已清除所有缓存，共删除 {total_count} 个键"}


# ==================== 选股器 ====================

@app.post("/api/stock-selection")
async def select_stocks(
    top_n: int = 10,
    industry: Optional[str] = None,
):
    """多因子选股"""
    try:
        from core.stock_selector import StockSelector

        selector = StockSelector()
        result = selector.select(top_n=top_n, industry=industry)
        
        # 记录选股成功指标
        stock_selection_total.labels(status='success').inc()

        return {
            "stocks": result,
            "count": len(result),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        # 记录选股失败指标
        stock_selection_total.labels(status='failure').inc()
        logger.error(f"选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 风控检查 ====================

@app.post("/api/risk/check")
async def check_risk(
    stock_code: str,
    volume: int,
    price: float,
):
    """风控检查"""
    try:
        from core.risk_engine import RiskEngine

        engine = RiskEngine()
        report = engine.check_trade(stock_code, volume, price)
        
        # 记录风控检查结果
        result_label = 'passed' if report.passed else 'rejected'
        risk_check_total.labels(result=result_label).inc()

        return {
            "passed": report.passed,
            "warnings": report.warnings,
            "violations": report.violations,
        }

    except Exception as e:
        logger.error(f"风控检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Prometheus Metrics 端点 ====================

@app.get("/metrics")
async def metrics():
    """Prometheus metrics 端点
    
    暴露应用程序性能指标供 Prometheus 抓取
    """
    # 更新应用运行时间
    app_uptime_seconds.set(time.time() - APP_START_TIME)
    
    # 更新缓存统计
    update_cache_stats(cache_manager)
    
    # 更新数据库连接池统计
    try:
        from core.db_performance import pool_monitor
        update_db_pool_stats(pool_monitor)
    except Exception:
        pass
    
    # 更新 Redis 状态
    update_redis_status(cache_manager)
    
    return Response(
        content=create_metrics_endpoint()().body,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


# ==================== 健康检查端点 ====================

@app.get("/health")
async def health_check():
    """Kubernetes/Docker 健康检查"""
    db_status = db.health_check()
    redis_status = cache_manager.health_check()

    if db_status and redis_status:
        return JSONResponse(status_code=200, content={"status": "healthy"})
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "connected" if db_status else "disconnected",
                "redis": "connected" if redis_status else "disconnected",
            }
        )


# ==================== 根路径 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "iQuant API",
        "version": "2.0.0",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web.app_async:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
