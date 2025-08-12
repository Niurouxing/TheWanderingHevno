# Dockerfile

# --- Stage 1: Build Frontend Assets ---
# 使用一个包含 Node.js 的轻量级镜像来构建前端
FROM node:18-alpine as frontend-builder
WORKDIR /app

# 复制前端构建所需的所有文件
COPY package.json package-lock.json* ./
# 复制 vite 配置文件和前端源码
COPY vite.config.js ./
COPY frontend/ ./frontend/
# 复制所有插件，因为它们包含前端代码和 package.json
COPY plugins/ ./plugins/

# 安装所有依赖，包括工作区中的插件
RUN npm install

# 执行构建脚本，生成静态文件 (主应用和插件)
RUN npm run build
RUN npm run build:plugins


# --- Stage 2: Build Python Application ---
# 使用一个轻量的 Python 镜像作为最终应用的运行环境
FROM python:3.11-slim
WORKDIR /app

# 设置环境变量，优化 Python 在容器中的运行
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 安装 Python 依赖
COPY pyproject.toml MANIFEST.in ./
RUN pip install --no-cache-dir -e ".[dev]"

# 复制后端代码和插件的 Python 部分
COPY backend/ ./backend/
COPY assets/ ./assets/
COPY hevno.json cli.py create_demo_sandbox.py ./

# 从第一阶段复制构建好的前端静态文件和插件资源到最终镜像中
COPY --from=frontend-builder /app/dist ./dist
COPY --from=frontend-builder /app/plugins ./plugins

# 暴露 FastAPI 运行的端口
EXPOSE 8000

# 定义容器启动时运行的命令 (生产模式)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]