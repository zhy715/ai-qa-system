"""数据模型验证测试"""
import pytest
from pydantic import ValidationError

from app.models.schemas import (
    QueryRequest,
    DocumentInfo,
    DocumentListResponse,
    DeleteDocumentResponse,
    ConversationMessage,
    ConversationInfo,
    ConversationDetail,
)


class TestQueryRequest:
    def test_valid_request(self):
        req = QueryRequest(question="什么是合同纠纷？")
        assert req.question == "什么是合同纠纷？"
        assert req.top_k == 3
        assert req.conversation_id is None

    def test_question_too_long(self):
        with pytest.raises(ValidationError):
            QueryRequest(question="x" * 2001)

    def test_question_empty(self):
        with pytest.raises(ValidationError):
            QueryRequest(question="")

    def test_top_k_minimum(self):
        with pytest.raises(ValidationError):
            QueryRequest(question="test", top_k=0)

    def test_top_k_maximum(self):
        with pytest.raises(ValidationError):
            QueryRequest(question="test", top_k=11)

    def test_top_k_default(self):
        req = QueryRequest(question="test")
        assert req.top_k == 3

    def test_conversation_id_too_long(self):
        with pytest.raises(ValidationError):
            QueryRequest(question="test", conversation_id="x" * 65)


class TestDocumentInfo:
    def test_create_document_info(self):
        doc = DocumentInfo(id="report", filename="report.pdf", source="report.pdf")
        assert doc.id == "report"
        assert doc.filename == "report.pdf"


class TestDeleteDocumentResponse:
    def test_create_response(self):
        resp = DeleteDocumentResponse(
            filename="test.pdf", deleted_chunks=5, message="已删除"
        )
        assert resp.filename == "test.pdf"
        assert resp.deleted_chunks == 5


class TestConversationMessage:
    def test_create_message(self):
        msg = ConversationMessage(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"
        assert msg.sources == []
