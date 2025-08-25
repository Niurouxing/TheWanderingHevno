# backend.Dockerfile

FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

#在同一层 RUN 中安装 git 和 curl
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY cli.py .
COPY backend/ backend/
COPY plugins/ plugins/

RUN pip install --no-cache-dir -e ".[dev]"

COPY entrypoint.sh .
RUN chmod +x ./entrypoint.sh

WORKDIR /app
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "4399", "--reload"]