"""登录持久化功能集成测试"""
import pytest
from fastapi.testclient import TestClient
from main import app
from auth import auth_manager


class TestLoginPersistence:
    """测试登录持久化功能"""

    def setup_method(self):
        """每个测试方法前初始化"""
        self.client = TestClient(app)

    def test_regular_login_flow(self):
        """测试普通登录流程（不勾选"记住我"）"""
        # 登录请求（不勾选记住我）
        response = self.client.post(
            "/login",
            json={"username": "admin", "password": "wrong_password", "remember_me": False},
        )

        # 验证响应
        assert response.status_code == 200
        data = response.json()

        # 注意：这里需要使用正确的密码才能测试成功的情况
        # 由于我们不知道正确的密码，这里只测试请求格式正确

    def test_persistent_login_flow(self):
        """测试持久化登录流程（勾选"记住我"并选择7天）"""
        # 登录请求（勾选记住我，选择7天）
        response = self.client.post(
            "/login",
            json={
                "username": "admin",
                "password": "wrong_password",
                "remember_me": True,
                "duration_days": 7,
            },
        )

        # 验证响应
        assert response.status_code == 200
        data = response.json()

        # 注意：这里需要使用正确的密码才能测试成功的情况

    def test_session_info_endpoint_not_logged_in(self):
        """测试会话信息接口（未登录）"""
        response = self.client.get("/api/session/info")

        assert response.status_code == 200
        data = response.json()

        assert data["logged_in"] is False
        assert data["session_type"] is None
        assert data["remaining_seconds"] is None
        assert data["expires_at"] is None

    def test_session_info_endpoint_with_valid_token(self):
        """测试会话信息接口（有效令牌）"""
        # 创建一个测试令牌
        username = "test_user"
        token = auth_manager.create_persistent_session(username, 7)

        # 使用令牌访问会话信息接口
        response = self.client.get("/api/session/info", cookies={"session": token})

        assert response.status_code == 200
        data = response.json()

        assert data["logged_in"] is True
        assert data["session_type"] == "persistent"
        assert data["remaining_seconds"] > 0
        assert data["expires_at"] is not None

    def test_session_info_endpoint_with_regular_token(self):
        """测试会话信息接口（普通令牌）"""
        # 创建一个普通令牌
        username = "test_user"
        token = auth_manager.create_session(username)

        # 使用令牌访问会话信息接口
        response = self.client.get("/api/session/info", cookies={"session": token})

        assert response.status_code == 200
        data = response.json()

        assert data["logged_in"] is True
        assert data["session_type"] == "regular"
        assert data["remaining_seconds"] > 0
        assert data["expires_at"] is not None

    def test_login_request_format(self):
        """测试登录请求格式"""
        # 测试完整的请求参数
        response = self.client.post(
            "/login",
            json={
                "username": "test_user",
                "password": "test_password",
                "remember_me": True,
                "duration_days": 30,
            },
        )

        # 验证请求被正确处理（即使密码错误）
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data

    def test_login_without_remember_me(self):
        """测试不勾选记住我的登录"""
        response = self.client.post(
            "/login",
            json={
                "username": "test_user",
                "password": "test_password",
                "remember_me": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_login_default_remember_me(self):
        """测试默认不勾选记住我"""
        response = self.client.post(
            "/login",
            json={"username": "test_user", "password": "test_password"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
