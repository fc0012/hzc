"""Hetzner Cloud API客户端"""
import asyncio
from typing import Dict, List, Any, Optional
import httpx

BASE_URL = "https://api.hetzner.cloud/v1"
BYTES_IN_TB = 1024**4


class HetznerClient:
    """Hetzner Cloud API客户端"""

    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

    async def _request(
        self, method: str, path: str, **kwargs
    ) -> Dict[str, Any]:
        """发送API请求"""
        url = f"{BASE_URL}{path}"
        for attempt in range(3):
            try:
                resp = await self.client.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise ValueError("Hetzner API认证失败，请检查Token")
                if attempt == 2:
                    raise
                await asyncio.sleep(1)
            except httpx.RequestError:
                if attempt == 2:
                    raise
                await asyncio.sleep(1)
        return {}

    # 服务器操作
    async def list_servers(self) -> List[Dict]:
        """获取服务器列表"""
        data = await self._request("GET", "/servers")
        return data.get("servers", [])

    async def get_server(self, server_id: int) -> Dict:
        """获取服务器详情"""
        data = await self._request("GET", f"/servers/{server_id}")
        return data.get("server", {})

    async def server_action(self, server_id: int, action: str) -> Dict:
        """执行服务器操作（poweron/poweroff/reboot）"""
        data = await self._request(
            "POST", f"/servers/{server_id}/actions/{action}"
        )
        return data

    async def delete_server(self, server_id: int) -> bool:
        """删除服务器"""
        try:
            await self._request("DELETE", f"/servers/{server_id}")
            return True
        except Exception:
            return False

    async def create_server(
        self,
        name: str,
        server_type: str,
        image: str,
        location: str = None,
        ssh_keys: List[int] = None,
        networks: List[int] = None,
        public_net: Dict = None,
    ) -> Dict:
        """创建服务器"""
        payload = {
            "name": name,
            "server_type": server_type,
            "image": image,
        }
        if location:
            payload["location"] = location
        if ssh_keys:
            payload["ssh_keys"] = ssh_keys
        if networks:
            payload["networks"] = networks
        if public_net:
            payload["public_net"] = public_net

        data = await self._request("POST", "/servers", json=payload)
        return data

    # 流量监控
    async def get_server_metrics(
        self, server_id: int, start: str, end: str, step: int = 3600
    ) -> Dict:
        """获取服务器流量指标"""
        params = {
            "type": "network",
            "start": start,
            "end": end,
            "step": str(step),
        }
        data = await self._request(
            "GET", f"/servers/{server_id}/metrics", params=params
        )
        return data.get("metrics", {})

    # 快照操作
    async def list_snapshots(self) -> List[Dict]:
        """获取快照列表"""
        data = await self._request("GET", "/images", params={"type": "snapshot"})
        return data.get("images", [])

    async def create_snapshot(
        self, server_id: int, description: str = None, type: str = "snapshot"
    ) -> Dict:
        """创建快照"""
        payload = {"type": type}
        if description:
            payload["description"] = description
        data = await self._request(
            "POST", f"/servers/{server_id}/actions/create_image", json=payload
        )
        return data

    async def delete_snapshot(self, image_id: int) -> bool:
        """删除快照"""
        try:
            await self._request("DELETE", f"/images/{image_id}")
            return True
        except Exception:
            return False

    # IP操作
    async def list_primary_ips(self) -> List[Dict]:
        """获取主IP列表"""
        data = await self._request("GET", "/primary_ips")
        return data.get("primary_ips", [])

    async def unassign_primary_ip(self, ip_id: int) -> Dict:
        """解绑主IP"""
        data = await self._request(
            "POST", f"/primary_ips/{ip_id}/actions/unassign"
        )
        return data

    async def update_primary_ip(self, ip_id: int, auto_delete: bool = False) -> Dict:
        """更新主IP设置"""
        data = await self._request(
            "PUT", f"/primary_ips/{ip_id}", json={"auto_delete": auto_delete}
        )
        return data

    # 辅助方法
    async def list_server_types(self) -> List[Dict]:
        """获取服务器类型列表"""
        data = await self._request("GET", "/server_types")
        return data.get("server_types", [])

    async def list_locations(self) -> List[Dict]:
        """获取机房位置列表"""
        data = await self._request("GET", "/locations")
        return data.get("locations", [])

    async def list_images(self) -> List[Dict]:
        """获取镜像列表"""
        data = await self._request("GET", "/images")
        return data.get("images", [])
