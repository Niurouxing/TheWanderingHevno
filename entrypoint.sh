#!/bin/sh
# entrypoint.sh

# 确保脚本在遇到错误时会退出
set -e

echo "🔌 [Entrypoint] Running plugin synchronization..."
# 使用 pip 安装的 hevno 命令来同步插件
hevno plugins sync

echo "🚀 [Entrypoint] Synchronization complete. Starting main process..."

# 执行传递给容器的 CMD (例如 uvicorn ...)
exec "$@"