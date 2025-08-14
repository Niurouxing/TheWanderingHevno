# frontend.Dockerfile
FROM node:22-slim
WORKDIR /app

COPY package.json package-lock.json ./
COPY plugins/ ./plugins/

RUN npm install

COPY frontend/ ./frontend/
COPY index.html .
COPY vite.config.js .

CMD ["npm", "run", "dev"]