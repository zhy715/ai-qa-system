"""大语言模型服务 -- 基于检索结果生成自然语言回答"""
import logging
import os
from typing import List

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# 加载 .env 中的环境变量
load_dotenv()

logger = logging.getLogger("lvda.llm")


# RAG 提示词模板（无历史）
RAG_PROMPT = """你是一名资深法律顾问，精通中国法律法规与司法实践。请根据以下参考资料回答用户的法律咨询。

## 身份与语气
- 使用专业但易懂的法律语言
- 保持中立、客观、严谨，不做主观臆断
- 你是法律信息提供者，不能替代执业律师

## 回答规则
- 严格基于参考资料回答，不得编造法条或案例
- 引用法条时注明法律法规名称和条款号
- 参考资料不足时明确告知并建议咨询专业律师
- 结构：先结论 → 再引述法律依据 → 最后补充实务要点

## 参考资料
{context}

## 用户问题
{question}

## 回答
"""

# RAG 提示词模板（带对话历史）
RAG_PROMPT_WITH_HISTORY = """你是一名资深法律顾问，精通中国法律法规与司法实践。请根据以下参考资料和对话历史回答用户的法律咨询。

## 身份与语气
- 使用专业但易懂的法律语言
- 保持中立、客观、严谨，不做主观臆断
- 你是法律信息提供者，不能替代执业律师

## 回答规则
- 严格基于参考资料回答，不得编造法条或案例
- 引用法条时注明法律法规名称和条款号
- 参考资料不足时明确告知并建议咨询专业律师
- 结合对话历史理解用户的追问和代词指代
- 结构：先结论 → 再引述法律依据 → 最后补充实务要点

## 对话历史
{history}

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
                timeout=30,        # 请求超时 30 秒
                max_retries=2,     # 失败后自动重试 2 次
            )

        self.prompt = ChatPromptTemplate.from_template(RAG_PROMPT)
        self.prompt_with_history = ChatPromptTemplate.from_template(RAG_PROMPT_WITH_HISTORY)

    def is_ready(self) -> bool:
        """检查 API Key 是否已配置"""
        return self.llm is not None

    def generate_answer(
        self,
        question: str,
        documents: List[str],
        history: List[dict] | None = None,
    ) -> str:
        """基于检索到的文档 + 对话历史生成回答"""
        if not self.llm:
            return "⚠️ LLM 未配置：请在 .env 文件中设置你的 DEEPSEEK_API_KEY"

        if not documents:
            return "未检索到相关文档，无法回答该问题。"

        context = "\n\n---\n\n".join(documents)

        # 有历史 → 带历史模板；无历史 → 简单模板
        if history and len(history) > 0:
            history_text = "\n".join(
                f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
                for m in history
            )
            messages = self.prompt_with_history.format_messages(
                context=context,
                question=question,
                history=history_text,
            )
        else:
            messages = self.prompt.format_messages(
                context=context,
                question=question,
            )

        response = self.llm.invoke(messages)
        logger.info("LLM 回答生成完成, 长度=%d 字符", len(response.content))
        return response.content

    def rerank(self, question: str, documents: list[str], top_k: int = 5) -> list[int]:
        """用 LLM 对候选文档片段进行精排，返回前 top_k 个的原始索引

        相比嵌入向量距离，cross-encoder 式精排对语义匹配更准确，
        能将正确 chunk 的排名从 6-20 位拉升到前 5。
        """
        if not self.llm or len(documents) <= top_k:
            return list(range(len(documents)))

        # 构建候选列表
        candidates = "\n".join(
            f"[{i}] {doc[:400]}" for i, doc in enumerate(documents)
        )

        prompt = f"""请根据用户问题，从以下法律条文候选中选出最相关的 {top_k} 个。
只输出编号列表，格式如: [3, 0, 7, 1, 5]，不要任何解释。

用户问题: {question}

候选条文:
{candidates}

最相关 {top_k} 个的编号:"""

        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=prompt)])
            text = response.content.strip()

            # 解析 "[3, 0, 7, 1, 5]" 格式
            import re
            nums = re.findall(r'\d+', text)
            indices = [int(n) for n in nums if 0 <= int(n) < len(documents)]

            # 去重 + 补齐
            seen = set()
            result = []
            for idx in indices:
                if idx not in seen:
                    result.append(idx)
                    seen.add(idx)
            # 补齐 LLM 未选满的
            for i in range(len(documents)):
                if len(result) >= top_k:
                    break
                if i not in seen:
                    result.append(i)

            logger.info(
                "精排完成: %d 候选 → top %d, LLM 选择了 %d 个",
                len(documents), top_k, len(indices),
            )
            return result[:top_k]

        except Exception as e:
            logger.warning("精排失败，回退到原始排序: %s", str(e))
            return list(range(min(top_k, len(documents))))
