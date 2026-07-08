"""AI知识库问答系统 —— FastAPI 主入口"""
import os
import shutil
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.models.schemas import (
    DocumentUploadResponse,
    DocumentInfo,
    DocumentListResponse,
    QueryRequest,
    QueryResponse,
)
from app.services.document_service import DocumentService
from app.services.vector_service import VectorService
from app.services.llm_service import LLMService

app = FastAPI(title="AI知识库问答系统", version="0.3.0")

# 初始化服务（全局单例）
doc_service = DocumentService(upload_dir="uploads")
vec_service = VectorService(persist_dir="chroma_db")
llm_service = LLMService()


@app.get("/")
def root():
    return {
        "message": "AI知识库问答系统",
        "llm_ready": llm_service.is_ready(),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "chunks_stored": vec_service.count(),
        "llm_ready": llm_service.is_ready(),
    }


# ==================== 文档上传接口 ====================

@app.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """上传 PDF 文档，解析、分块并存入向量数据库"""
    # 1. 校验文件类型
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    # 2. 保存到本地
    file_path = os.path.join(doc_service.upload_dir, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 3. 解析 PDF + 文本分块
    chunks = doc_service.process_pdf(file_path, file.filename)

    if not chunks:
        # 清理空文件
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="PDF 无可提取的文字内容")

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


# ==================== 问答接口（RAG 全链路）====================

@app.post("/query", response_model=QueryResponse)
async def query_knowledge(request: QueryRequest):
    """RAG 问答：检索知识库 → LLM 生成回答"""
    if vec_service.count() == 0:
        raise HTTPException(status_code=400, detail="知识库为空，请先上传文档")

    # 1. 检索相关文档片段
    result = vec_service.query(request.question, top_k=request.top_k)
    documents = result["documents"]
    metadatas = result["metadatas"]

    if not documents:
        return QueryResponse(
            question=request.question,
            answer="未找到相关内容",
            sources=[],
        )

    # 2. 列出来源文件（去重）
    sources = list(set(m["source"] for m in metadatas if m))

    # 3. 用 LLM 基于检索结果生成回答
    if llm_service.is_ready():
        answer = llm_service.generate_answer(request.question, documents)
    else:
        # 未配置 API Key，退回为直接返回文档片段
        answer = "⚠️ 请配置 DeepSeek API Key 以启用 AI 回答\n\n" + "\n\n---\n\n".join(documents)

    return QueryResponse(
        question=request.question,
        answer=answer,
        sources=sources,
    )
