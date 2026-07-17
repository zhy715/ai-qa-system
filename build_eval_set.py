"""方法 A：LLM 自动生成法律问答测评集"""
import json
import os
import random
import sys

sys.path.insert(0, ".")
os.environ["HF_HUB_OFFLINE"] = "1"

from app.services.vector_service import VectorService
from app.services.llm_service import LLMService


def sample_chunks(vec_service, per_law=5):
    """从每部法律中随机采样 chunk"""
    all_data = vec_service.collection.get()
    by_source = {}
    for doc, meta in zip(all_data["documents"], all_data["metadatas"]):
        src = meta.get("source", "?")
        chunk_i = meta.get("chunk_index", -1)
        by_source.setdefault(src, []).append((chunk_i, doc[:600]))  # 截断减少 prompt 长度

    random.seed(42)
    samples = []
    for src in sorted(by_source):
        picked = random.sample(by_source[src], min(per_law, len(by_source[src])))
        for ci, content in picked:
            samples.append((src, ci, content))
    return samples


PROMPT = """你是一位法律测评专家。请根据以下法律条文片段，生成一个用户可能提出的法律咨询问题。

要求：
1. 问题的答案必须严格依据该条文，不能超出条文范围
2. 问题要像真实用户会问的话，模拟普通人在生活中遇到法律困惑时的语气
3. 问题中不要出现法条号（如"第X条"）
4. 每次生成不同类型的问题：有时是咨询类（"我该怎么办"），有时是确认类（"这样合法吗"），有时是维权类（"我能要求赔偿吗"）
5. 只输出问题本身，一行，不加任何前缀

法律条文：
{chunk}

问题："""


def generate_questions(samples, llm_service):
    """用 LLM 为每个 chunk 生成问题"""
    test_set = []
    for i, (src, ci, chunk) in enumerate(samples):
        law_name = src.replace(".md", "").replace(".txt", "")
        prompt = PROMPT.format(chunk=chunk)
        try:
            # 直接调用底层 LLM，不走 RAG 流程
            from langchain_core.messages import HumanMessage
            msg = HumanMessage(content=prompt)
            resp = llm_service.llm.invoke([msg])
            question = resp.content.strip().strip("""）。)""")
            # 清理多余前缀
            for prefix in ["问题：", "问题是：", "问题:"]:
                if question.startswith(prefix):
                    question = question[len(prefix):].strip()
            test_set.append({
                "question": question,
                "source_law": src,
                "chunk_index": ci,
                "chunk_content_preview": chunk[:200],
            })
            print(f"[{i+1}/{len(samples)}] {law_name} #{ci}: {question[:80]}...")
        except Exception as e:
            print(f"[{i+1}/{len(samples)}] FAIL {law_name} #{ci}: {e}")
    return test_set


def main():
    print("=" * 60)
    print("方法 A：LLM 生成测评集")
    print("=" * 60)

    vec = VectorService(persist_dir="chroma_db")
    llm = LLMService()

    if not llm.is_ready():
        print("LLM not ready — check .env DEEPSEEK_API_KEY")
        return

    # 1. 采样 — 每部法律 15 题，不足则全取
    samples = sample_chunks(vec, per_law=15)
    print(f"\n采样 {len(samples)} 个 chunk (来自 {len(set(s for s,_,_ in samples))} 部法律)")

    # 2. LLM 生成问题
    print(f"\n生成问题中...\n")
    test_set = generate_questions(samples, llm)

    # 3. 保存
    out_path = "eval_test_set.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(test_set, f, ensure_ascii=False, indent=2)
    print(f"\n测评集已保存: {out_path} ({len(test_set)} 题)")

    # 4. 简要统计
    by_law = {}
    for item in test_set:
        by_law.setdefault(item["source_law"], 0)
        by_law[item["source_law"]] += 1
    print("\n各法律题目数:")
    for law, n in sorted(by_law.items()):
        print(f"  {law}: {n} 题")


if __name__ == "__main__":
    main()
