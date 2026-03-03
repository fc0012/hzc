#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "[x] docker 未安装，请先安装 Docker。"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[x] docker compose 不可用，请先安装 Docker Compose 插件。"
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
fi

ask() {
  local key="$1" prompt="$2" secret="${3:-0}"
  local cur
  cur=$(grep -E "^${key}=" .env | head -n1 | cut -d'=' -f2- || true)
  if [ "$secret" = "1" ]; then
    read -r -s -p "$prompt${cur:+ [已存在]}: " val
    echo
  else
    read -r -p "$prompt${cur:+ [${cur}]}: " val
  fi
  if [ -n "${val:-}" ]; then
    sed -i "s#^${key}=.*#${key}=${val}#" .env
  fi
}

echo "== Hetzner Traffic Guard 一键初始化 =="
echo "提示：只填 Hetzner Token 也能跑，其余可回车跳过。"

ask "HETZNER_TOKEN" "请输入 Hetzner API Token(必填)" 1
if [ -z "$(grep -E '^HETZNER_TOKEN=' .env | head -n1 | cut -d'=' -f2-)" ]; then
  echo "[x] HETZNER_TOKEN 不能为空"
  exit 1
fi

ask "TELEGRAM_BOT_TOKEN" "Telegram Bot Token(可留空)" 1
ask "TELEGRAM_CHAT_ID" "Telegram Chat ID(可留空)"
ask "ROTATE_THRESHOLD" "触发阈值(推荐0.98，默认0.98)"
ask "CHECK_INTERVAL_MINUTES" "检测间隔分钟(默认5)"
ask "SAFE_MODE" "安全模式(默认true，true=只告警不自动删机)"

# 小白安全默认值
sed -i 's#^TRAFFIC_LIMIT_TB=.*#TRAFFIC_LIMIT_TB=20#' .env
if ! grep -q '^ROTATE_THRESHOLD=' .env; then echo 'ROTATE_THRESHOLD=0.98' >> .env; fi
if ! grep -q '^CHECK_INTERVAL_MINUTES=' .env; then echo 'CHECK_INTERVAL_MINUTES=5' >> .env; fi
if ! grep -q '^SAFE_MODE=' .env; then echo 'SAFE_MODE=true' >> .env; fi

echo "[i] 启动中..."
docker compose up -d --build

echo "[ok] 已启动"
echo "访问: http://$(hostname -I | awk '{print $1}'):1227"
echo "配置文件: $(pwd)/.env"
echo "查看详细教程：README.md"
