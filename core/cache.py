"""Redis 缓存管理器"""
import json
import pickle
from typing import Any, Optional

import redis
from loguru import logger

from config.settings import settings


class CacheManager:
    """统一缓存管理层

    提供统一的缓存接口，支持：
    - 字符串、JSON、Pickle 序列化
    - TTL 自动过期
    - 缓存键命名空间管理
    - 缓存统计和监控
    """

    # 默认 TTL（秒）
    DEFAULT_TTL = {
        "stock_info": 86400,      # 股票基础信息: 24h
        "daily_data": 3600,       # 日线行情: 1h
        "strategy_signal": 1800,  # 策略信号: 30min
        "ai_diagnosis": 21600,    # AI 诊断: 6h
        "backtest_result": 604800,  # 回测结果: 7d
        "index_data": 3600,       # 指数数据: 1h
        "stock_list": 86400,      # 股票列表: 24h
    }

    def __init__(self, redis_url: Optional[str] = None):
        """初始化缓存管理器

        Args:
            redis_url: Redis 连接 URL，默认从配置读取
        """
        self.redis_url = redis_url or settings.redis_url
        logger.info(f"使用Redis URL: {self.redis_url}")
        self.client: Optional[redis.Redis] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
        }

        try:
            self.client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=False,  # 使用 bytes，由我们控制序列化
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # 测试连接
            self.client.ping()
            logger.info(f"Redis 连接成功: {self.redis_url}")
        except Exception as e:
            logger.warning(f"Redis 连接失败，缓存功能将不可用: {e}")
            self.client = None

    def _make_key(self, namespace: str, key: str) -> str:
        """生成带命名空间的缓存键

        Args:
            namespace: 命名空间（如 stock, strategy）
            key: 缓存键

        Returns:
            完整的缓存键
        """
        return f"iquant:{namespace}:{key}"

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """获取缓存值（JSON 反序列化）

        Args:
            namespace: 命名空间
            key: 缓存键

        Returns:
            缓存的值，不存在或过期返回 None
        """
        if not self.client:
            self._stats["misses"] += 1
            return None

        try:
            cache_key = self._make_key(namespace, key)
            value = self.client.get(cache_key)

            if value is None:
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            return json.loads(value.decode("utf-8"))
        except Exception as e:
            logger.error(f"缓存读取失败: {e}")
            self._stats["errors"] += 1
            return None

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置缓存值（JSON 序列化）

        Args:
            namespace: 命名空间
            key: 缓存键
            value: 缓存值（必须是 JSON 可序列化的）
            ttl: 过期时间（秒），None 则使用默认值

        Returns:
            是否设置成功
        """
        if not self.client:
            return False

        try:
            cache_key = self._make_key(namespace, key)

            # 确定 TTL
            if ttl is None:
                ttl = self.DEFAULT_TTL.get(namespace, 3600)

            # JSON 序列化
            serialized = json.dumps(value, ensure_ascii=False, default=str).encode(
                "utf-8"
            )

            self.client.setex(cache_key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"缓存写入失败: {e}")
            self._stats["errors"] += 1
            return False

    def get_pickle(self, namespace: str, key: str) -> Optional[Any]:
        """获取 Pickle 序列化的缓存值（用于复杂对象如 DataFrame）

        注意：Pickle 反序列化存在安全风险，仅用于可信数据源。
        Redis 应配置访问控制，防止未授权访问。

        Args:
            namespace: 命名空间
            key: 缓存键

        Returns:
            缓存的值，不存在或过期返回 None
        """
        if not self.client:
            self._stats["misses"] += 1
            return None

        try:
            cache_key = self._make_key(namespace, key)
            value = self.client.get(cache_key)

            if value is None:
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            return pickle.loads(value)
        except Exception as e:
            logger.error(f"缓存读取失败 (Pickle): {e}")
            self._stats["errors"] += 1
            return None

    def set_pickle(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置 Pickle 序列化的缓存值（用于复杂对象如 DataFrame）

        注意：仅缓存可信数据，避免反序列化恶意对象。

        Args:
            namespace: 命名空间
            key: 缓存键
            value: 缓存值（可以是任意 Python 对象）
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        if not self.client:
            return False

        try:
            cache_key = self._make_key(namespace, key)

            if ttl is None:
                ttl = self.DEFAULT_TTL.get(namespace, 3600)

            # Pickle 序列化
            serialized = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

            self.client.setex(cache_key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"缓存写入失败 (Pickle): {e}")
            self._stats["errors"] += 1
            return False

    def delete(self, namespace: str, key: str) -> bool:
        """删除缓存

        Args:
            namespace: 命名空间
            key: 缓存键

        Returns:
            是否删除成功
        """
        if not self.client:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            self.client.delete(cache_key)
            return True
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
            self._stats["errors"] += 1
            return False

    def delete_pattern(self, namespace: str, pattern: str = "*") -> int:
        """批量删除匹配模式的缓存

        Args:
            namespace: 命名空间
            pattern: 匹配模式（支持通配符 *）

        Returns:
            删除的键数量
        """
        if not self.client:
            return 0

        try:
            cache_pattern = self._make_key(namespace, pattern)
            keys = self.client.keys(cache_pattern)

            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"批量删除缓存失败: {e}")
            self._stats["errors"] += 1
            return 0

    def exists(self, namespace: str, key: str) -> bool:
        """检查缓存是否存在

        Args:
            namespace: 命名空间
            key: 缓存键

        Returns:
            是否存在
        """
        if not self.client:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            return self.client.exists(cache_key) > 0
        except Exception as e:
            logger.error(f"检查缓存存在性失败: {e}")
            return False

    def clear_namespace(self, namespace: str) -> int:
        """清空整个命名空间的缓存

        Args:
            namespace: 命名空间

        Returns:
            删除的键数量
        """
        return self.delete_pattern(namespace, "*")

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            包含 hits, misses, errors, hit_rate 的字典
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (
            self._stats["hits"] / total * 100 if total > 0 else 0
        )

        return {
            **self._stats,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total,
        }

    def reset_stats(self):
        """重置统计信息"""
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    def health_check(self) -> bool:
        """健康检查

        Returns:
            Redis 是否可用
        """
        if not self.client:
            return False

        try:
            return self.client.ping()
        except Exception:
            return False

    def close(self):
        """关闭 Redis 连接"""
        if self.client:
            self.client.close()
            logger.info("Redis 连接已关闭")


# 全局缓存实例（单例）
cache_manager = CacheManager()
