"""API 限流中间件"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from starlette.responses import JSONResponse

# ==================== 限流器配置 ====================

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # 默认限制：每分钟 200 次请求
)


# ==================== 自定义限流处理器 ====================

async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """自定义限流异常处理

    Args:
        request: FastAPI 请求对象
        exc: 限流异常

    Returns:
        JSON 响应
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": str(exc.detail),
            "retry_after": 60,  # 建议重试时间（秒）
        },
        headers={
            "Retry-After": "60",
            "X-RateLimit-Limit": "200",
            "X-RateLimit-Remaining": "0",
        }
    )


# ==================== IP 黑名单管理 ====================

class IPBlacklistManager:
    """IP 黑名单管理器"""

    def __init__(self):
        self._blacklist = set()
        self._whitelist = set()

    def add_to_blacklist(self, ip_address: str):
        """添加 IP 到黑名单"""
        self._blacklist.add(ip_address)

    def remove_from_blacklist(self, ip_address: str):
        """从黑名单移除 IP"""
        self._blacklist.discard(ip_address)

    def add_to_whitelist(self, ip_address: str):
        """添加 IP 到白名单"""
        self._whitelist.add(ip_address)

    def is_blocked(self, ip_address: str) -> bool:
        """检查 IP 是否被阻止"""
        # 白名单优先
        if ip_address in self._whitelist:
            return False
        return ip_address in self._blacklist

    def get_blacklist(self) -> set:
        """获取黑名单"""
        return self._blacklist.copy()

    def clear_blacklist(self):
        """清空黑名单"""
        self._blacklist.clear()


# 全局 IP 黑名单实例
ip_blacklist = IPBlacklistManager()


# ==================== IP 过滤中间件 ====================

class IPFilterMiddleware:
    """IP 过滤中间件

    在请求到达路由之前检查 IP 是否在黑名单中
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 获取客户端 IP
        client_host = scope.get("client", ("unknown",))[0]

        # 检查黑名单
        if ip_blacklist.is_blocked(client_host):
            response = JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "detail": "Your IP address has been blocked"
                }
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


# ==================== 常用限流规则 ====================

# API 端点限流规则
RATE_LIMIT_RULES = {
    # 认证相关
    "auth_login": "10/minute",       # 登录：每分钟 10 次
    "auth_register": "5/hour",       # 注册：每小时 5 次

    # 数据查询
    "get_strategies": "100/minute",  # 获取策略：每分钟 100 次
    "get_stock_data": "60/minute",   # 获取股票数据：每分钟 60 次

    # AI 诊断（计算密集型）
    "ai_diagnosis": "20/minute",     # AI 诊断：每分钟 20 次

    # 回测（资源密集型）
    "backtest_sync": "10/minute",    # 同步回测：每分钟 10 次
    "backtest_async": "30/minute",   # 异步回测提交：每分钟 30 次

    # 交易操作（关键操作）
    "submit_order": "10/minute",     # 下单：每分钟 10 次
    "cancel_order": "20/minute",     # 撤单：每分钟 20 次

    # 数据同步
    "sync_data": "5/minute",         # 数据同步：每分钟 5 次

    # 管理操作
    "cache_clear": "10/hour",        # 清除缓存：每小时 10 次
}
