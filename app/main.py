"""AI知识库问答系统 —— FastAPI 主入口"""
import logging
import os
import time
from typing import List

from fastapi import FastAPI, File, Request, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models.schemas import (
    DocumentUploadResponse,
    DocumentInfo,
    DocumentListResponse,
    QueryRequest,
    QueryResponse,
    ConversationInfo,
    ConversationListResponse,
    ConversationDetail,
    DeleteDocumentResponse,
)
from app.services.document_service import DocumentService, SUPPORTED_EXTENSIONS
from app.services.vector_service import VectorService
from app.services.llm_service import LLMService
from app.services.conversation_service import ConversationService
from app.services.seed_service import SeedService

# ── 日志配置 ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("lvda")

app = FastAPI(title="律答 AI - 智能法律咨询助手", version="1.1.0")

# CORS — 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务（全局单例）
doc_service = DocumentService(upload_dir="uploads")
vec_service = VectorService(persist_dir="chroma_db")
llm_service = LLMService()
conv_service = ConversationService(data_dir="conversations")
BUILTIN_DIR = "builtin_docs"

logger.info("律答 AI 启动完成, LLM就绪=%s, 向量库块数=%d", llm_service.is_ready(), vec_service.count())


@app.on_event("startup")
async def seed_builtin_docs():
    """启动时自动索引内置文档目录中的新文档"""
    seed = SeedService(BUILTIN_DIR, doc_service, vec_service)
    seed.seed()


# ── 简单速率限制中间件 ──────────────────────────────
# 按 IP 限流：每分钟最多 30 次请求
_rate_limits: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # 秒
RATE_LIMIT_MAX = 30


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # 清理过期记录
    if client_ip in _rate_limits:
        _rate_limits[client_ip] = [
            t for t in _rate_limits[client_ip] if now - t < RATE_LIMIT_WINDOW
        ]

    _rate_limits.setdefault(client_ip, [])

    if len(_rate_limits[client_ip]) >= RATE_LIMIT_MAX:
        logger.warning("速率限制触发: IP=%s", client_ip)
        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试"},
        )

    _rate_limits[client_ip].append(now)
    logger.info("请求: %s %s (IP=%s)", request.method, request.url.path, client_ip)
    response = await call_next(request)
    return response


@staticmethod
def _safe_filename(filename: str) -> str:
    """清洗文件名，防止路径遍历攻击"""
    name = os.path.basename(filename)
    # 移除空字节和路径分隔符
    name = name.replace("\0", "").replace("/", "_").replace("\\", "_")
    if not name or name.startswith("."):
        raise ValueError("无效的文件名")
    return name


@app.get("/")
def root():
    return {
        "message": "律答 AI - 智能法律咨询助手",
        "llm_ready": llm_service.is_ready(),
    }


@app.get("/health")
def health():
    convs = conv_service.list_all()
    return {
        "status": "ok",
        "chunks_stored": vec_service.count(),
        "llm_ready": llm_service.is_ready(),
        "conversations": len(convs),
    }


# ==================== 文档上传接口 ====================

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB


@app.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """上传文档，解析、分块并存入向量数据库"""
    # 0. 安全：清洗文件名
    try:
        safe_name = _safe_filename(file.filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文件名")

    # 1. 校验文件类型
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"不支持的文件格式，支持：{allowed}")

    # 2. 去重检查（含内置文档）
    existing = vec_service.get_all_sources()
    if safe_name in existing:
        raise HTTPException(status_code=409, detail=f"文档 '{safe_name}' 已存在，请勿重复上传")
    builtin_path = os.path.join(BUILTIN_DIR, safe_name)
    if os.path.exists(builtin_path):
        raise HTTPException(status_code=409, detail=f"与内置文档 '{safe_name}' 同名，无法上传")

    # 3. 分块读取并校验大小
    file_path = os.path.join(doc_service.upload_dir, safe_name)
    total_size = 0
    try:
        with open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE:
                    raise ValueError(f"文件过大，最大支持 {MAX_UPLOAD_SIZE // 1024 // 1024}MB")
                f.write(chunk)
    except ValueError:
        # 大小超限，清理文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=413,
            detail=f"文件过大，最大支持 {MAX_UPLOAD_SIZE // 1024 // 1024}MB",
        )

    # 4. 解析文档 + 文本分块
    try:
        chunks = doc_service.process_file(file_path, safe_name)
    except Exception as e:
        logger.error("文档解析失败: %s, 错误: %s", safe_name, str(e))
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"文档解析失败: {str(e)}")

    if not chunks:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="文档无可提取的文字内容")

    # 5. 存入向量数据库
    count = vec_service.add_documents(chunks)
    logger.info("文档入库完成: %s, 共 %d 个文本块", safe_name, count)

    return DocumentUploadResponse(
        filename=safe_name,
        chunks_count=count,
        message=f"文档解析完成，共 {count} 个文本块已入库",
    )


# ==================== 文档列表接口 ====================

@app.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """列出所有文档（含内置文档和上传文档）"""
    sources = vec_service.get_all_sources_with_type()
    documents: List[DocumentInfo] = []
    for item in sources:
        source = item["source"]
        doc_id = os.path.splitext(source)[0]
        documents.append(
            DocumentInfo(
                id=doc_id,
                filename=source,
                source=source,
                source_type=item["source_type"],
            )
        )
    return DocumentListResponse(documents=documents, total=len(documents))


@app.get("/documents/{filename}/content")
async def get_document_content(filename: str):
    """获取文档的完整文本内容（支持上传文档和内置文档）"""
    # 安全：清洗文件名
    safe_name = _safe_filename(filename)

    # 先查上传目录，再查内置文档目录
    file_path = os.path.join(doc_service.upload_dir, safe_name)
    if not os.path.exists(file_path):
        file_path = os.path.join(BUILTIN_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文档不存在")
    try:
        text = doc_service.parse_file(file_path, safe_name)
        return {"filename": safe_name, "content": text, "length": len(text)}
    except Exception as e:
        logger.error("文档读取失败: %s, 错误: %s", safe_name, str(e))
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")


# ==================== 文档删除接口 ====================

@app.delete("/documents/{filename}", response_model=DeleteDocumentResponse)
async def delete_document(filename: str):
    """删除指定文档及其在向量库中的所有分块（禁止删除内置文档）"""
    safe_name = _safe_filename(filename)

    # 检查是否为内置文档
    builtin_path = os.path.join(BUILTIN_DIR, safe_name)
    if os.path.exists(builtin_path):
        raise HTTPException(status_code=403, detail="内置文档不可删除，请从 builtin_docs/ 目录移除后重启服务")

    # 删除向量库中的分块
    deleted_chunks = vec_service.delete_by_source(safe_name)

    # 删除上传文件
    file_path = os.path.join(doc_service.upload_dir, safe_name)
    if os.path.exists(file_path):
        os.remove(file_path)

    logger.info("文档已删除: %s, 共移除 %d 个文本块", safe_name, deleted_chunks)
    return DeleteDocumentResponse(
        filename=safe_name,
        deleted_chunks=deleted_chunks,
        message=f"文档 '{safe_name}' 已删除，共移除 {deleted_chunks} 个文本块",
    )


# ==================== 问答接口（RAG + 多轮对话）====================

# 向量检索相似度阈值：欧氏距离超过此值的文档视为不相关
SIMILARITY_THRESHOLD = 1.5


@app.post("/query", response_model=QueryResponse)
async def query_knowledge(request: QueryRequest):
    """RAG 问答：检索知识库 → 查对话历史 → LLM 生成回答"""
    if vec_service.count() == 0:
        raise HTTPException(status_code=400, detail="知识库为空，请先上传文档")

    # 0. 对话管理：没有 ID → 新建；有 ID → 加载历史
    conversation_id = request.conversation_id
    if not conversation_id:
        conv = conv_service.create()
        conversation_id = conv.id
    elif not conv_service.get(conversation_id):
        raise HTTPException(status_code=404, detail=f"对话不存在: {conversation_id}")

    # 1. 初检：用嵌入向量召回 top-20 作为重排候选池
    RETRIEVAL_POOL = 20
    result = vec_service.query(request.question, top_k=RETRIEVAL_POOL)
    documents = result["documents"]
    metadatas = result["metadatas"]
    distances = result["distances"]

    # 1a. LLM 精排：从候选池中挑出最相关的 top_k 个
    if llm_service.is_ready() and len(documents) > request.top_k:
        reranked_idx = llm_service.rerank(request.question, documents, request.top_k)
        documents = [documents[i] for i in reranked_idx]
        metadatas = [metadatas[i] for i in reranked_idx]
        distances = [distances[i] for i in reranked_idx]
        logger.info(
            "精排完成: %d → %d, 索引=%s",
            len(result["documents"]), len(documents), reranked_idx,
        )

    # 1b. 相似度阈值过滤：距离超过阈值的视为不相关
    if distances:
        filtered = [
            (doc, meta, dist)
            for doc, meta, dist in zip(documents, metadatas, distances)
            if dist < SIMILARITY_THRESHOLD
        ]
        if filtered:
            documents = [f[0] for f in filtered]
            metadatas = [f[1] for f in filtered]
            logger.info("检索结果: %d 条, 过滤后 %d 条 (阈值=%.2f)", len(distances), len(filtered), SIMILARITY_THRESHOLD)
        else:
            documents = []
            metadatas = []

    if not documents:
        return QueryResponse(
            question=request.question,
            answer="未找到相关内容，建议尝试换个问法或上传相关法律文件。",
            sources=[],
            conversation_id=conversation_id,
        )

    # 2. 列出来源文件
    sources = list(set(m["source"] for m in metadatas if m))

    # 3. 加载对话历史（最近 10 轮）
    history = conv_service.get_messages(conversation_id, limit=10)
    history_dicts = [{"role": h.role, "content": h.content} for h in history]

    # 4. LLM 生成回答
    if llm_service.is_ready():
        try:
            answer = llm_service.generate_answer(request.question, documents, history_dicts)
        except Exception as e:
            logger.error("LLM 调用失败: %s", str(e))
            answer = f"⚠️ AI 回答生成失败，请稍后重试。\n\n错误信息: {str(e)}"
    else:
        answer = "⚠️ 请配置 DeepSeek API Key 以启用 AI 回答\n\n" + "\n\n---\n\n".join(documents)

    # 5. 保存本轮对话
    conv_service.add_message(conversation_id, "user", request.question)
    conv_service.add_message(conversation_id, "assistant", answer, sources)

    return QueryResponse(
        question=request.question,
        answer=answer,
        sources=sources,
        conversation_id=conversation_id,
    )


# ==================== 对话管理接口 ====================

@app.post("/conversations", response_model=ConversationDetail)
async def create_conversation():
    """创建新对话"""
    return conv_service.create()


@app.get("/conversations", response_model=ConversationListResponse)
async def list_conversations():
    """获取所有对话列表"""
    convs = conv_service.list_all()
    return ConversationListResponse(conversations=convs, total=len(convs))


@app.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """获取某个对话的完整内容"""
    conv = conv_service.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conv


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    ok = conv_service.delete(conversation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"ok": True}
