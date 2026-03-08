# HZC - Hetzner 流量保护

面向 Hetzner 用户的流量监控 + 安全自动化工具。  
目标：**简单、稳妥、可回滚**。

---

## 快速开始（3步）

### 1) 拉取项目

```bash
git clone https://github.com/liqiba/hzc.git
cd hzc
```

### 2) 一键安装

```bash
chmod +x scripts/onekey.sh
./scripts/onekey.sh
```

> 只需先填写 `HETZNER_TOKEN`，其他可先默认。

### 3) 打开面板

```text
http://你的服务器IP:1227
```

---

## 一键升级（推荐）

```bash
cd hzc
./scripts/upgrade.sh
```

说明（当前逻辑）：
- 自动拉取 `origin/main`
- 本地代码与远端一致时：提示“已是最新版本”，不重复升级
- 有新版本时：自动同步代码并重建容器
- 升级后自动做健康检查（`/api/ping`）

---

## 默认安全策略

默认参数：
- `SAFE_MODE=true`（只告警，不自动删机）
- `ROTATE_THRESHOLD=0.98`
- `CHECK_INTERVAL_MINUTES=5`

适合先观察再放开自动化，降低误操作风险。

---

## 常用环境变量

必填：
- `HETZNER_TOKEN`

常用：
- `TRAFFIC_LIMIT_TB`（默认20）
- `ROTATE_THRESHOLD`（默认0.98）
- `CHECK_INTERVAL_MINUTES`（默认5）
- `SAFE_MODE`（默认true）

Telegram（可选）：
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

qB（可选）：
- `QB_URL`
- `QB_USERNAME`
- `QB_PASSWORD`

---

## 功能概览

- 服务器状态/流量可视化
- 每日流量统计
- 快照管理（创建/删除/重命名）
- 手动重建、自动策略重建
- Telegram 按钮与命令（版本、升级、状态）

---

## 常见问题（简版）

### 1) 页面显示异常或旧样式
先强刷浏览器（Ctrl/Cmd + Shift + R）。

### 2) 升级后版本没变化
先看 TG 的“升级日志”与 `/version`，确认是否已同步到最新提交。

### 3) 升级失败
优先执行：
```bash
cd hzc
./scripts/upgrade.sh
```
并查看日志：
```bash
docker logs -f hetzner-traffic-guard
```

---

## 免责声明

关闭 `SAFE_MODE` 后，自动化动作可能涉及重建与删除。  
请先在测试环境验证，再用于生产环境。
