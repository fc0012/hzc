"""
HZC - Hetzner流量保护面板 错误类型定义
"""


class HzcError(Exception):
    """HZC基础异常"""
    pass


class HetznerApiError(HzcError):
    """Hetzner API错误"""
    def __init__(self, message: str, status_code: int | None = None, detail: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class ValidationError(HzcError):
    """参数验证错误"""
    def __init__(self, message: str, field: str | None = None, suggestion: str | None = None):
        self.message = message
        self.field = field
        self.suggestion = suggestion
        super().__init__(message)


class IpOperationError(HzcError):
    """IP操作错误"""
    def __init__(self, message: str, ip_id: int | None = None, operation: str | None = None):
        self.message = message
        self.ip_id = ip_id
        self.operation = operation
        super().__init__(message)


class ServerOperationError(HzcError):
    """服务器操作错误"""
    def __init__(self, message: str, server_id: int | None = None, operation: str | None = None):
        self.message = message
        self.server_id = server_id
        self.operation = operation
        super().__init__(message)


class SnapshotError(HzcError):
    """快照操作错误"""
    def __init__(self, message: str, snapshot_id: int | None = None, operation: str | None = None):
        self.message = message
        self.snapshot_id = snapshot_id
        self.operation = operation
        super().__init__(message)
