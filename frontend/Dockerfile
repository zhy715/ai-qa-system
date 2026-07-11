# ─── 前端 Dockerfile（多阶段构建）─────────────────────────
# 构建: cd frontend && docker build -t lvda-frontend .
# 运行: docker run -p 80:80 lvda-frontend

# Stage 1: 构建 React 应用
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖（利用 Docker 缓存）
COPY package.json package-lock.json ./
RUN npm ci

# 复制源码并构建
COPY . .
RUN npm run build

# Stage 2: nginx 服务
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx 配置：SPA 路由回退 + API 代理
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    \
    location /api/ { \
        proxy_pass http://backend:8000/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
