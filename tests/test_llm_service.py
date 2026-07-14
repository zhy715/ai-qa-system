"""LLM 服务测试"""
import os

import pytest

from app.services.llm_service import LLMService, RAG_PROMPT, RAG_PROMPT_WITH_HISTORY


class TestLLMService:
    def test_not_ready_without_key(self, monkeypatch):
        """无 API Key 时应返回 is_ready=False"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "")
        service = LLMService()
        assert service.is_ready() is False

    def test_ready_with_key(self, monkeypatch):
        """有 API Key 时应返回 is_ready=True"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key-123")
        service = LLMService()
        assert service.is_ready() is True

    def test_placeholder_key_not_ready(self, monkeypatch):
        """占位符 Key 视为未配置"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-your-api-key-here")
        service = LLMService()
        assert service.is_ready() is False

    def test_generate_without_llm(self, monkeypatch):
        """无 LLM 时 generate 返回提示信息"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "")
        service = LLMService()
        result = service.generate_answer("问题", ["文档内容"], [])
        assert "未配置" in result

    def test_generate_without_documents(self, monkeypatch):
        """无文档时应返回提示"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        service = LLMService()
        result = service.generate_answer("问题", [], [])
        assert "未检索到" in result

    def test_prompts_exist(self):
        """确保两个 Prompt 模板都存在"""
        assert len(RAG_PROMPT) > 100
        assert len(RAG_PROMPT_WITH_HISTORY) > 100
        assert "{context}" in RAG_PROMPT
        assert "{question}" in RAG_PROMPT
        assert "{history}" in RAG_PROMPT_WITH_HISTORY
