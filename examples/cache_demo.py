"""
Redis 缓存使用示例

演示如何在 iQuant 中使用缓存功能
"""
import sys
from pathlib import Path
import time

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cache import cache_manager
from core.data_fetcher import data_fetcher


def example_basic_cache():
    """示例 1: 基本缓存操作"""
    print("=" * 60)
    print("示例 1: 基本缓存操作")
    print("=" * 60)

    # 设置缓存
    cache_manager.set("example", "user_123", {
        "name": "张三",
        "age": 30,
        "email": "zhangsan@example.com"
    })
    print("✓ 已设置用户缓存")

    # 获取缓存
    user = cache_manager.get("example", "user_123")
    print(f"✓ 获取用户: {user}")

    # 检查存在性
    exists = cache_manager.exists("example", "user_123")
    print(f"✓ 缓存存在: {exists}")

    # 删除缓存
    cache_manager.delete("example", "user_123")
    print("✓ 已删除缓存")
    print()


def example_dataframe_cache():
    """示例 2: DataFrame 缓存"""
    print("=" * 60)
    print("示例 2: DataFrame 缓存（日线数据）")
    print("=" * 60)

    stock_code = "000001"
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    # 第一次请求（从数据源获取，较慢）
    print("\n第一次请求（无缓存）...")
    start_time = time.time()
    df1 = data_fetcher.get_daily_data(stock_code, start_date, end_date)
    elapsed1 = time.time() - start_time
    print(f"  耗时: {elapsed1:.2f} 秒")
    print(f"  数据行数: {len(df1)}")

    # 第二次请求（从缓存获取，快速）
    print("\n第二次请求（缓存命中）...")
    start_time = time.time()
    df2 = data_fetcher.get_daily_data(stock_code, start_date, end_date)
    elapsed2 = time.time() - start_time
    print(f"  耗时: {elapsed2:.2f} 秒")
    print(f"  数据行数: {len(df2)}")

    # 性能对比
    if elapsed1 > 0:
        speedup = elapsed1 / max(elapsed2, 0.001)
        print(f"\n  ⚡ 性能提升: {speedup:.1f}x")

    print()


def example_cache_stats():
    """示例 3: 缓存统计"""
    print("=" * 60)
    print("示例 3: 缓存统计")
    print("=" * 60)

    stats = cache_manager.get_stats()
    print(f"\n总请求数: {stats['total_requests']}")
    print(f"命中次数: {stats['hits']}")
    print(f"未命中次数: {stats['misses']}")
    print(f"错误次数: {stats['errors']}")
    print(f"命中率: {stats['hit_rate']}%")
    print()


def example_cache_ttl():
    """示例 4: 自定义 TTL"""
    print("=" * 60)
    print("示例 4: 自定义过期时间")
    print("=" * 60)

    # 设置 10 秒过期的缓存
    cache_manager.set("example", "temp_data", {"value": 123}, ttl=10)
    print("✓ 已设置缓存（TTL: 10秒）")

    # 立即读取
    result = cache_manager.get("example", "temp_data")
    print(f"  立即读取: {result}")

    # 等待 11 秒后读取
    print("  等待 11 秒...")
    time.sleep(11)
    result = cache_manager.get("example", "temp_data")
    print(f"  11秒后读取: {result} (已过期)")
    print()


def example_namespace_management():
    """示例 5: 命名空间管理"""
    print("=" * 60)
    print("示例 5: 命名空间批量管理")
    print("=" * 60)

    # 设置多个缓存
    for i in range(5):
        cache_manager.set("test_ns", f"key_{i}", {"index": i})

    print("✓ 已设置 5 个测试缓存")

    # 清空整个命名空间
    count = cache_manager.clear_namespace("test_ns")
    print(f"✓ 已清空命名空间，删除 {count} 个键")
    print()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("iQuant Redis 缓存使用示例")
    print("=" * 60 + "\n")

    # 检查 Redis 连接
    if not cache_manager.health_check():
        print("⚠️  Redis 未连接，请先启动 Redis 服务")
        print("\n启动方式:")
        print("  1. Docker: docker-compose up -d redis")
        print("  2. 本地: redis-server")
        return

    print("✓ Redis 连接成功\n")

    # 运行示例
    try:
        example_basic_cache()
        example_dataframe_cache()
        example_cache_stats()
        example_cache_ttl()
        example_namespace_management()

        # 最终统计
        print("=" * 60)
        print("最终缓存统计")
        print("=" * 60)
        example_cache_stats()

    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
