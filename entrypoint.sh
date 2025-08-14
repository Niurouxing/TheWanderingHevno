#!/bin/sh
set -e

HOST_ENV_FILE="/app/.env.host"
APP_ENV_FILE="/app/.env"

if [ -f "$HOST_ENV_FILE" ]; then
  echo "📝 [Entrypoint] Found host .env file. Copying to $APP_ENV_FILE"
  cp "$HOST_ENV_FILE" "$APP_ENV_FILE"
else
  echo "📝 [Entrypoint] Host .env not found. Creating empty $APP_ENV_FILE"
  touch "$APP_ENV_FILE"
fi


# --- .env 处理结束，下面的代码保持不变 ---

# 如果 hevno.json 存在，则运行插件同步
if [ -f "hevno.json" ]; then
  echo "🔌 [Entrypoint] hevno.json found. Running plugin synchronization..."
  hevno plugins sync
else
  echo "ℹ️ [Entrypoint] hevno.json not found. Skipping plugin synchronization."
fi

echo "🚀 [Entrypoint] Starting main process..."
# 执行 CMD 命令 (uvicorn ...)，此时 /app/.env 文件已经准备就绪
exec "$@"