#!/bin/sh
set -e

# --- .env 文件处理 ---
HOST_ENV_FILE="/app/.env.host" # 这是从宿主机挂载进来的临时文件/目录
APP_ENV_FILE="/app/.env"      # 这是我们最终要给应用程序使用的文件

# 检查临时挂载点是否是一个真实的文件
if [ -f "$HOST_ENV_FILE" ]; then
  # 如果是，说明用户提供了 .env，我们把它复制到最终位置
  echo "📝 [Entrypoint] Found host .env file. Copying to $APP_ENV_FILE"
  cp "$HOST_ENV_FILE" "$APP_ENV_FILE"
else
  # 如果不是文件（不存在或是一个目录），我们就创建一个空的 .env 文件
  # 这样可以保证 /app/.env 永远是一个文件
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