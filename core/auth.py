"""用户认证与授权模块"""
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from config.settings import settings

# ==================== 密码加密 ====================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==================== JWT 配置 ====================

SECRET_KEY = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ==================== OAuth2 Scheme ====================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ==================== 用户角色 ====================

class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"              # 管理员：所有权限
    TRADER = "trader"            # 交易员：策略执行、下单
    ANALYST = "analyst"          # 分析师：查看数据、回测
    VIEWER = "viewer"            # 观察者：只读权限


# ==================== Pydantic 模型 ====================

class Token(BaseModel):
    """访问令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """令牌数据"""
    username: Optional[str] = None
    role: Optional[str] = None


class User(BaseModel):
    """用户模型"""
    id: int
    username: str
    email: str
    role: UserRole = UserRole.VIEWER
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserCreate(BaseModel):
    """用户创建请求"""
    username: str
    email: str
    password: str
    role: UserRole = UserRole.VIEWER


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


# ==================== 密码工具函数 ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希

    Args:
        password: 明文密码

    Returns:
        哈希后的密码
    """
    return pwd_context.hash(password)


# ==================== JWT Token 工具函数 ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌

    Args:
        data: 要编码的数据（通常包含 username 和 role）
        expires_delta: 过期时间增量

    Returns:
        JWT 访问令牌
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建刷新令牌

    Args:
        data: 要编码的数据

    Returns:
        JWT 刷新令牌
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """解码 JWT Token

    Args:
        token: JWT Token

    Returns:
        TokenData 对象

    Raises:
        HTTPException: Token 无效或已过期
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")

        if username is None:
            raise credentials_exception

        return TokenData(username=username, role=role)

    except JWTError:
        raise credentials_exception


# ==================== 用户认证依赖 ====================

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """获取当前用户（从 Token 中解析）

    Args:
        token: JWT Access Token

    Returns:
        User 对象

    Raises:
        HTTPException: 用户不存在或已被禁用
    """
    token_data = decode_token(token)

    # TODO: 从数据库查询用户
    # 这里暂时返回 mock 用户
    user = User(
        id=1,
        username=token_data.username,
        email=f"{token_data.username}@example.com",
        role=UserRole(token_data.role or "viewer"),
        is_active=True,
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# ==================== 权限检查装饰器 ====================

def require_role(required_role: UserRole):
    """角色权限检查装饰器

    Args:
        required_role: 所需的最低角色权限

    Usage:
        @app.post("/api/trading/order")
        @require_role(UserRole.TRADER)
        async def submit_order(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        from functools import wraps

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中获取 current_user
            current_user = kwargs.get('current_user')

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # 角色权限等级
            role_hierarchy = {
                UserRole.VIEWER: 0,
                UserRole.ANALYST: 1,
                UserRole.TRADER: 2,
                UserRole.ADMIN: 3,
            }

            user_level = role_hierarchy.get(current_user.role, 0)
            required_level = role_hierarchy.get(required_role, 0)

            if user_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_role.value}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ==================== 审计日志 ====================

class AuditLogger:
    """审计日志记录器"""

    @staticmethod
    def log_action(
        user_id: int,
        action: str,
        resource: str,
        details: dict = None,
        ip_address: str = None,
    ):
        """记录用户操作

        Args:
            user_id: 用户 ID
            action: 操作类型（CREATE, UPDATE, DELETE, LOGIN, etc.）
            resource: 资源类型（ORDER, STRATEGY, BACKTEST, etc.）
            details: 详细信息
            ip_address: IP 地址
        """
        from loguru import logger

        log_entry = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {},
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 记录到日志文件
        logger.info(f"AUDIT: {log_entry}")

        # TODO: 写入数据库审计日志表
        # db.execute(
        #     "INSERT INTO audit_logs (user_id, action, resource, details, ip_address, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        #     (user_id, action, resource, json.dumps(details), ip_address, datetime.utcnow())
        # )


audit_logger = AuditLogger()
