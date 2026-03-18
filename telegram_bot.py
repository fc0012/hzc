"""Telegram机器人模块"""
import asyncio
from typing import Optional, Callable
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

from config import settings
from service import MonitorService


class TelegramBot:
    """Telegram机器人"""

    def __init__(self, service: MonitorService):
        self.service = service
        self.bot: Optional[Bot] = None
        self.app: Optional[Application] = None
        self.chat_id = settings.telegram_chat_id
        self._notify_callback: Optional[Callable] = None

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return bool(settings.telegram_bot_token and self.chat_id)

    def _check_chat_id(self, update: Update) -> bool:
        """检查ChatID白名单"""
        chat_id = str(update.effective_chat.id)
        if chat_id != self.chat_id:
            update.message.reply_text("❌ 无权限访问")
            return False
        return True

    async def send_message(self, text: str):
        """发送消息"""
        if not self.is_enabled():
            return
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            print(f"Telegram发送消息失败: {e}")

    async def send_alert(self, text: str):
        """发送告警"""
        await self.send_message(f"⚠️ {text}")

    # ========== 命令处理器 ==========

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start - 显示帮助"""
        if not self._check_chat_id(update):
            return

        help_text = """
🤖 Hetzner PT流量管理器

可用命令:
/servers - 查看服务器列表
/start {id} - 开机
/stop {id} - 关机
/reboot {id} - 重启
/delete {id} - 删除服务器
/snapshot {id} - 创建快照
/snapshots - 查看快照列表
/ps {id} - 查看进程状态
/policy {id} {image_id} - 配置重建策略
/safe_on - 开启安全模式
/safe_off - 关闭安全模式
/help - 显示帮助
"""
        await update.message.reply_text(help_text)

    async def cmd_servers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/servers - 查看服务器列表"""
        if not self._check_chat_id(update):
            return

        servers = await self.service.collect_servers()
        if not servers:
            await update.message.reply_text("暂无服务器")
            return

        lines = ["🖥️ 服务器列表:\n"]
        for s in servers:
            status_emoji = {"running": "🟢", "off": "⚪", "error": "🔴"}.get(
                s["status"], "❓"
            )
            lines.append(
                f"{status_emoji} [{s['id']}] {s['name']}\n"
                f"   状态: {s['status']}\n"
                f"   IP: {s['public_ip'] or '-'}\n"
                f"   流量: {s['usage_percent']}% ({s['used_traffic_tb']}/{s['included_traffic_tb']} TB)\n"
            )

        await update.message.reply_text("\n".join(lines))

    async def cmd_power_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start {id} - 开机"""
        if not self._check_chat_id(update):
            return

        try:
            server_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("用法: /start {服务器ID}")
            return

        try:
            await self.service.power_on(server_id)
            await update.message.reply_text(f"✅ 服务器 {server_id} 开机命令已发送")
        except Exception as e:
            await update.message.reply_text(f"❌ 开机失败: {e}")

    async def cmd_power_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/stop {id} - 关机"""
        if not self._check_chat_id(update):
            return

        try:
            server_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("用法: /stop {服务器ID}")
            return

        try:
            await self.service.power_off(server_id)
            await update.message.reply_text(f"✅ 服务器 {server_id} 关机命令已发送")
        except Exception as e:
            await update.message.reply_text(f"❌ 关机失败: {e}")

    async def cmd_reboot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/reboot {id} - 重启"""
        if not self._check_chat_id(update):
            return

        try:
            server_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("用法: /reboot {服务器ID}")
            return

        try:
            await self.service.reboot(server_id)
            await update.message.reply_text(f"✅ 服务器 {server_id} 重启命令已发送")
        except Exception as e:
            await update.message.reply_text(f"❌ 重启失败: {e}")

    async def cmd_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/delete {id} - 删除服务器"""
        if not self._check_chat_id(update):
            return

        try:
            server_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("用法: /delete {服务器ID}")
            return

        # 确认删除
        await update.message.reply_text(
            f"⚠️ 确定要删除服务器 {server_id} 吗？\n"
            f"请回复 /confirm_delete {server_id} 确认"
        )

    async def cmd_confirm_delete(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """/confirm_delete {id} - 确认删除"""
        if not self._check_chat_id(update):
            return

        try:
            server_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("用法: /confirm_delete {服务器ID}")
            return

        try:
            success = await self.service.delete_server(server_id)
            if success:
                await update.message.reply_text(f"✅ 服务器 {server_id} 已删除")
            else:
                await update.message.reply_text(f"❌ 删除失败")
        except Exception as e:
            await update.message.reply_text(f"❌ 删除失败: {e}")

    async def cmd_snapshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/snapshot {id} - 创建快照"""
        if not self._check_chat_id(update):
            return

        try:
            server_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("用法: /snapshot {服务器ID}")
            return

        try:
            result = await self.service.create_snapshot(server_id)
            await update.message.reply_text(
                f"✅ 服务器 {server_id} 快照创建中..."
            )
        except Exception as e:
            await update.message.reply_text(f"❌ 创建快照失败: {e}")

    async def cmd_snapshots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/snapshots - 查看快照列表"""
        if not self._check_chat_id(update):
            return

        snapshots = await self.service.list_snapshots()
        if not snapshots:
            await update.message.reply_text("暂无快照")
            return

        lines = ["📸 快照列表:\n"]
        for s in snapshots:
            lines.append(
                f"[{s['id']}] {s['name'] or '未命名'}\n"
                f"   大小: {s['size_gb']} GB\n"
                f"   创建时间: {s['created_at'] or '-'}\n"
            )

        await update.message.reply_text("\n".join(lines))

    async def cmd_ps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/ps {id} - 查看进程状态"""
        if not self._check_chat_id(update):
            return

        try:
            server_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("用法: /ps {服务器ID}")
            return

        processes = await self.service.check_processes(server_id)
        if not processes:
            await update.message.reply_text("无监控进程或无法获取")
            return

        lines = [f"📊 服务器 {server_id} 进程状态:\n"]
        for p in processes:
            status = "✅ 运行中" if p["is_running"] else "❌ 未运行"
            pid_info = f" (PID: {p['pid']})" if p["pid"] else ""
            lines.append(f"{p['name']}: {status}{pid_info}")

        await update.message.reply_text("\n".join(lines))

    async def cmd_policy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/policy {id} {image_id} - 配置重建策略"""
        if not self._check_chat_id(update):
            return

        try:
            server_id = int(context.args[0])
            image_id = context.args[1]
        except (IndexError, ValueError):
            await update.message.reply_text("用法: /policy {服务器ID} {镜像ID}")
            return

        from service import RebuildPolicy

        policy = RebuildPolicy(server_id=server_id, enabled=True, image_id=image_id)
        self.service.save_policy(policy)
        await update.message.reply_text(
            f"✅ 已为服务器 {server_id} 配置自动重建策略\n"
            f"   镜像ID: {image_id}\n"
            f"   阈值: 98%"
        )

    async def cmd_safe_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/safe_on - 开启安全模式"""
        if not self._check_chat_id(update):
            return

        self.service.set_safe_mode(True)
        await update.message.reply_text("✅ 安全模式已开启（只告警不执行）")

    async def cmd_safe_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/safe_off - 关闭安全模式"""
        if not self._check_chat_id(update):
            return

        self.service.set_safe_mode(False)
        await update.message.reply_text("✅ 安全模式已关闭")

    # ========== 启动 ==========

    async def start(self):
        """启动机器人"""
        if not self.is_enabled():
            print("Telegram机器人未配置，跳过启动")
            return

        self.app = Application.builder().token(settings.telegram_bot_token).build()
        self.bot = self.app.bot

        # 注册命令处理器
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_start))
        self.app.add_handler(CommandHandler("servers", self.cmd_servers))
        self.app.add_handler(CommandHandler("stop", self.cmd_power_off))
        self.app.add_handler(CommandHandler("reboot", self.cmd_reboot))
        self.app.add_handler(CommandHandler("delete", self.cmd_delete))
        self.app.add_handler(CommandHandler("confirm_delete", self.cmd_confirm_delete))
        self.app.add_handler(CommandHandler("snapshot", self.cmd_snapshot))
        self.app.add_handler(CommandHandler("snapshots", self.cmd_snapshots))
        self.app.add_handler(CommandHandler("ps", self.cmd_ps))
        self.app.add_handler(CommandHandler("policy", self.cmd_policy))
        self.app.add_handler(CommandHandler("safe_on", self.cmd_safe_on))
        self.app.add_handler(CommandHandler("safe_off", self.cmd_safe_off))

        # 初始化
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        print(f"✅ Telegram机器人已启动 (ChatID: {self.chat_id})")

    async def stop(self):
        """停止机器人"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
