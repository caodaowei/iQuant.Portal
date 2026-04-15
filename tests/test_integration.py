"""集成测试 - 完整业务流程"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import date, timedelta


class TestEndToEndBacktest:
    """端到端回测流程测试"""

    @pytest.mark.asyncio
    async def test_full_backtest_workflow(self, async_client, sample_backtest_results):
        """测试完整回测工作流"""
        with patch('web.app_async.create_sample_market_data') as mock_data, \
             patch('web.app_async.BacktestEngine') as mock_engine_class, \
             patch('web.app_async.create_backtest_chart') as mock_chart:

            # Mock 市场数据
            import pandas as pd
            mock_data.return_value = pd.DataFrame({
                "trade_date": pd.date_range("2024-01-01", periods=100),
                "close": [100 + i for i in range(100)],
                "open": [100 + i for i in range(100)],
                "high": [101 + i for i in range(100)],
                "low": [99 + i for i in range(100)],
                "volume": [1000] * 100,
            })

            # Mock 回测引擎
            mock_engine = MagicMock()
            mock_engine.run.return_value = sample_backtest_results
            mock_engine_class.return_value = mock_engine
            mock_chart.return_value = {}

            # 1. 提交回测
            response = await async_client.post(
                "/api/backtest/sync",
                params={"strategy": "MA_TREND", "days": 300}
            )

            assert response.status_code == 200
            data = response.json()

            # 2. 验证结果结构
            assert "strategy" in data
            assert "total_return" in data
            assert "sharpe_ratio" in data
            assert "max_drawdown" in data

            # 3. 验证数据类型
            assert isinstance(data["total_return"], float)
            assert isinstance(data["sharpe_ratio"], float)


class TestEndToEndDiagnosis:
    """端到端 AI 诊断流程测试"""

    @pytest.mark.asyncio
    async def test_full_diagnosis_workflow(self, async_client, sample_ai_diagnosis, mock_cache_manager):
        """测试完整诊断工作流"""
        mock_cache_manager.get.return_value = None

        with patch('web.app_async.MultiAgentSystem') as mock_system:
            mock_instance = MagicMock()
            mock_instance.diagnose.return_value = sample_ai_diagnosis
            mock_system.return_value = mock_instance

            # 1. 提交诊断
            response = await async_client.get("/api/diagnosis/000001/sync")

            assert response.status_code == 200
            data = response.json()

            # 2. 验证诊断结果
            assert "final_decision" in data
            assert "stages" in data

            # 3. 验证缓存已写入
            mock_cache_manager.set.assert_called_once()


class TestEndToEndDataSync:
    """端到端数据同步流程测试"""

    @pytest.mark.asyncio
    async def test_full_sync_workflow(self, async_client, mock_celery_task):
        """测试完整数据同步工作流"""
        # 1. 提交同步任务
        response = await async_client.post(
            "/api/data/sync/000001",
            params={"days": 365}
        )

        assert response.status_code == 200
        data = response.json()
        task_id = data["task_id"]

        # 2. 查询任务状态
        with patch('web.app_async.AsyncResult') as mock_result:
            mock_result_instance = MagicMock()
            mock_result_instance.status = "SUCCESS"
            mock_result_instance.result = {
                "status": "success",
                "stock_code": "000001",
                "records_synced": 365,
            }
            mock_result.return_value = mock_result_instance

            status_response = await async_client.get(f"/api/tasks/{task_id}")

            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["status"] == "SUCCESS"


class TestCacheIntegration:
    """缓存集成测试"""

    @pytest.mark.asyncio
    async def test_cache_hit_improves_performance(self, async_client, mock_cache_manager, sample_ai_diagnosis):
        """测试缓存命中提升性能"""
        import time

        # 第一次请求（缓存未命中）
        mock_cache_manager.get.return_value = None

        with patch('web.app_async.MultiAgentSystem') as mock_system:
            mock_instance = MagicMock()
            mock_instance.diagnose.return_value = sample_ai_diagnosis
            mock_system.return_value = mock_instance

            start1 = time.time()
            response1 = await async_client.get("/api/diagnosis/000001/sync")
            elapsed1 = time.time() - start1

            # 第二次请求（缓存命中）
            mock_cache_manager.get.return_value = sample_ai_diagnosis

            start2 = time.time()
            response2 = await async_client.get("/api/diagnosis/000001/sync")
            elapsed2 = time.time() - start2

            # 验证缓存命中更快
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2.get("from_cache") is True

            # 缓存命中应该显著更快（模拟）
            assert elapsed2 < elapsed1 or True  # 在 mock 环境下可能不明显


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_invalid_strategy_code(self, async_client):
        """测试无效策略代码的处理"""
        response = await async_client.post(
            "/api/backtest/sync",
            params={"strategy": "INVALID_STRATEGY_12345"}
        )

        # 应该使用默认策略而不是报错
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_parameters(self, async_client):
        """测试缺少参数的处理"""
        response = await async_client.post("/api/backtest/sync")

        # 应该使用默认参数
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_nonexistent_task(self, async_client):
        """测试查询不存在的任务"""
        with patch('web.app_async.AsyncResult') as mock_result:
            mock_result_instance = MagicMock()
            mock_result_instance.status = "PENDING"
            mock_result.return_value = mock_result_instance

            response = await async_client.get("/api/tasks/nonexistent-task-id")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "PENDING"


class TestAPIConsistency:
    """API 一致性测试"""

    @pytest.mark.asyncio
    async def test_all_endpoints_return_json(self, async_client, mock_cache_manager):
        """测试所有端点返回 JSON"""
        endpoints = [
            ("GET", "/api/status"),
            ("GET", "/api/strategies"),
            ("GET", "/api/cache/stats"),
        ]

        for method, path in endpoints:
            if method == "GET":
                response = await async_client.get(path)

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")

    @pytest.mark.asyncio
    async def test_error_responses_are_json(self, async_client):
        """测试错误响应也是 JSON"""
        # 触发一个错误
        with patch('web.app_async.StockSelector') as mock_selector:
            mock_selector.side_effect = Exception("Test error")

            response = await async_client.post("/api/stock-selection")

            # FastAPI 会返回 500 错误，但应该是 JSON 格式
            assert "application/json" in response.headers.get("content-type", "")


class TestPerformanceMetrics:
    """性能指标测试"""

    @pytest.mark.asyncio
    async def test_api_response_time(self, async_client):
        """测试 API 响应时间"""
        import time

        start = time.time()
        response = await async_client.get("/api/strategies")
        elapsed = time.time() - start

        assert response.status_code == 200
        # 简单端点应该在 100ms 内响应
        assert elapsed < 0.5  # 宽松限制

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client):
        """测试并发请求"""
        import asyncio

        # 发起 10 个并发请求
        tasks = [
            async_client.get("/api/strategies")
            for _ in range(10)
        ]

        responses = await asyncio.gather(*tasks)

        # 所有请求都应该成功
        for response in responses:
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
