# Hetzner Traffic Guard

一个 Docker 化项目：监控 Hetzner 每台 VPS 当月外网出流量，接近阈值时自动快照+重建+删除旧机；并提供 Web 面板与 Telegram 通知。

## 功能
- 每 `CHECK_INTERVAL_MINUTES` 分钟检测流量
- 超阈值（`ROTATE_THRESHOLD`）自动轮换服务器
- Web 面板展示每台机器流量占比，支持手动重建
- Telegram 通知轮换结果

## 快速开始
```bash
git clone <your-repo-url>
cd hetzner-traffic-guard
cp .env.example .env
# 编辑 .env 填写 HETZNER_TOKEN 等

docker compose up -d --build
```

访问：`http://<server-ip>:1227`

## 关键环境变量
- `HETZNER_TOKEN`: Hetzner Cloud API Token
- `TRAFFIC_LIMIT_TB`: 套餐月流量（默认20）
- `ROTATE_THRESHOLD`: 触发阈值（默认0.9）
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`: Telegram 通知

## GitHub 发布
```bash
git init
git add .
git commit -m "init hetzner traffic guard"
git branch -M main
git remote add origin git@github.com:<you>/<repo>.git
git push -u origin main
```

## 注意
- 自动重建会删除旧机，务必先在测试项目验证。
- 建议先将 `ROTATE_THRESHOLD` 调高到 `0.98` 做灰度。
