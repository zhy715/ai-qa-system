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
    conversation_id: str | None = None  # 多轮对话 ID，为空则新建


class QueryResponse(BaseModel):
    """查询响应"""
    question: str
    answer: str
    sources: list[str]
    conversation_id: str | None = None  # 返回对话 ID，后续可继续追问


# ==================== 对话管理 ====================

class ConversationMessage(BaseModel):
    """对话中的一条消息"""
    role: str  # "user" | "assistant"
    content: str
    sources: list[str] = []


class ConversationInfo(BaseModel):
    """对话摘要信息"""
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    conversations: list[ConversationInfo]
    total: int


class ConversationDetail(BaseModel):
    """对话详情（含全部消息）"""
    id: str
    title: str
    messages: list[ConversationMessage]
    created_at: str
    updated_at: str
