# ─── 后端 Dockerfile ────────────────────────────────────
# 构建: docker build -t lvda-backend .
# 运行: docker run -p 8000:8000 --env-file .env lvda-backend

FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（先 COPY requirements 利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 预下载多语言嵌入模型（约 470MB，构建时下载一次，启动不需联网）
ENV HF_HUB_OFFLINE=1
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# 复制源码
COPY . .

# 运行时需要的目录
RUN mkdir -p uploads chroma_db conversations

EXPOSE 8000

# 启动
CMD ["python", "run_server.py"]
