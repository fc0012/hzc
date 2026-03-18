"""Web认证模块"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from config import settings

DATA_DIR = "data"
PASSWORD_FILE = os.path.join(DATA_DIR, "password.hash")
LOCK_FILE = os.path.join(DATA_DIR, "lock.json")

# 会话有效期（秒）
SESSION_MAX_AGE = 24 * 60 * 60  # 24小时
# 登录失败锁定阈值
MAX_LOGIN_ATTEMPTS = 5
# 锁定时间（秒）
LOCK_DURATION = 30 * 60  # 30分钟


class AuthManager:
    """认证管理器"""

    def __init__(self):
        self.serializer = URLSafeTimedSerializer(settings.secret_key, salt="auth")
        os.makedirs(DATA_DIR, exist_ok=True)
        self._init_password()

    def _init_password(self):
        """初始化密码文件"""
        if not os.path.exists(PASSWORD_FILE):
            # 首次运行，创建密码哈希
            password_hash = bcrypt.hashpw(
                settings.web_password.encode("utf-8"), bcrypt.gensalt()
            )
            with open(PASSWORD_FILE, "wb") as f:
                f.write(password_hash)

    def _get_password_hash(self) -> bytes:
        """获取存储的密码哈希"""
        with open(PASSWORD_FILE, "rb") as f:
            return f.read()

    def _get_lock_info(self) -> dict:
        """获取锁定信息"""
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, "r") as f:
                return json.load(f)
        return {"attempts": 0, "locked_until": None}

    def _save_lock_info(self, info: dict):
        """保存锁定信息"""
        with open(LOCK_FILE, "w") as f:
            json.dump(info, f)

    def is_locked(self) -> tuple[bool, int]:
        """检查是否被锁定"""
        info = self._get_lock_info()
        if info.get("locked_until"):
            locked_until = datetime.fromisoformat(info["locked_until"])
            if datetime.now() < locked_until:
                remaining = int((locked_until - datetime.now()).total_seconds())
                return True, remaining
            else:
                # 锁定已过期，重置
                self._save_lock_info({"attempts": 0, "locked_until": None})
        return False, 0

    def verify_password(self, username: str, password: str) -> tuple[bool, str]:
        """
        验证登录

        返回: (success, message)
        """
        # 检查用户名
        if username != settings.web_username:
            return False, "用户名或密码错误"

        # 检查锁定
        locked, remaining = self.is_locked()
        if locked:
            return False, f"账号已锁定，请 {remaining // 60} 分钟后重试"

        # 验证密码
        password_hash = self._get_password_hash()
        if bcrypt.checkpw(password.encode("utf-8"), password_hash):
            # 登录成功，重置锁定信息
            self._save_lock_info({"attempts": 0, "locked_until": None})
            return True, "登录成功"
        else:
            # 登录失败，增加失败次数
            info = self._get_lock_info()
            info["attempts"] = info.get("attempts", 0) + 1

            if info["attempts"] >= MAX_LOGIN_ATTEMPTS:
                # 锁定账号
                locked_until = datetime.now() + timedelta(seconds=LOCK_DURATION)
                info["locked_until"] = locked_until.isoformat()
                self._save_lock_info(info)
                return False, f"密码错误次数过多，账号已锁定 {LOCK_DURATION // 60} 分钟"
            else:
                self._save_lock_info(info)
                remaining_attempts = MAX_LOGIN_ATTEMPTS - info["attempts"]
                return False, f"密码错误，还剩 {remaining_attempts} 次尝试"

    def create_session(self, username: str) -> str:
        """创建普通会话令牌"""
        return self.serializer.dumps(
            {"username": username, "time": time.time(), "type": "regular"}
        )

    def create_persistent_session(self, username: str, duration_days: int) -> str:
        """
        创建持久化会话令牌

        Args:
            username: 用户名
            duration_days: 持久化天数

        Returns:
            签名后的令牌字符串
        """
        # 限制持久化时长不超过配置的最大值
        max_days = settings.max_remember_me_days
        actual_days = min(duration_days, max_days)

        return self.serializer.dumps(
            {
                "username": username,
                "time": time.time(),
                "type": "persistent",
                "duration_days": actual_days,
            }
        )

    def get_session_max_age(self, remember_me: bool = False, duration_days: int = 7) -> int:
        """
        获取会话最大有效期（秒）

        Args:
            remember_me: 是否启用持久化会话
            duration_days: 持久化天数

        Returns:
            会话最大有效期（秒）
        """
        if remember_me and settings.enable_remember_me:
            # 限制不超过配置的最大天数
            actual_days = min(duration_days, settings.max_remember_me_days)
            return actual_days * 24 * 60 * 60
        else:
            return SESSION_MAX_AGE

    def verify_session_with_info(
        self, token: str, max_age: int
    ) -> tuple[bool, Optional[str], Optional[dict]]:
        """
        验证会话令牌并返回详细信息

        Args:
            token: 会话令牌
            max_age: 最大有效期（秒）

        Returns:
            (valid, username, info) - 验证结果、用户名、会话信息
        """
        try:
            data = self.serializer.loads(token, max_age=max_age)
            username = data.get("username")
            session_type = data.get("type", "regular")
            session_time = data.get("time", 0)

            # 计算剩余有效期
            elapsed = time.time() - session_time
            remaining = max(0, max_age - elapsed)
            expires_at = datetime.fromtimestamp(session_time + max_age).isoformat()

            info = {
                "session_type": session_type,
                "remaining_seconds": int(remaining),
                "expires_at": expires_at,
            }

            return True, username, info
        except (BadSignature, SignatureExpired):
            return False, None, None

    def verify_session(self, token: str) -> tuple[bool, Optional[str]]:
        """
        验证会话令牌

        返回: (valid, username)
        """
        try:
            data = self.serializer.loads(token, max_age=SESSION_MAX_AGE)
            return True, data.get("username")
        except (BadSignature, SignatureExpired):
            return False, None

    def change_password(self, old_password: str, new_password: str) -> tuple[bool, str]:
        """修改密码"""
        # 验证旧密码
        password_hash = self._get_password_hash()
        if not bcrypt.checkpw(old_password.encode("utf-8"), password_hash):
            return False, "旧密码错误"

        # 设置新密码
        new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        with open(PASSWORD_FILE, "wb") as f:
            f.write(new_hash)

        return True, "密码修改成功"


# 全局认证管理器
auth_manager = AuthManager()
