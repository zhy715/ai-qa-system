"""大语言模型服务 —— 基于检索结果生成自然语言回答"""
import os
from typing import List

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# 加载 .env 中的环境变量
load_dotenv()


# RAG 提示词模板
RAG_PROMPT = """你是一个专业的知识库助手。请根据以下参考资料回答用户的问题。

## 规则
- 只根据参考资料回答，不要编造信息
- 如果参考资料不足以回答问题，诚实地说"根据现有资料，我无法回答这个问题"
- 回答要简洁、有条理，使用中文

## 参考资料
{context}

## 用户问题
{question}

## 回答
"""


class LLMService:
    """大模型服务：基于检索到的文档片段，生成自然语言回答"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not self.api_key or self.api_key == "sk-your-api-key-here":
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model=self.model_name,
                base_url=self.base_url,
                api_key=self.api_key,
                temperature=0.3,   # 低温度，回答更稳定
                max_tokens=1024,
            )

        self.prompt = ChatPromptTemplate.from_template(RAG_PROMPT)

    def is_ready(self) -> bool:
        """检查 API Key 是否已配置"""
        return self.llm is not None

    def generate_answer(self, question: str, documents: List[str]) -> str:
        """基于检索到的文档生成回答"""
        if not self.llm:
            return "⚠️ LLM 未配置：请在 .env 文件中设置你的 DEEPSEEK_API_KEY"

        if not documents:
            return "未检索到相关文档，无法回答该问题。"

        # 拼接文档作为上下文
        context = "\n\n---\n\n".join(documents)

        # 构建消息
        messages = self.prompt.format_messages(
            context=context,
            question=question,
        )

        # 调用大模型
        response = self.llm.invoke(messages)

        return response.content
