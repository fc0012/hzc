import httpx


class QBClient:
    def __init__(self, url: str, username: str, password: str):
        self.url = (url or "").rstrip("/")
        self.username = username
        self.password = password

    @property
    def enabled(self):
        return bool(self.url and self.username and self.password)

    async def stats(self):
        if not self.enabled:
            return {"enabled": False}

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            # login
            r = await c.post(f"{self.url}/api/v2/auth/login", data={"username": self.username, "password": self.password})
            r.raise_for_status()

            info = await c.get(f"{self.url}/api/v2/transfer/info")
            info.raise_for_status()
            transfer = info.json()

            md = await c.get(f"{self.url}/api/v2/sync/maindata")
            md.raise_for_status()
            maindata = md.json()

        torrents = maindata.get("torrents", {})
        active = 0
        for t in torrents.values():
            if t.get("state") not in {"pausedUP", "pausedDL"}:
                active += 1

        return {
            "enabled": True,
            "dl_speed": transfer.get("dl_info_speed", 0),
            "up_speed": transfer.get("up_info_speed", 0),
            "dl_total": transfer.get("dl_info_data", 0),
            "up_total": transfer.get("up_info_data", 0),
            "all_torrents": len(torrents),
            "active_torrents": active,
            "dht_nodes": transfer.get("dht_nodes", 0),
            "connection_status": transfer.get("connection_status", "unknown"),
        }
