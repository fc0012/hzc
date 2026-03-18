"""主应用入口"""
import asyncio
import os
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from service import MonitorService, RebuildPolicy
from auth import auth_manager
from telegram_bot import TelegramBot

# 全局实例
service: Optional[MonitorService] = None
telegram_bot: Optional[TelegramBot] = None
scheduler = AsyncIOScheduler()


async def notify_callback(message: str):
    """通知回调函数"""
    if telegram_bot and telegram_bot.is_enabled():
        await telegram_bot.send_message(message)


async def scheduled_check():
    """定时检查任务"""
    if service:
        await service.rotate_if_needed(notify_callback)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global service, telegram_bot

    # 验证配置
    settings.validate_required()

    # 创建服务实例
    service = MonitorService()

    # 启动定时任务
    scheduler.add_job(
        scheduled_check,
        "interval",
        minutes=settings.check_interval_minutes,
        id="traffic_check",
        replace_existing=True,
    )
    scheduler.start()

    # 启动Telegram机器人
    telegram_bot = TelegramBot(service)
    if telegram_bot.is_enabled():
        asyncio.create_task(telegram_bot.start())

    print("✅ Hetzner PT流量管理器已启动")
    print(f"   Web界面: http://localhost:8080")
    print(f"   安全模式: {service.get_safe_mode()}")
    print(f"   检查间隔: {settings.check_interval_minutes} 分钟")

    yield

    # 关闭
    scheduler.shutdown()
    if telegram_bot:
        await telegram_bot.stop()
    if service:
        await service.close()
    print("👋 应用已关闭")


# 创建应用
app = FastAPI(title="Hetzner PT流量管理器", lifespan=lifespan)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ========== 数据模型 ==========


class LoginRequest(BaseModel):
    """登录请求模型"""

    username: str
    password: str
    remember_me: bool = False
    duration_days: int = 7


class SessionInfo(BaseModel):
    """会话信息模型"""

    logged_in: bool
    session_type: Optional[str] = None
    remaining_seconds: Optional[int] = None
    expires_at: Optional[str] = None


# ========== 依赖 ==========

def get_session(request: Request) -> str:
    """获取会话令牌"""
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    return token


def verify_auth(token: str = Depends(get_session)) -> str:
    """验证认证"""
    valid, username = auth_manager.verify_session(token)
    if not valid:
        raise HTTPException(status_code=401, detail="会话已过期")
    return username


# ========== 页面路由 ==========

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": {}})


@app.post("/login")
async def login(request: Request):
    """登录处理"""
    data = await request.json()
    username = data.get("username", "")
    password = data.get("password", "")
    remember_me = data.get("remember_me", False)
    duration_days = data.get("duration_days", 7)

    success, message = auth_manager.verify_password(username, password)
    if success:
        # 根据是否选择"记住我"创建不同类型的会话
        if remember_me and settings.enable_remember_me:
            token = auth_manager.create_persistent_session(username, duration_days)
            session_type = "persistent"
        else:
            token = auth_manager.create_session(username)
            session_type = "regular"

        # 计算会话最大有效期
        max_age = auth_manager.get_session_max_age(remember_me, duration_days)

        # 计算过期时间
        from datetime import datetime, timedelta

        expires_at = (datetime.now() + timedelta(seconds=max_age)).isoformat()

        response = JSONResponse(
            {
                "success": True,
                "message": message,
                "session_type": session_type,
                "expires_at": expires_at,
            }
        )
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            max_age=max_age,
            samesite="lax",
        )

        # 记录审计日志
        if session_type == "persistent":
            print(
                f"📝 持久化会话创建: 用户={username}, 类型={session_type}, 天数={duration_days}"
            )

        return response
    else:
        return JSONResponse({"success": False, "message": message})


@app.post("/logout")
async def logout():
    """退出登录"""
    response = JSONResponse({"success": True})
    response.delete_cookie("session")
    return response


@app.get("/api/session/info")
async def session_info(request: Request):
    """获取会话信息"""
    token = request.cookies.get("session")

    if not token:
        return SessionInfo(logged_in=False)

    # 使用默认的最大有效期进行验证
    max_age = 30 * 24 * 60 * 60  # 30天（最大可能值）
    valid, username, info = auth_manager.verify_session_with_info(token, max_age)

    if not valid:
        return SessionInfo(logged_in=False)

    return SessionInfo(
        logged_in=True,
        session_type=info.get("session_type"),
        remaining_seconds=info.get("remaining_seconds"),
        expires_at=info.get("expires_at"),
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, token: str = Depends(get_session)):
    """首页"""
    valid, username = auth_manager.verify_session(token)
    if not valid:
        return RedirectResponse("/login")
    return templates.TemplateResponse("index.html", {"request": request})


# ========== API路由 ==========

@app.get("/api/servers")
async def api_servers(username: str = Depends(verify_auth)):
    """获取服务器列表"""
    servers = await service.collect_servers()
    return {"servers": servers}


@app.post("/api/server/{server_id}/start")
async def api_start(server_id: int, username: str = Depends(verify_auth)):
    """开机"""
    try:
        await service.power_on(server_id)
        return {"success": True, "message": "开机命令已发送"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/server/{server_id}/stop")
async def api_stop(server_id: int, username: str = Depends(verify_auth)):
    """关机"""
    try:
        await service.power_off(server_id)
        return {"success": True, "message": "关机命令已发送"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/server/{server_id}/reboot")
async def api_reboot(server_id: int, username: str = Depends(verify_auth)):
    """重启"""
    try:
        await service.reboot(server_id)
        return {"success": True, "message": "重启命令已发送"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/server/{server_id}/delete")
async def api_delete(server_id: int, username: str = Depends(verify_auth)):
    """删除服务器"""
    try:
        success = await service.delete_server(server_id)
        return {"success": success, "message": "删除成功" if success else "删除失败"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/server/{server_id}/snapshot")
async def api_snapshot(server_id: int, username: str = Depends(verify_auth)):
    """创建快照"""
    try:
        result = await service.create_snapshot(server_id)
        return {"success": True, "message": "快照创建中...", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/server/{server_id}/ps")
async def api_ps(server_id: int, username: str = Depends(verify_auth)):
    """查看进程状态"""
    processes = await service.check_processes(server_id)
    return {"processes": processes}


@app.get("/api/snapshots")
async def api_snapshots(username: str = Depends(verify_auth)):
    """获取快照列表"""
    snapshots = await service.list_snapshots()
    return {"snapshots": snapshots}


@app.delete("/api/snapshot/{image_id}")
async def api_delete_snapshot(image_id: int, username: str = Depends(verify_auth)):
    """删除快照"""
    success = await service.delete_snapshot(image_id)
    return {"success": success, "message": "删除成功" if success else "删除失败"}


@app.get("/api/policies")
async def api_policies(username: str = Depends(verify_auth)):
    """获取重建策略列表"""
    policies = service.load_policies()
    return {"policies": [p.model_dump() for p in policies]}


class PolicyRequest(BaseModel):
    enabled: bool = False
    threshold: float = 0.98
    image_id: str = ""
    server_type: str = ""
    keep_ip: bool = True


@app.put("/api/policy/{server_id}")
async def api_policy(
    server_id: int, req: PolicyRequest, username: str = Depends(verify_auth)
):
    """配置重建策略"""
    policy = RebuildPolicy(
        server_id=server_id,
        enabled=req.enabled,
        threshold=req.threshold,
        image_id=req.image_id,
        server_type=req.server_type,
        keep_ip=req.keep_ip,
    )
    service.save_policy(policy)
    return {"success": True, "message": "策略已保存"}


@app.get("/api/safe_mode")
async def api_safe_mode_get(username: str = Depends(verify_auth)):
    """获取安全模式状态"""
    return {"safe_mode": service.get_safe_mode()}


@app.put("/api/safe_mode")
async def api_safe_mode_set(request: Request, username: str = Depends(verify_auth)):
    """设置安全模式"""
    data = await request.json()
    enabled = data.get("safe_mode", not service.get_safe_mode())
    service.set_safe_mode(enabled)
    return {"success": True, "safe_mode": enabled}


# ========== 主入口 ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
