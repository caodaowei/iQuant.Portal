"""敏感数据加密管理"""
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from loguru import logger


class SecretsManager:
    """敏感数据加密管理器

    使用 Fernet 对称加密算法加密敏感配置（数据库密码、API Token 等）

    Usage:
        secrets = SecretsManager()

        # 加密
        encrypted = secrets.encrypt("my_secret_password")

        # 解密
        decrypted = secrets.decrypt(encrypted)
    """

    def __init__(self, key_file: str = ".secret.key"):
        """初始化加密管理器

        Args:
            key_file: 密钥文件路径
        """
        self.key_file = Path(key_file)

        # 加载或生成密钥
        self.key = self._load_or_generate_key()
        self.fernet = Fernet(self.key)

    def _load_or_generate_key(self) -> bytes:
        """加载或生成加密密钥

        Returns:
            Fernet 密钥（32字节）
        """
        if self.key_file.exists():
            # 加载现有密钥
            with open(self.key_file, 'rb') as f:
                key = f.read()
            logger.info(f"已加载加密密钥: {self.key_file}")
            return key
        else:
            # 生成新密钥
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)

            # 设置文件权限（仅所有者可读写）
            os.chmod(self.key_file, 0o600)

            logger.warning(f"已生成新加密密钥: {self.key_file}")
            logger.warning("⚠️  请妥善保管此密钥文件，丢失后将无法解密数据")
            return key

    def encrypt(self, value: str) -> str:
        """加密字符串

        Args:
            value: 要加密的明文

        Returns:
            加密后的字符串（Base64 编码）
        """
        if not value:
            return ""

        encrypted_bytes = self.fernet.encrypt(value.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    def decrypt(self, encrypted_value: str) -> str:
        """解密字符串

        Args:
            encrypted_value: 要解密的密文

        Returns:
            解密后的明文

        Raises:
            cryptography.fernet.InvalidToken: 密钥错误或数据损坏
        """
        if not encrypted_value:
            return ""

        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_value.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise

    def encrypt_env_file(self, env_file: str = "config/.env", output_file: str = "config/.env.encrypted"):
        """加密 .env 文件

        Args:
            env_file: 原始 .env 文件路径
            output_file: 加密后文件路径
        """
        env_path = Path(env_file)
        if not env_path.exists():
            logger.error(f".env 文件不存在: {env_file}")
            return

        # 读取所有行
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 加密敏感字段
        sensitive_keys = [
            'DB_PASSWORD',
            'REDIS_PASSWORD',
            'TUSHARE_TOKEN',
            'SECRET_KEY',
            'API_KEY',
            'PRIVATE_KEY',
        ]

        encrypted_lines = []
        for line in lines:
            line = line.strip()

            # 跳过注释和空行
            if not line or line.startswith('#'):
                encrypted_lines.append(line)
                continue

            # 检查是否是敏感字段
            is_sensitive = any(line.startswith(key) for key in sensitive_keys)

            if is_sensitive and '=' in line:
                key, value = line.split('=', 1)
                if value:  # 只加密非空值
                    encrypted_value = self.encrypt(value)
                    encrypted_lines.append(f"{key}={encrypted_value}")
                    logger.info(f"已加密: {key}")
                else:
                    encrypted_lines.append(line)
            else:
                encrypted_lines.append(line)

        # 写入加密文件
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(encrypted_lines))

        logger.info(f"加密文件已保存: {output_file}")
        logger.warning("⚠️  请安全删除原始 .env 文件: rm config/.env")

    def decrypt_env_file(self, encrypted_file: str = "config/.env.encrypted", output_file: str = "config/.env"):
        """解密 .env 文件

        Args:
            encrypted_file: 加密文件路径
            output_file: 解密后文件路径
        """
        encrypted_path = Path(encrypted_file)
        if not encrypted_path.exists():
            logger.error(f"加密文件不存在: {encrypted_file}")
            return

        # 读取所有行
        with open(encrypted_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 解密所有加密的值
        decrypted_lines = []
        for line in lines:
            line = line.strip()

            # 跳过注释和空行
            if not line or line.startswith('#'):
                decrypted_lines.append(line)
                continue

            # 尝试解密
            if '=' in line:
                key, value = line.split('=', 1)
                if value and self._is_encrypted(value):
                    try:
                        decrypted_value = self.decrypt(value)
                        decrypted_lines.append(f"{key}={decrypted_value}")
                    except Exception as e:
                        logger.warning(f"解密失败 {key}: {e}，保留原值")
                        decrypted_lines.append(line)
                else:
                    decrypted_lines.append(line)
            else:
                decrypted_lines.append(line)

        # 写入解密文件
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(decrypted_lines))

        logger.info(f"解密文件已保存: {output_file}")

    def _is_encrypted(self, value: str) -> bool:
        """检查值是否已加密

        Args:
            value: 要检查的值

        Returns:
            是否已加密
        """
        # Fernet token 通常以 gAAAAA 开头
        return value.startswith('gAAAAA') or len(value) > 100


# 全局实例
secrets_manager = SecretsManager()


def get_secrets_manager() -> SecretsManager:
    """获取 SecretsManager 单例"""
    return secrets_manager
