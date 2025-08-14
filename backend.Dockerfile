# backend.Dockerfile

FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# 1. 安装 git 用于插件同步
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 2. 复制项目结构和依赖定义文件
COPY pyproject.toml .
COPY cli.py .
COPY backend/ backend/
COPY plugins/ plugins/

# 3. 安装 Python 依赖
#    使用 -e ".[dev]" 进行可编辑安装，这样卷挂载的源码更改才能生效
RUN pip install --no-cache-dir -e ".[dev]"

# 4. 复制入口脚本并赋予权限
COPY entrypoint.sh .
RUN chmod +x ./entrypoint.sh

# 5. 设置工作目录 (保持不变)
WORKDIR /app

ENTRYPOINT ["./entrypoint.sh"]
# 默认命令现在是 uvicorn 的热重载模式
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]