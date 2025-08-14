#!/bin/sh
set -e

# 如果 hevno.json 存在，则运行插件同步
if [ -f "hevno.json" ]; then
  echo "🔌 [Entrypoint] hevno.json found. Running plugin synchronization..."
  hevno plugins sync
else
  echo "ℹ️ [Entrypoint] hevno.json not found. Skipping plugin synchronization."
fi

echo "🚀 [Entrypoint] Starting main process..."
exec "$@"