"""FastAPI 集成测试"""
import pytest
from unittest.mock import patch, MagicMock


class TestSystemStatus:
    """系统状态 API 测试"""

    @pytest.mark.asyncio
    async def test_status_endpoint(self, async_client, mock_cache_manager):
        """测试系统状态端点"""
        with patch('core.database.db') as mock_db:
            mock_db.health_check.return_value = True

            response = await async_client.get("/api/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["ok", "degraded"]
            assert "database" in data
            assert "redis" in data
            assert "version" in data
            assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, async_client, mock_cache_manager):
        """测试健康检查（健康状态）"""
        with patch('core.database.db') as mock_db:
            mock_db.health_check.return_value = True
            mock_cache_manager.health_check.return_value = True

            response = await async_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, async_client, mock_cache_manager):
        """测试健康检查（不健康状态）"""
        with patch('core.database.db') as mock_db:
            mock_db.health_check.return_value = False
            mock_cache_manager.health_check.return_value = False

            response = await async_client.get("/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"


class TestStrategies:
    """策略管理 API 测试"""

    @pytest.mark.asyncio
    async def test_get_strategies(self, async_client):
        """测试获取策略列表"""
        response = await async_client.get("/api/strategies")

        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert "count" in data
        assert data["count"] > 0
        assert isinstance(data["strategies"], list)

    @pytest.mark.asyncio
    async def test_strategy_structure(self, async_client):
        """测试策略数据结构"""
        response = await async_client.get("/api/strategies")
        data = response.json()

        for strategy in data["strategies"]:
            assert "code" in strategy
            assert "name" in strategy
            assert "type" in strategy


class TestBacktest:
    """回测 API 测试"""

    @pytest.mark.asyncio
    async def test_backtest_sync_success(self, async_client, sample_backtest_results):
        """测试同步回测成功"""
        with patch('web.app_async.create_sample_market_data') as mock_data, \
             patch('web.app_async.BacktestEngine') as mock_engine_class, \
             patch('web.app_async.create_backtest_chart') as mock_chart:

            # Mock 数据
            import pandas as pd
            mock_data.return_value = pd.DataFrame({
                "trade_date": pd.date_range("2024-01-01", periods=100),
                "close": [100 + i for i in range(100)],
                "open": [100 + i for i in range(100)],
                "high": [101 + i for i in range(100)],
                "low": [99 + i for i in range(100)],
                "volume": [1000] * 100,
            })

            # Mock 引擎
            mock_engine = MagicMock()
            mock_engine.run.return_value = sample_backtest_results
            mock_engine_class.return_value = mock_engine
            mock_chart.return_value = {}

            response = await async_client.post(
                "/api/backtest/sync",
                params={"strategy": "MA_TREND", "days": 300}
            )

            assert response.status_code == 200
            data = response.json()
            assert "strategy" in data
            assert "total_return" in data
            assert "sharpe_ratio" in data

    @pytest.mark.asyncio
    async def test_backtest_async_submit(self, async_client, mock_celery_task):
        """测试异步回测提交"""
        response = await async_client.post(
            "/api/backtest/async",
            params={"strategy": "MACD_SIGNAL", "days": 300}
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_backtest_invalid_strategy(self, async_client):
        """测试无效策略代码"""
        response = await async_client.post(
            "/api/backtest/sync",
            params={"strategy": "INVALID_STRATEGY", "days": 300}
        )

        # 应该使用默认策略而不是报错
        assert response.status_code == 200


class TestAIDiagnosis:
    """AI 诊断 API 测试"""

    @pytest.mark.asyncio
    async def test_diagnosis_sync_with_cache(self, async_client, sample_ai_diagnosis, mock_cache_manager):
        """测试同步诊断（缓存命中）"""
        mock_cache_manager.get.return_value = sample_ai_diagnosis

        response = await async_client.get("/api/diagnosis/000001/sync")

        assert response.status_code == 200
        data = response.json()
        assert data.get("from_cache") is True
        assert "final_decision" in data

    @pytest.mark.asyncio
    async def test_diagnosis_sync_without_cache(self, async_client, sample_ai_diagnosis, mock_cache_manager):
        """测试同步诊断（缓存未命中）"""
        mock_cache_manager.get.return_value = None

        with patch('web.app_async.MultiAgentSystem') as mock_system:
            mock_instance = MagicMock()
            mock_instance.diagnose.return_value = sample_ai_diagnosis
            mock_system.return_value = mock_instance

            response = await async_client.get("/api/diagnosis/000001/sync")

            assert response.status_code == 200
            data = response.json()
            assert data.get("from_cache") is False
            mock_cache_manager.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_diagnosis_async_submit(self, async_client, mock_celery_task):
        """测试异步诊断提交"""
        response = await async_client.get("/api/diagnosis/000001/async")

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"


class TestDataSync:
    """数据同步 API 测试"""

    @pytest.mark.asyncio
    async def test_sync_single_stock(self, async_client, mock_celery_task):
        """测试单只股票同步"""
        response = await async_client.post(
            "/api/data/sync/000001",
            params={"days": 365}
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "000001" in data["message"]

    @pytest.mark.asyncio
    async def test_sync_batch_stocks(self, async_client, mock_celery_task):
        """测试批量股票同步"""
        stock_codes = ["000001", "000002", "000003"]

        response = await async_client.post(
            "/api/data/sync/batch",
            json={"stock_codes": stock_codes, "days": 365}
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "3" in data["message"]


class TestTaskManagement:
    """任务管理 API 测试"""

    @pytest.mark.asyncio
    async def test_get_task_status_success(self, async_client):
        """测试查询成功任务状态"""
        with patch('web.app_async.AsyncResult') as mock_result:
            mock_result_instance = MagicMock()
            mock_result_instance.status = "SUCCESS"
            mock_result_instance.result = {"data": "test"}
            mock_result.return_value = mock_result_instance

            response = await async_client.get("/api/tasks/test-task-id")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "SUCCESS"
            assert "result" in data

    @pytest.mark.asyncio
    async def test_get_task_status_pending(self, async_client):
        """测试查询等待中任务状态"""
        with patch('web.app_async.AsyncResult') as mock_result:
            mock_result_instance = MagicMock()
            mock_result_instance.status = "PENDING"
            mock_result.return_value = mock_result_instance

            response = await async_client.get("/api/tasks/test-task-id")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_get_task_status_failure(self, async_client):
        """测试查询失败任务状态"""
        with patch('web.app_async.AsyncResult') as mock_result:
            mock_result_instance = MagicMock()
            mock_result_instance.status = "FAILURE"
            mock_result_instance.result = Exception("Test error")
            mock_result.return_value = mock_result_instance

            response = await async_client.get("/api/tasks/test-task-id")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "FAILURE"
            assert "error" in data

    @pytest.mark.asyncio
    async def test_revoke_task(self, async_client):
        """测试撤销任务"""
        with patch('web.app_async.celery_app') as mock_celery:
            response = await async_client.delete("/api/tasks/test-task-id")

            assert response.status_code == 200
            mock_celery.control.revoke.assert_called_once()


class TestCacheManagement:
    """缓存管理 API 测试"""

    @pytest.mark.asyncio
    async def test_cache_stats(self, async_client, mock_cache_manager):
        """测试缓存统计"""
        response = await async_client.get("/api/cache/stats")

        assert response.status_code == 200
        data = response.json()
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate" in data

    @pytest.mark.asyncio
    async def test_clear_cache_all(self, async_client, mock_cache_manager):
        """测试清除所有缓存"""
        mock_cache_manager.clear_namespace.return_value = 10

        response = await async_client.post("/api/cache/clear")

        assert response.status_code == 200
        data = response.json()
        assert "已清除" in data["message"]

    @pytest.mark.asyncio
    async def test_clear_cache_namespace(self, async_client, mock_cache_manager):
        """测试清除指定命名空间缓存"""
        mock_cache_manager.clear_namespace.return_value = 5

        response = await async_client.post(
            "/api/cache/clear?namespace=ai_diagnosis"
        )

        assert response.status_code == 200
        data = response.json()
        assert "ai_diagnosis" in data["message"]


class TestStockSelection:
    """选股器 API 测试"""

    @pytest.mark.asyncio
    async def test_stock_selection(self, async_client):
        """测试选股功能"""
        with patch('web.app_async.StockSelector') as mock_selector:
            mock_instance = MagicMock()
            mock_instance.select.return_value = [
                {"code": "000001", "score": 95},
                {"code": "000002", "score": 90},
            ]
            mock_selector.return_value = mock_instance

            response = await async_client.post(
                "/api/stock-selection",
                params={"top_n": 10}
            )

            assert response.status_code == 200
            data = response.json()
            assert "stocks" in data
            assert "count" in data


class TestRiskCheck:
    """风控检查 API 测试"""

    @pytest.mark.asyncio
    async def test_risk_check_passed(self, async_client):
        """测试风控检查通过"""
        with patch('web.app_async.RiskEngine') as mock_engine:
            mock_instance = MagicMock()
            mock_report = MagicMock()
            mock_report.passed = True
            mock_report.warnings = []
            mock_report.violations = []
            mock_instance.check_trade.return_value = mock_report
            mock_engine.return_value = mock_instance

            response = await async_client.post(
                "/api/risk/check",
                params={"stock_code": "000001", "volume": 1000, "price": 50.0}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["passed"] is True

    @pytest.mark.asyncio
    async def test_risk_check_failed(self, async_client):
        """测试风控检查失败"""
        with patch('web.app_async.RiskEngine') as mock_engine:
            mock_instance = MagicMock()
            mock_report = MagicMock()
            mock_report.passed = False
            mock_report.warnings = ["持仓比例过高"]
            mock_report.violations = ["超过单笔限制"]
            mock_instance.check_trade.return_value = mock_report
            mock_engine.return_value = mock_instance

            response = await async_client.post(
                "/api/risk/check",
                params={"stock_code": "000001", "volume": 10000, "price": 50.0}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["passed"] is False
            assert len(data["violations"]) > 0


class TestRootEndpoint:
    """根路径测试"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        """测试根路径"""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "iQuant" in data["name"]
        assert "2.0.0" in data["version"]
        assert "docs" in data
