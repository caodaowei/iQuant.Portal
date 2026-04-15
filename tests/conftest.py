"""Pytest 配置和共享 fixtures"""
import pytest
import asyncio
from typing import Generator
from unittest.mock import MagicMock, patch

import pandas as pd
from datetime import date, timedelta

# FastAPI 测试客户端
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture
def sample_stock_data():
    """示例股票数据"""
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(100)]
    return pd.DataFrame({
        "trade_date": dates,
        "stock_code": "000001",
        "open_price": [100 + i * 0.5 for i in range(100)],
        "high_price": [102 + i * 0.5 for i in range(100)],
        "low_price": [98 + i * 0.5 for i in range(100)],
        "close_price": [100 + i * 0.6 for i in range(100)],
        "volume": [1000000 + i * 1000 for i in range(100)],
        "amount": [100000000 + i * 100000 for i in range(100)],
    })


@pytest.fixture
def sample_backtest_results():
    """示例回测结果"""
    return {
        "initial_capital": 1000000.0,
        "final_capital": 1150000.0,
        "total_return": 0.15,
        "annualized_return": 0.18,
        "max_drawdown": -0.08,
        "sharpe_ratio": 1.5,
        "total_trades": 25,
        "win_rate": 0.64,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "nav_data": [],
        "trades": [],
    }


@pytest.fixture
def mock_data_fetcher(sample_stock_data):
    """Mock 数据获取器"""
    with patch('core.data_fetcher.data_fetcher') as mock:
        mock.get_daily_data.return_value = sample_stock_data
        mock.get_stock_list.return_value = pd.DataFrame({
            "stock_code": ["000001", "000002", "000003"],
            "stock_name": ["平安银行", "万科A", "国农科技"],
        })
        yield mock


@pytest.fixture
def mock_cache_manager():
    """Mock 缓存管理器"""
    with patch('core.cache.cache_manager') as mock:
        mock.get.return_value = None
        mock.set.return_value = True
        mock.health_check.return_value = True
        mock.get_stats.return_value = {
            "hits": 100,
            "misses": 20,
            "errors": 0,
            "hit_rate": 83.33,
        }
        yield mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery 任务"""
    with patch('core.task_queue.celery_app') as mock:
        mock_task = MagicMock()
        mock_task.id = "test-task-id-12345"
        mock.delay.return_value = mock_task
        yield mock


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client():
    """FastAPI 异步测试客户端"""
    from web.app_async import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sync_client():
    """FastAPI 同步测试客户端"""
    from web.app_async import app
    return TestClient(app)


@pytest.fixture
def sample_ai_diagnosis():
    """示例 AI 诊断结果"""
    return {
        "code": "000001",
        "stages": {
            "stage1_analysts": [
                {
                    "agent_name": "MarketAnalyst",
                    "role": "market_analyst",
                    "score": 75,
                    "signals": ["buy"],
                }
            ],
            "stage5_decision": {
                "agent_name": "Manager",
                "recommendation": "buy",
                "confidence": 80,
            },
        },
        "final_decision": {
            "decision": "buy",
            "confidence": 80,
            "reasoning": "技术面和基本面均向好",
        },
    }


@pytest.fixture
def sample_strategy_list():
    """示例策略列表"""
    return [
        {"code": "MA_TREND", "name": "均线趋势策略", "type": "timing"},
        {"code": "MACD_SIGNAL", "name": "MACD 信号策略", "type": "timing"},
        {"code": "RSI_MEAN_REVERT", "name": "RSI 均值回归策略", "type": "timing"},
    ]
