"""缓存功能验证脚本"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_import():
    """测试导入"""
    try:
        from core.cache import cache_manager
        print("✓ CacheManager 导入成功")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        print("\n请先安装 redis 依赖:")
        print("  pip install redis>=5.0.0")
        return False


def test_redis_connection():
    """测试 Redis 连接"""
    from core.cache import cache_manager

    if cache_manager.client is None:
        print("✗ Redis 未连接（可能未启动或未安装）")
        print("\n请确保 Redis 服务正在运行:")
        print("  - Windows: 下载并运行 redis-server.exe")
        print("  - Docker: docker run -d -p 6379:6379 redis:latest")
        return False

    if cache_manager.health_check():
        print("✓ Redis 连接成功")
        return True
    else:
        print("✗ Redis 连接失败")
        return False


def test_basic_operations():
    """测试基本操作"""
    from core.cache import cache_manager

    if not cache_manager.client:
        print("⊘ 跳过基本操作测试（Redis 未连接）")
        return False

    # 测试设置和获取
    cache_manager.set("test", "hello", {"message": "world"})
    result = cache_manager.get("test", "hello")

    if result and result.get("message") == "world":
        print("✓ 缓存读写测试通过")
        cache_manager.delete("test", "hello")
        return True
    else:
        print("✗ 缓存读写测试失败")
        return False


def test_dataframe_caching():
    """测试 DataFrame 缓存"""
    import pandas as pd
    from datetime import date
    from core.cache import cache_manager

    if not cache_manager.client:
        print("⊘ 跳过 DataFrame 缓存测试（Redis 未连接）")
        return False

    df = pd.DataFrame({
        "date": [date(2024, 1, 1), date(2024, 1, 2)],
        "close": [100.0, 101.0],
        "volume": [1000, 1100],
    })

    cache_manager.set_pickle("test", "sample_df", df)
    result = cache_manager.get_pickle("test", "sample_df")

    if isinstance(result, pd.DataFrame) and len(result) == 2:
        print("✓ DataFrame 缓存测试通过")
        cache_manager.delete("test", "sample_df")
        return True
    else:
        print("✗ DataFrame 缓存测试失败")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("iQuant 缓存功能验证")
    print("=" * 60)
    print()

    # 测试导入
    if not test_import():
        return

    print()

    # 测试连接
    connected = test_redis_connection()
    print()

    if not connected:
        print("提示: Redis 未连接，缓存功能将降级为无缓存模式")
        print("      系统仍可正常运行，但性能会有所降低")
        return

    # 测试基本操作
    test_basic_operations()
    print()

    # 测试 DataFrame 缓存
    test_dataframe_caching()
    print()

    # 显示统计
    from core.cache import cache_manager
    stats = cache_manager.get_stats()
    print("缓存统计:")
    print(f"  命中次数: {stats['hits']}")
    print(f"  未命中次数: {stats['misses']}")
    print(f"  命中率: {stats['hit_rate']}%")
    print()

    print("=" * 60)
    print("验证完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
