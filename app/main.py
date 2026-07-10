"""AI知识库问答系统 —— FastAPI 主入口"""
import os
import shutil
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
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
)
from app.services.document_service import DocumentService, SUPPORTED_EXTENSIONS
from app.services.vector_service import VectorService
from app.services.llm_service import LLMService
from app.services.conversation_service import ConversationService

app = FastAPI(title="律答 AI - 智能法律咨询助手", version="1.0.0")

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
    """上传 PDF 文档，解析、分块并存入向量数据库"""
    # 1. 校验文件类型
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"不支持的文件格式，支持：{allowed}")

    # 2. 分块读取并校验大小
    file_path = os.path.join(doc_service.upload_dir, file.filename)
    total_size = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            total_size += len(chunk)
            if total_size > MAX_UPLOAD_SIZE:
                f.close()
                os.remove(file_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"文件过大，最大支持 {MAX_UPLOAD_SIZE // 1024 // 1024}MB",
                )
            f.write(chunk)

    # 3. 解析文档 + 文本分块
    chunks = doc_service.process_file(file_path, file.filename)

    if not chunks:
        # 清理空文件
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="文档无可提取的文字内容")

    # 4. 存入向量数据库
    count = vec_service.add_documents(chunks)

    return DocumentUploadResponse(
        filename=file.filename,
        chunks_count=count,
        message=f"文档解析完成，共 {count} 个文本块已入库",
    )


# ==================== 文档列表接口 ====================

@app.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """列出已上传的所有文档"""
    sources = vec_service.get_all_sources()
    documents: List[DocumentInfo] = []
    for source in sources:
        documents.append(
            DocumentInfo(
                id=source.replace(".pdf", ""),
                filename=source,
                source=source,
            )
        )
    return DocumentListResponse(documents=documents, total=len(documents))


@app.get("/documents/{filename}/content")
async def get_document_content(filename: str):
    """获取已上传文档的完整文本内容"""
    file_path = os.path.join(doc_service.upload_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文档不存在")
    try:
        text = doc_service.parse_file(file_path, filename)
        return {"filename": filename, "content": text, "length": len(text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")


# ==================== 问答接口（RAG + 多轮对话）====================

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

    # 1. 检索相关文档片段
    result = vec_service.query(request.question, top_k=request.top_k)
    documents = result["documents"]
    metadatas = result["metadatas"]

    if not documents:
        return QueryResponse(
            question=request.question,
            answer="未找到相关内容",
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
        answer = llm_service.generate_answer(request.question, documents, history_dicts)
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
