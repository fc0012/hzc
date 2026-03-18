"""认证持久化功能单元测试"""
import pytest
import time
from auth import AuthManager
from config import settings


class TestAuthPersistence:
    """测试认证持久化功能"""

    def setup_method(self):
        """每个测试方法前初始化"""
        self.auth_manager = AuthManager()

    def test_create_persistent_session_7_days(self):
        """测试创建7天持久化会话"""
        username = "test_user"
        duration_days = 7

        token = self.auth_manager.create_persistent_session(username, duration_days)

        assert token is not None
        assert isinstance(token, str)

        # 验证令牌可以解析
        max_age = duration_days * 24 * 60 * 60
        valid, parsed_username, info = self.auth_manager.verify_session_with_info(
            token, max_age
        )

        assert valid is True
        assert parsed_username == username
        assert info["session_type"] == "persistent"
        assert info["remaining_seconds"] > 0

    def test_create_persistent_session_30_days(self):
        """测试创建30天持久化会话"""
        username = "test_user"
        duration_days = 30

        token = self.auth_manager.create_persistent_session(username, duration_days)

        assert token is not None

        # 验证令牌
        max_age = duration_days * 24 * 60 * 60
        valid, parsed_username, info = self.auth_manager.verify_session_with_info(
            token, max_age
        )

        assert valid is True
        assert parsed_username == username
        assert info["session_type"] == "persistent"

    def test_persistent_session_duration_limit(self):
        """测试持久化时长限制（超过30天被限制）"""
        username = "test_user"
        duration_days = 100  # 超过最大值

        token = self.auth_manager.create_persistent_session(username, duration_days)

        # 验证令牌使用的是最大允许天数
        max_age = settings.max_remember_me_days * 24 * 60 * 60
        valid, _, info = self.auth_manager.verify_session_with_info(token, max_age)

        assert valid is True
        assert info["session_type"] == "persistent"

    def test_get_session_max_age_regular(self):
        """测试普通会话返回86400秒"""
        max_age = self.auth_manager.get_session_max_age(remember_me=False)

        assert max_age == 86400  # 24小时

    def test_get_session_max_age_7_days(self):
        """测试7天持久化会话返回604800秒"""
        max_age = self.auth_manager.get_session_max_age(
            remember_me=True, duration_days=7
        )

        assert max_age == 604800  # 7天

    def test_get_session_max_age_30_days(self):
        """测试30天持久化会话返回2592000秒"""
        max_age = self.auth_manager.get_session_max_age(
            remember_me=True, duration_days=30
        )

        assert max_age == 2592000  # 30天

    def test_verify_session_with_info_valid(self):
        """测试有效会话返回正确信息"""
        username = "test_user"
        token = self.auth_manager.create_persistent_session(username, 7)

        max_age = 7 * 24 * 60 * 60
        valid, parsed_username, info = self.auth_manager.verify_session_with_info(
            token, max_age
        )

        assert valid is True
        assert parsed_username == username
        assert info["session_type"] == "persistent"
        assert info["remaining_seconds"] > 0
        assert info["expires_at"] is not None

    def test_verify_session_with_info_expired(self):
        """测试过期会话返回验证失败"""
        username = "test_user"
        token = self.auth_manager.create_persistent_session(username, 7)

        # 使用非常短的最大有效期来模拟过期
        max_age = 1  # 1秒
        time.sleep(2)  # 等待2秒

        valid, parsed_username, info = self.auth_manager.verify_session_with_info(
            token, max_age
        )

        assert valid is False
        assert parsed_username is None
        assert info is None

    def test_verify_session_with_info_invalid_token(self):
        """测试无效令牌返回验证失败"""
        invalid_token = "invalid_token_string"

        max_age = 7 * 24 * 60 * 60
        valid, parsed_username, info = self.auth_manager.verify_session_with_info(
            invalid_token, max_age
        )

        assert valid is False
        assert parsed_username is None
        assert info is None

    def test_create_session_includes_type(self):
        """测试普通会话令牌包含type字段"""
        username = "test_user"
        token = self.auth_manager.create_session(username)

        # 验证令牌
        max_age = 24 * 60 * 60
        valid, parsed_username, info = self.auth_manager.verify_session_with_info(
            token, max_age
        )

        assert valid is True
        assert info["session_type"] == "regular"
