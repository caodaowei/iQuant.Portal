"""Celery 异步任务定义"""
import time
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger
from celery import states

from core.task_queue import celery_app
from core.data_fetcher import data_fetcher
from core.backtest_engine import BacktestEngine
from core.agents import MultiAgentSystem
from strategies.registry import get_strategy_or_default
from core.metrics import (
    celery_tasks_total,
    celery_task_duration_seconds,
    backtest_executions_total,
    ai_diagnosis_total,
    data_sync_total,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_stock_data(self, stock_code: str, days: int = 365) -> Dict:
    """异步同步股票数据

    Args:
        stock_code: 股票代码
        days: 同步天数

    Returns:
        同步结果
    """
    start_time = time.time()
    try:
        logger.info(f"开始同步股票数据: {stock_code}, 天数: {days}")

        # 获取数据
        df = data_fetcher.get_daily_data(stock_code, days=days)

        if df.empty:
            # 记录失败指标
            data_sync_total.labels(sync_type='single', status='failed').inc()
            celery_tasks_total.labels(task_name='sync_stock_data', status='failed').inc()
            return {
                "status": "failed",
                "message": f"未获取到 {stock_code} 的数据",
                "stock_code": stock_code,
            }

        # 注意：数据已缓存到 Redis，如需持久化到数据库请取消注释以下代码
        # from core.database import db
        # db.save_daily_data(df)

        result = {
            "status": "success",
            "stock_code": stock_code,
            "records_synced": len(df),
            "date_range": {
                "start": str(df["trade_date"].min()),
                "end": str(df["trade_date"].max()),
            },
        }

        # 记录成功指标
        data_sync_total.labels(sync_type='single', status='success').inc()
        celery_tasks_total.labels(task_name='sync_stock_data', status='success').inc()
        celery_task_duration_seconds.labels(task_name='sync_stock_data').observe(
            time.time() - start_time
        )

        logger.info(f"股票数据同步完成: {stock_code}, {len(df)} 条记录")
        return result

    except Exception as exc:
        # 记录异常指标
        data_sync_total.labels(sync_type='single', status='error').inc()
        celery_tasks_total.labels(task_name='sync_stock_data', status='error').inc()
        logger.error(f"股票数据同步失败 {stock_code}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def run_backtest(
    self,
    strategy_code: str,
    days: int = 300,
    initial_capital: float = 1000000.0,
) -> Dict:
    """异步运行回测

    Args:
        strategy_code: 策略代码
        days: 回测天数
        initial_capital: 初始资金

    Returns:
        回测结果
    """
    start_time = time.time()
    try:
        logger.info(f"开始回测: {strategy_code}, 天数: {days}")

        # 生成测试数据
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

        # 生成图表数据
        from core.visualization import create_backtest_chart
        chart_json = create_backtest_chart(
            nav_data=results.get("nav_data", []),
            trades=results.get("trades", []),
        )

        result = {
            "status": "completed",
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

        # 记录成功指标
        backtest_executions_total.labels(strategy=strategy_code, status='success').inc()
        celery_tasks_total.labels(task_name='run_backtest', status='success').inc()
        celery_task_duration_seconds.labels(task_name='run_backtest').observe(
            time.time() - start_time
        )

        logger.info(f"回测完成: {strategy_code}, 收益率: {results['total_return']:.2%}")
        return result

    except Exception as exc:
        # 记录失败指标
        backtest_executions_total.labels(strategy=strategy_code, status='failure').inc()
        celery_tasks_total.labels(task_name='run_backtest', status='failure').inc()
        logger.error(f"回测失败 {strategy_code}: {exc}")
        self.update_state(state=states.FAILURE, meta={"error": str(exc)})
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def run_ai_diagnosis(self, stock_code: str) -> Dict:
    """异步运行 AI 诊断

    Args:
        stock_code: 股票代码

    Returns:
        诊断结果
    """
    start_time = time.time()
    try:
        logger.info(f"开始 AI 诊断: {stock_code}")

        system = MultiAgentSystem()
        result = system.diagnose(stock_code)

        # 记录成功指标
        ai_diagnosis_total.labels(stock_code=stock_code, status='success').inc()
        celery_tasks_total.labels(task_name='run_ai_diagnosis', status='success').inc()
        celery_task_duration_seconds.labels(task_name='run_ai_diagnosis').observe(
            time.time() - start_time
        )

        logger.info(f"AI 诊断完成: {stock_code}")
        return {
            "status": "completed",
            "stock_code": stock_code,
            "diagnosis": result,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 记录失败指标
        ai_diagnosis_total.labels(stock_code=stock_code, status='failure').inc()
        celery_tasks_total.labels(task_name='run_ai_diagnosis', status='failure').inc()
        logger.error(f"AI 诊断失败 {stock_code}: {exc}")
        self.update_state(state=states.FAILURE, meta={"error": str(exc)})
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def batch_sync_stocks(self, stock_codes: List[str], days: int = 365) -> Dict:
    """批量同步股票数据

    Args:
        stock_codes: 股票代码列表
        days: 同步天数

    Returns:
        批量同步结果
    """
    start_time = time.time()
    try:
        logger.info(f"开始批量同步 {len(stock_codes)} 只股票")

        results = []
        success_count = 0
        failed_count = 0

        for code in stock_codes:
            try:
                result = sync_stock_data(code, days)
                results.append(result)
                if result["status"] == "success":
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"同步 {code} 失败: {e}")
                failed_count += 1

        result = {
            "status": "completed",
            "total": len(stock_codes),
            "success": success_count,
            "failed": failed_count,
            "details": results,
        }

        # 记录批量同步指标
        data_sync_total.labels(sync_type='batch', status='success').inc()
        celery_tasks_total.labels(task_name='batch_sync_stocks', status='success').inc()
        celery_task_duration_seconds.labels(task_name='batch_sync_stocks').observe(
            time.time() - start_time
        )

        logger.info(f"批量同步完成: 成功 {success_count}, 失败 {failed_count}")
        return result

    except Exception as exc:
        # 记录失败指标
        data_sync_total.labels(sync_type='batch', status='error').inc()
        celery_tasks_total.labels(task_name='batch_sync_stocks', status='error').inc()
        logger.error(f"批量同步失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def scheduled_data_sync(self) -> Dict:
    """定时数据同步任务（每日收盘后执行）

    Returns:
        同步结果
    """
    try:
        logger.info("开始定时数据同步任务")

        # 获取所有需要同步的股票
        stock_list = data_fetcher.get_stock_list()

        if stock_list.empty:
            return {"status": "failed", "message": "无法获取股票列表"}

        # 取前 100 只股票作为示例（实际应该全量同步）
        stock_codes = stock_list["stock_code"].head(100).tolist()

        # 调用批量同步
        result = batch_sync_stocks(stock_codes, days=1)

        logger.info(f"定时同步完成: {result}")
        return result

    except Exception as exc:
        logger.error(f"定时同步失败: {exc}")
        raise self.retry(exc=exc)
