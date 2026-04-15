"""安全模块单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta

from core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    TokenData,
    UserRole,
    User,
)
from core.secrets import SecretsManager
from core.rate_limiter import IPBlacklistManager


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "secure_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 50  # bcrypt hash 长度

    def test_verify_password_correct(self):
        """测试验证正确密码"""
        password = "test_password"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试验证错误密码"""
        password = "test_password"
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        """测试相同密码生成不同哈希（因为盐值不同）"""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # 每次哈希都不同
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """JWT Token 测试"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "testuser", "role": "trader"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        data = {"sub": "testuser", "role": "trader"}
        token = create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        """测试解码有效令牌"""
        data = {"sub": "testuser", "role": "analyst"}
        token = create_access_token(data)

        token_data = decode_token(token)

        assert token_data.username == "testuser"
        assert token_data.role == "analyst"

    def test_decode_expired_token(self):
        """测试解码过期令牌"""
        data = {"sub": "testuser", "role": "viewer"}

        # 创建立即过期的令牌
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(Exception):  # JWTError 或 HTTPException
            decode_token(token)

    def test_decode_invalid_token(self):
        """测试解码无效令牌"""
        invalid_token = "invalid.token.here"

        with pytest.raises(Exception):
            decode_token(invalid_token)

    def test_token_expiration(self):
        """测试令牌过期时间"""
        data = {"sub": "testuser"}

        # 创建 5 分钟后过期的令牌
        token = create_access_token(data, expires_delta=timedelta(minutes=5))
        token_data = decode_token(token)

        assert token_data.username == "testuser"


class TestUserRole:
    """用户角色测试"""

    def test_role_hierarchy(self):
        """测试角色层级"""
        roles = [UserRole.VIEWER, UserRole.ANALYST, UserRole.TRADER, UserRole.ADMIN]

        # 确保所有角色都存在
        assert len(roles) == 4

    def test_role_values(self):
        """测试角色值"""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.TRADER.value == "trader"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.VIEWER.value == "viewer"


class TestUserModel:
    """用户模型测试"""

    def test_create_user(self):
        """测试创建用户"""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            role=UserRole.TRADER,
        )

        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.TRADER
        assert user.is_active is True


class TestSecretsManager:
    """加密管理器测试"""

    @pytest.fixture
    def secrets(self, tmp_path):
        """创建临时密钥文件的 SecretsManager"""
        key_file = tmp_path / ".test_secret.key"
        return SecretsManager(key_file=str(key_file))

    def test_encrypt_decrypt(self, secrets):
        """测试加密和解密"""
        original = "secret_password_123"
        encrypted = secrets.encrypt(original)
        decrypted = secrets.decrypt(encrypted)

        assert encrypted != original
        assert decrypted == original

    def test_encrypt_empty_string(self, secrets):
        """测试加密空字符串"""
        assert secrets.encrypt("") == ""

    def test_decrypt_empty_string(self, secrets):
        """测试解密空字符串"""
        assert secrets.decrypt("") == ""

    def test_different_encryptions_for_same_value(self, secrets):
        """测试相同值生成不同密文"""
        value = "same_value"
        encrypted1 = secrets.encrypt(value)
        encrypted2 = secrets.encrypt(value)

        assert encrypted1 != encrypted2  # Fernet 使用时间戳作为 IV
        assert secrets.decrypt(encrypted1) == value
        assert secrets.decrypt(encrypted2) == value

    def test_is_encrypted(self, secrets):
        """测试检查是否已加密"""
        encrypted = secrets.encrypt("test")
        assert secrets._is_encrypted(encrypted) is True
        assert secrets._is_encrypted("plain_text") is False


class TestIPBlacklist:
    """IP 黑名单测试"""

    @pytest.fixture
    def blacklist(self):
        """创建黑名单管理器"""
        return IPBlacklistManager()

    def test_add_to_blacklist(self, blacklist):
        """测试添加 IP 到黑名单"""
        blacklist.add_to_blacklist("192.168.1.100")
        assert blacklist.is_blocked("192.168.1.100") is True

    def test_remove_from_blacklist(self, blacklist):
        """测试从黑名单移除 IP"""
        blacklist.add_to_blacklist("192.168.1.100")
        blacklist.remove_from_blacklist("192.168.1.100")
        assert blacklist.is_blocked("192.168.1.100") is False

    def test_whitelist_override(self, blacklist):
        """测试白名单覆盖黑名单"""
        blacklist.add_to_blacklist("192.168.1.100")
        blacklist.add_to_whitelist("192.168.1.100")

        # 白名单优先
        assert blacklist.is_blocked("192.168.1.100") is False

    def test_clear_blacklist(self, blacklist):
        """测试清空黑名单"""
        blacklist.add_to_blacklist("192.168.1.100")
        blacklist.add_to_blacklist("192.168.1.101")
        blacklist.clear_blacklist()

        assert len(blacklist.get_blacklist()) == 0


class TestAuditLogger:
    """审计日志测试"""

    def test_log_action(self):
        """测试记录操作"""
        from core.auth import audit_logger

        # 应该不抛出异常
        audit_logger.log_action(
            user_id=1,
            action="LOGIN",
            resource="USER",
            details={"username": "testuser"},
            ip_address="127.0.0.1",
        )

        # 成功执行即通过测试


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
