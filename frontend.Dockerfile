# frontend.Dockerfile (已修正)

FROM node:22-slim
WORKDIR /app

# 1. 复制所有 package.json 文件，包括 workspaces 中的
COPY package.json package-lock.json ./
COPY plugins/ ./plugins/

# 2. 现在执行 npm install，它能正确识别 workspaces 并安装所有依赖
RUN npm install

# 3. 复制剩余的前端代码（可选，但有助于缓存）。
#    由于你使用了卷挂载，这一步主要在构建镜像时起作用。
COPY frontend/ ./frontend/
COPY index.html .
COPY vite.config.js .

# 4. 启动开发服务器
CMD ["npm", "run", "dev"]