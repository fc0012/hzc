"""核心业务服务层"""
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from hetzner_client import HetznerClient
from ssh_client import SSHClient
from config import settings

BYTES_IN_TB = 1024**4
DATA_DIR = "data"

# 机房位置中文名称映射
LOCATION_NAMES = {
    "fsn1": "德国-纽伦堡",
    "nbg1": "德国-纽伦堡",
    "hel1": "芬兰-赫尔辛基",
    "ash": "美国-阿什本",
    "sin": "新加坡",
}


class RebuildPolicy(BaseModel):
    """自动重建策略"""
    server_id: int
    enabled: bool = False
    threshold: float = 0.98
    image_id: str = ""
    server_type: str = ""
    keep_ip: bool = True


class MonitorService:
    """监控服务"""

    def __init__(self):
        self.client = HetznerClient(settings.hetzner_token)
        self.ssh = SSHClient(settings.ssh_user, settings.ssh_port)
        self._safe_mode = settings.safe_mode
        self._shutdown_done: set[int] = set()  # 已执行关机的服务器ID
        self._rebuild_done: set[int] = set()  # 已执行重建的服务器ID
        self._alert_sent: set[int] = set()  # 已发送告警的服务器ID

        # 确保数据目录存在
        os.makedirs(DATA_DIR, exist_ok=True)

    async def close(self):
        """关闭客户端"""
        await self.client.close()

    # ========== 流量监控 ==========

    async def collect_servers(self) -> List[Dict]:
        """收集所有服务器状态"""
        servers = await self.client.list_servers()
        result = []

        for s in servers:
            # 计算流量使用
            outgoing = int(s.get("outgoing_traffic") or 0)
            included = int(s.get("included_traffic") or 0)

            used_tb = outgoing / BYTES_IN_TB
            included_tb = included / BYTES_IN_TB if included > 0 else settings.traffic_limit_tb

            if included_tb == 0:
                included_tb = settings.traffic_limit_tb

            usage_percent = (used_tb / included_tb * 100) if included_tb > 0 else 0

            # 获取公网IP
            public_net = s.get("public_net", {})
            ipv4 = public_net.get("ipv4", {})
            public_ip = ipv4.get("ip", "")

            # 获取机房位置
            location = s.get("datacenter", {}).get("location", {}).get("name", "")
            location_cn = LOCATION_NAMES.get(location, location)

            result.append({
                "id": s["id"],
                "name": s["name"],
                "status": s["status"],
                "public_ip": public_ip,
                "used_traffic_tb": round(used_tb, 2),
                "included_traffic_tb": round(included_tb, 2),
                "usage_percent": round(usage_percent, 1),
                "server_type": s.get("server_type", {}).get("name", ""),
                "location": location,
                "location_cn": location_cn,
            })

        return result

    # ========== 服务器操作 ==========

    async def power_on(self, server_id: int) -> Dict:
        """开机"""
        return await self.client.server_action(server_id, "poweron")

    async def power_off(self, server_id: int) -> Dict:
        """关机"""
        return await self.client.server_action(server_id, "poweroff")

    async def reboot(self, server_id: int) -> Dict:
        """重启"""
        return await self.client.server_action(server_id, "reboot")

    async def delete_server(self, server_id: int) -> bool:
        """删除服务器"""
        # 先关机
        try:
            await self.power_off(server_id)
            await asyncio.sleep(3)
        except Exception:
            pass

        return await self.client.delete_server(server_id)

    # ========== 自动重建 ==========

    async def rebuild_server(self, server_id: int, image_id: str, keep_ip: bool = True) -> Dict:
        """重建服务器（保留IP）"""
        # 获取原服务器信息
        server = await self.client.get_server(server_id)
        if not server:
            raise ValueError(f"服务器 {server_id} 不存在")

        server_name = server["name"]
        server_type = server["server_type"]["name"]
        location = server["datacenter"]["location"]["name"]

        # 获取公网IP信息
        public_net = server.get("public_net", {})
        ipv4 = public_net.get("ipv4", {})
        ipv4_id = ipv4.get("id")

        if keep_ip and ipv4_id:
            # 禁止IP自动删除
            await self.client.update_primary_ip(ipv4_id, auto_delete=False)

        # 删除旧服务器
        await self.client.delete_server(server_id)
        await asyncio.sleep(2)

        # 创建新服务器
        create_params = {
            "name": server_name,
            "server_type": server_type,
            "image": image_id,
            "location": location,
        }

        if keep_ip and ipv4_id:
            create_params["public_net"] = {
                "ipv4": ipv4_id,
                "enable_ipv4": True,
                "enable_ipv6": False,
            }

        result = await self.client.create_server(**create_params)
        return result

    # ========== 快照管理 ==========

    async def create_snapshot(self, server_id: int, description: str = None) -> Dict:
        """创建快照"""
        return await self.client.create_snapshot(server_id, description)

    async def list_snapshots(self) -> List[Dict]:
        """获取快照列表"""
        snapshots = await self.client.list_snapshots()
        result = []
        for s in snapshots:
            result.append({
                "id": s["id"],
                "name": s.get("name") or s.get("description", ""),
                "size_gb": round(s.get("image_size", 0) / 1024, 2),
                "created_at": s.get("created", ""),
                "server_id": s.get("created_from", {}).get("id"),
            })
        return result

    async def delete_snapshot(self, image_id: int) -> bool:
        """删除快照"""
        return await self.client.delete_snapshot(image_id)

    # ========== 进程监控 ==========

    async def check_processes(self, server_id: int) -> List[Dict]:
        """检查服务器进程状态"""
        server = await self.client.get_server(server_id)
        if not server:
            return []

        if server["status"] != "running":
            return []

        public_net = server.get("public_net", {})
        ipv4 = public_net.get("ipv4", {})
        host = ipv4.get("ip", "")

        if not host:
            return []

        if not settings.monitor_processes:
            return []

        return self.ssh.check_processes(host, settings.monitor_processes)

    # ========== 策略管理 ==========

    def _policy_file(self) -> str:
        return os.path.join(DATA_DIR, "policies.json")

    def load_policies(self) -> List[RebuildPolicy]:
        """加载重建策略"""
        filepath = self._policy_file()
        if not os.path.exists(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [RebuildPolicy(**p) for p in data]

    def save_policy(self, policy: RebuildPolicy) -> None:
        """保存重建策略"""
        policies = self.load_policies()

        # 更新或添加
        found = False
        for i, p in enumerate(policies):
            if p.server_id == policy.server_id:
                policies[i] = policy
                found = True
                break

        if not found:
            policies.append(policy)

        with open(self._policy_file(), "w", encoding="utf-8") as f:
            json.dump([p.model_dump() for p in policies], f, indent=2)

    def get_policy(self, server_id: int) -> Optional[RebuildPolicy]:
        """获取指定服务器的策略"""
        policies = self.load_policies()
        for p in policies:
            if p.server_id == server_id:
                return p
        return None

    # ========== 安全模式 ==========

    def _safe_mode_file(self) -> str:
        return os.path.join(DATA_DIR, "safe_mode.json")

    def get_safe_mode(self) -> bool:
        """获取安全模式状态"""
        filepath = self._safe_mode_file()
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                return data.get("safe_mode", settings.safe_mode)
        return settings.safe_mode

    def set_safe_mode(self, enabled: bool) -> None:
        """设置安全模式"""
        self._safe_mode = enabled
        with open(self._safe_mode_file(), "w") as f:
            json.dump({"safe_mode": enabled}, f)

    # ========== 定时检查 ==========

    async def rotate_if_needed(self, notify_callback=None) -> None:
        """检查流量并执行自动操作"""
        servers = await self.collect_servers()
        safe_mode = self.get_safe_mode()
        policies = self.load_policies()

        for server in servers:
            server_id = server["id"]
            usage_percent = server["usage_percent"]
            policy = self.get_policy(server_id)

            # 检查是否需要重建
            if policy and policy.enabled:
                threshold = policy.threshold * 100
                if usage_percent >= threshold and server_id not in self._rebuild_done:
                    if not safe_mode:
                        try:
                            await self.rebuild_server(
                                server_id, policy.image_id, policy.keep_ip
                            )
                            self._rebuild_done.add(server_id)
                            if notify_callback:
                                await notify_callback(
                                    f"🔄 服务器 {server['name']} 已自动重建"
                                )
                        except Exception as e:
                            if notify_callback:
                                await notify_callback(
                                    f"❌ 服务器 {server['name']} 重建失败: {e}"
                                )
                    else:
                        if notify_callback and server_id not in self._alert_sent:
                            await notify_callback(
                                f"⚠️ 服务器 {server['name']} 流量已达 {usage_percent}%，"
                                f"建议手动重建（安全模式已开启）"
                            )
                            self._alert_sent.add(server_id)
            else:
                # 未配置重建策略，执行关机保护
                if usage_percent >= 100 and server_id not in self._shutdown_done:
                    if not safe_mode:
                        try:
                            await self.power_off(server_id)
                            self._shutdown_done.add(server_id)
                            if notify_callback:
                                await notify_callback(
                                    f"🛑 服务器 {server['name']} 流量已满，已自动关机"
                                )
                        except Exception as e:
                            if notify_callback:
                                await notify_callback(
                                    f"❌ 服务器 {server['name']} 关机失败: {e}"
                                )
                    else:
                        if notify_callback and server_id not in self._alert_sent:
                            await notify_callback(
                                f"⚠️ 服务器 {server['name']} 流量已达 {usage_percent}%，"
                                f"建议手动关机（安全模式已开启）"
                            )
                            self._alert_sent.add(server_id)

                # 预警通知（95%）
                elif usage_percent >= 95 and server_id not in self._alert_sent:
                    if notify_callback:
                        await notify_callback(
                            f"⚠️ 服务器 {server['name']} 流量已达 {usage_percent}%，请注意"
                        )
                        self._alert_sent.add(server_id)
