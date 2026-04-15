"""认证 API 路由"""
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm

from core.auth import (
    Token,
    User,
    UserCreate,
    UserRole,
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_current_active_user,
    require_role,
    audit_logger,
)
from core.rate_limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ==================== 模拟用户数据库（演示用）====================
# 注意：生产环境应使用真实数据库存储用户信息
# 参考 core/auth.py 中的 UserStore 类实现

MOCK_USERS_DB = {}


def _init_mock_users():
    """延迟初始化模拟用户数据（避免模块加载时的bcrypt问题）"""
    global MOCK_USERS_DB
    if not MOCK_USERS_DB:
        MOCK_USERS_DB = {
            "admin": {
                "id": 1,
                "username": "admin",
                "email": "admin@iquant.com",
                "password_hash": get_password_hash("admin123"),
                "role": UserRole.ADMIN,
                "is_active": True,
            },
            "trader1": {
                "id": 2,
                "username": "trader1",
                "email": "trader1@iquant.com",
                "password_hash": get_password_hash("trader123"),
                "role": UserRole.TRADER,
                "is_active": True,
            },
            "analyst1": {
                "id": 3,
                "username": "analyst1",
                "email": "analyst1@iquant.com",
                "password_hash": get_password_hash("analyst123"),
                "role": UserRole.ANALYST,
                "is_active": True,
            },
        }


def get_user_from_db(username: str) -> dict:
    """从数据库获取用户（Mock）"""
    _init_mock_users()
    return MOCK_USERS_DB.get(username)


def create_user_in_db(user_data: UserCreate) -> User:
    """创建新用户（Mock）"""
    user_id = len(MOCK_USERS_DB) + 1

    new_user = {
        "id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": get_password_hash(user_data.password),
        "role": user_data.role,
        "is_active": True,
    }

    MOCK_USERS_DB[user_data.username] = new_user

    return User(
        id=user_id,
        username=user_data.username,
        email=user_data.email,
        role=user_data.role,
        is_active=True,
    )


# ==================== 认证端点 ====================

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录

    Args:
        form_data: OAuth2 密码表单（username + password）

    Returns:
        访问令牌和刷新令牌

    Raises:
        HTTPException: 用户名或密码错误
    """
    # 查找用户
    user_dict = get_user_from_db(form_data.username)

    if not user_dict or not verify_password(form_data.password, user_dict["password_hash"]):
        audit_logger.log_action(
            user_id=0,
            action="LOGIN_FAILED",
            resource="USER",
            details={"username": form_data.username},
            ip_address=request.client.host if request.client else None,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查账户是否激活
    if not user_dict["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # 创建用户对象
    user = User(
        id=user_dict["id"],
        username=user_dict["username"],
        email=user_dict["email"],
        role=user_dict["role"],
        is_active=user_dict["is_active"],
    )

    # 生成 Token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "role": user.role.value}
    )

    # 记录审计日志
    audit_logger.log_action(
        user_id=user.id,
        action="LOGIN",
        resource="USER",
        details={"username": user.username},
        ip_address=request.client.host if request.client else None,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800,  # 30分钟
    }


@router.post("/register", response_model=User)
@limiter.limit("5/hour")
async def register(request: Request, user_data: UserCreate):
    """用户注册

    Args:
        user_data: 用户注册信息

    Returns:
        创建的用户对象
    """
    # 检查用户名是否已存在
    if get_user_from_db(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )

    # 检查邮箱是否已存在
    for user in MOCK_USERS_DB.values():
        if user["email"] == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

    # 创建用户
    new_user = create_user_in_db(user_data)

    # 记录审计日志
    audit_logger.log_action(
        user_id=new_user.id,
        action="REGISTER",
        resource="USER",
        details={"username": new_user.username},
        ip_address=request.client.host if request.client else None,
    )

    return new_user


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """刷新访问令牌

    Args:
        refresh_token: 刷新令牌

    Returns:
        新的访问令牌和刷新令牌
    """
    try:
        token_data = decode_token(refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # 查找用户
    user_dict = get_user_from_db(token_data.username)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # 生成新 Token
    access_token = create_access_token(
        data={"sub": user_dict["username"], "role": user_dict["role"].value},
        expires_delta=timedelta(minutes=30),
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user_dict["username"], "role": user_dict["role"].value}
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 1800,
    }


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user), request: Request = None):
    """用户登出"""
    audit_logger.log_action(
        user_id=current_user.id,
        action="LOGOUT",
        resource="USER",
        details={"username": current_user.username},
        ip_address=request.client.host if request and request.client else None,
    )

    return {"message": "Successfully logged out"}


# ==================== 管理端点 ====================

@router.get("/users", response_model=List[User])
@require_role(UserRole.ADMIN)
async def list_users(current_user: User = Depends(get_current_user)):
    """列出所有用户（仅管理员）"""
    users = [
        User(
            id=u["id"],
            username=u["username"],
            email=u["email"],
            role=u["role"],
            is_active=u["is_active"],
        )
        for u in MOCK_USERS_DB.values()
    ]
    return users


@router.delete("/users/{username}")
@require_role(UserRole.ADMIN)
async def delete_user(username: str, current_user: User = Depends(get_current_user)):
    """删除用户（仅管理员）"""
    if username not in MOCK_USERS_DB:
        raise HTTPException(status_code=404, detail="User not found")

    del MOCK_USERS_DB[username]

    audit_logger.log_action(
        user_id=current_user.id,
        action="DELETE_USER",
        resource="USER",
        details={"deleted_username": username},
    )

    return {"message": f"User {username} deleted"}
