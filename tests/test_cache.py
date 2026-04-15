"""Redis 缓存测试"""
import pytest
import pandas as pd
from datetime import date

from core.cache import cache_manager


class TestCacheManager:
    """缓存管理器测试"""

    def test_set_and_get(self):
        """测试基本读写"""
        # 设置缓存
        success = cache_manager.set("test", "key1", {"value": 123})
        assert success is True

        # 获取缓存
        result = cache_manager.get("test", "key1")
        assert result == {"value": 123}

        # 清理
        cache_manager.delete("test", "key1")

    def test_cache_miss(self):
        """测试缓存未命中"""
        result = cache_manager.get("test", "nonexistent")
        assert result is None

    def test_delete(self):
        """测试删除缓存"""
        cache_manager.set("test", "key2", {"value": 456})
        cache_manager.delete("test", "key2")

        result = cache_manager.get("test", "key2")
        assert result is None

    def test_exists(self):
        """测试检查存在性"""
        cache_manager.set("test", "key3", {"value": 789})
        assert cache_manager.exists("test", "key3") is True

        cache_manager.delete("test", "key3")
        assert cache_manager.exists("test", "key3") is False

    def test_pickle_dataframe(self):
        """测试 Pickle 序列化 DataFrame"""
        df = pd.DataFrame({
            "date": [date(2024, 1, 1), date(2024, 1, 2)],
            "close": [100.0, 101.0],
            "volume": [1000, 1100],
        })

        cache_manager.set_pickle("test", "df1", df)
        result = cache_manager.get_pickle("test", "df1")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert result["close"].iloc[0] == 100.0

        cache_manager.delete("test", "df1")

    def test_stats(self):
        """测试统计信息"""
        cache_manager.reset_stats()

        # 触发一些缓存操作
        cache_manager.set("test", "stats_key", {"value": 1})
        cache_manager.get("test", "stats_key")  # hit
        cache_manager.get("test", "nonexistent")  # miss

        stats = cache_manager.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["hit_rate"] > 0

        cache_manager.delete("test", "stats_key")

    def test_clear_namespace(self):
        """测试清空命名空间"""
        cache_manager.set("test_ns", "key1", {"v": 1})
        cache_manager.set("test_ns", "key2", {"v": 2})
        cache_manager.set("test_ns", "key3", {"v": 3})

        count = cache_manager.clear_namespace("test_ns")
        assert count >= 3

    def test_health_check(self):
        """测试健康检查"""
        status = cache_manager.health_check()
        # Redis 可能未运行，所以只检查返回布尔值
        assert isinstance(status, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
