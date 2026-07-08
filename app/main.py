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

app = FastAPI(title="AI知识库问答系统", version="0.2.0")

# 初始化服务（全局单例）
doc_service = DocumentService(upload_dir="uploads")
vec_service = VectorService(persist_dir="chroma_db")


@app.get("/")
def root():
    return {"message": "AI知识库问答系统"}


@app.get("/health")
def health():
    return {"status": "ok", "chunks_stored": vec_service.count()}


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


# ==================== 问答接口（向量检索）====================

@app.post("/query", response_model=QueryResponse)
async def query_knowledge(request: QueryRequest):
    """根据问题检索知识库，返回相关文档片段"""
    if vec_service.count() == 0:
        raise HTTPException(status_code=400, detail="知识库为空，请先上传文档")

    result = vec_service.query(request.question, top_k=request.top_k)

    # 拼接检索到的文档作为"答案"
    documents = result["documents"]
    metadatas = result["metadatas"]

    if not documents or not documents[0]:
        return QueryResponse(
            question=request.question,
            answer="未找到相关内容",
            sources=[],
        )

    # 列出来源文件（去重）
    sources = list(set(m["source"] for m in metadatas if m))

    # 拼接多个相关片段作为答案上下文
    context = "\n\n---\n\n".join(documents)

    return QueryResponse(
        question=request.question,
        answer=context,
        sources=sources,
    )
