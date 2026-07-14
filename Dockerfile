# ─── 律答 AI 后端 Dockerfile ──────────────────────────────
# 构建: docker build -t lvda-backend .
# 运行: docker run -p 8000:8000 --env-file .env lvda-backend

FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
# 关键顺序：先装 CPU 版 torch，避免 sentence-transformers 自动拉取 CUDA 版（2GB+）
COPY requirements-server.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements-server.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 模型通过 volume 挂载本地缓存，构建时不下载
ENV HF_HUB_OFFLINE=1

# 复制源码
COPY . .

RUN mkdir -p uploads chroma_db conversations

EXPOSE 8000

CMD ["python", "run_server.py"]
