"""数据模型定义"""
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    filename: str
    chunks_count: int
    message: str


class DocumentInfo(BaseModel):
    """文档信息"""
    id: str
    filename: str
    source: str


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: list[DocumentInfo]
    total: int


class QueryRequest(BaseModel):
    """查询请求"""
    question: str
    top_k: int = 3


class QueryResponse(BaseModel):
    """查询响应"""
    question: str
    answer: str
    sources: list[str]
