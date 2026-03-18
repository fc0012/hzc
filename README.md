# Hetzner PT流量管理器

一个轻量级的 Hetzner 云服务器流量管理工具，用于在刷 PT 时自动控制服务器开关机，防止超出流量限制。

## 功能特性

- 🔄 **流量监控** - 周期性检查服务器流量使用情况
- 🛑 **自动关机** - 流量达到阈值时自动关机保护
- 🔁 **自动重建** - 支持自动重建服务器重置流量（保留IP）
- 📸 **快照管理** - 创建、查看、删除服务器快照
- 📊 **进程监控** - 查看服务器关键进程运行状态
- 🤖 **Telegram机器人** - 通过Telegram远程控制
- 🌐 **Web管理界面** - 简洁的Web界面（账号认证）
- 🔒 **安全模式** - 只告警不执行，适合测试
- 🔑 **登录持久化** - 支持"记住我"功能，避免频繁登录

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

必填配置：
- `HETZNER_TOKEN` - Hetzner API Token
- `WEB_PASSWORD` - Web登录密码
- `SECRET_KEY` - 会话加密密钥（随机字符串）

可选配置：
- `TELEGRAM_BOT_TOKEN` - Telegram机器人Token
- `TELEGRAM_CHAT_ID` - 接收通知的ChatID

### 2. 运行

#### Docker方式（推荐）

```bash
docker-compose up -d
```

#### 直接运行

```bash
pip install -r requirements.txt
python main.py
```

### 3. 访问

- Web界面: http://localhost:8080
- 默认用户名: admin

## Telegram命令

| 命令 | 说明 |
|------|------|
| `/servers` | 查看服务器列表 |
| `/start {id}` | 开机 |
| `/stop {id}` | 关机 |
| `/reboot {id}` | 重启 |
| `/delete {id}` | 删除服务器 |
| `/snapshot {id}` | 创建快照 |
| `/snapshots` | 查看快照列表 |
| `/ps {id}` | 查看进程状态 |
| `/policy {id} {image_id}` | 配置自动重建策略 |
| `/safe_on` | 开启安全模式 |
| `/safe_off` | 关闭安全模式 |

## 配置说明

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| Hetzner Token | HETZNER_TOKEN | 必填 | Hetzner API Token |
| 流量阈值 | TRAFFIC_LIMIT_TB | 20 | 月流量上限(TB) |
| 重建阈值 | ROTATE_THRESHOLD | 0.98 | 自动重建触发比例 |
| 检查间隔 | CHECK_INTERVAL_MINUTES | 5 | 检查间隔(分钟) |
| 安全模式 | SAFE_MODE | true | 只告警不执行 |
| Telegram Token | TELEGRAM_BOT_TOKEN | 可选 | Telegram机器人Token |
| Telegram ChatID | TELEGRAM_CHAT_ID | 可选 | 接收通知的ChatID |
| Web用户名 | WEB_USERNAME | admin | Web登录用户名 |
| Web密码 | WEB_PASSWORD | 必填 | Web登录密码 |
| 会话密钥 | SECRET_KEY | 必填 | 会话加密密钥 |
| 启用记住我 | ENABLE_REMEMBER_ME | true | 是否启用"记住我"功能 |
| 记住我天数 | REMEMBER_ME_DAYS | 7 | 默认持久化天数 |
| 最大记住我天数 | MAX_REMEMBER_ME_DAYS | 30 | 最大持久化天数上限 |
| 监控进程 | MONITOR_PROCESSES | 可选 | 需监控的进程名列表 |

## 登录持久化功能

### 功能说明

系统支持"记住我"功能，允许用户在登录时选择保持登录状态，避免频繁重复登录。

### 使用方法

1. 在登录页面输入用户名和密码
2. 勾选"记住我（保持登录状态）"复选框
3. 选择保持登录时长（7天或30天）
4. 点击登录按钮

### 配置选项

- `ENABLE_REMEMBER_ME` - 是否启用"记住我"功能（默认：true）
- `REMEMBER_ME_DAYS` - 默认持久化天数（默认：7）
- `MAX_REMEMBER_ME_DAYS` - 最大持久化天数上限（默认：30）

### 安全说明

- 持久化会话使用加密令牌存储在浏览器Cookie中
- 最长有效期为30天，可通过配置调整
- 建议在公共设备上不要使用"记住我"功能

## 项目结构

```
hetzner_pt/
├── main.py              # 应用入口
├── config.py            # 配置管理
├── service.py           # 核心业务逻辑
├── hetzner_client.py    # Hetzner API客户端
├── telegram_bot.py      # Telegram机器人
├── ssh_client.py        # SSH客户端
├── auth.py              # Web认证模块
├── templates/           # HTML模板
├── static/              # 静态资源
├── requirements.txt     # 依赖列表
├── Dockerfile           # Docker构建文件
└── docker-compose.yml   # Docker编排配置
```

## 许可证

MIT License
