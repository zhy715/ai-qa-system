"""方法 B：法条号直标测评集 — 答案精确到具体法条号"""
import json
import os
import random
import re
import sys

sys.path.insert(0, ".")
os.environ["HF_HUB_OFFLINE"] = "1"

from app.services.document_service import DocumentService
from app.services.llm_service import LLMService


def extract_articles(text, min_chars=80):
    """从法律文本中提取每一条法条及其编号

    支持格式：
    - 民法典: 《中华人民共和国民法典》第一条 为了...
    - 刑法等: **第一条** 为了...
    - 其他: 第一条 为了...
    """
    # 跳过 YAML frontmatter
    text_clean = text
    if text.startswith('---'):
        end = text_clean.find('---', 3)
        if end > 0:
            text_clean = text_clean[end + 3:]

    # 去掉 markdown 加粗标记，统一格式
    text_clean = text_clean.replace('**', '')

    # 匹配法条号（不要求行首）
    # 法条号后跟内容，直到下一个法条号或文末
    art_re = re.compile(
        r'(第[一二三四五六七八九十百千\d]+条)\s*'
        r'((?:(?!第[一二三四五六七八九十百千\d]+条).)*)',
        re.DOTALL,
    )
    articles = []
    for m in art_re.finditer(text_clean):
        num = m.group(1)
        content = m.group(2).strip()
        # 清理换行和多余空格
        content = ' '.join(content.split())
        full = num + " " + content
        if len(full) >= min_chars:
            articles.append((num, full[:600]))
    return articles


PROMPT = """根据以下法条，生成一个用户可能提出的法律咨询问题。

法条：
{article}

要求：
1. 问题的答案必须严格依据该法条
2. 模拟普通用户语气，自然口语化
3. 问题中不要出现法条号
4. 只输出问题本身，一行

问题："""


def main():
    print("=" * 60)
    print("方法 B：法条号直标测评集")
    print("=" * 60)

    doc = DocumentService(upload_dir="uploads")
    llm = LLMService()

    if not llm.is_ready():
        print("LLM not ready")
        return

    builtin = "builtin_docs"
    law_files = sorted(f for f in os.listdir(builtin)
                       if os.path.splitext(f)[1].lower() in {'.txt', '.md', '.pdf'}
                       and f != '.gitkeep')

    random.seed(42)
    test_set = []
    total_gen = 0

    for law_file in law_files:
        path = os.path.join(builtin, law_file)
        try:
            text = doc.parse_file(path, law_file)
        except Exception as e:
            print(f"SKIP {law_file}: {e}")
            continue

        articles = extract_articles(text)
        if len(articles) < 5:
            print(f"SKIP {law_file}: only {len(articles)} articles")
            continue

        # 每部法律随机选 10 条
        n = min(10, len(articles))
        picked = random.sample(articles, n)
        print(f"\n{law_file}: {len(articles)} 条法条 → 选 {n} 条")

        for art_num, art_content in picked:
            total_gen += 1
            # 截断超长法条
            truncated = art_content[:600] if len(art_content) > 600 else art_content
            prompt = PROMPT.format(article=truncated)
            try:
                from langchain_core.messages import HumanMessage
                resp = llm.llm.invoke([HumanMessage(content=prompt)])
                question = resp.content.strip().strip("""）。)""")
                for prefix in ["问题：", "问题是：", "问题:"]:
                    if question.startswith(prefix):
                        question = question[len(prefix):].strip()

                test_set.append({
                    "question": question,
                    "source_law": law_file,
                    "article_number": art_num,
                    "article_preview": art_content[:200],
                })
                print(f"  [{total_gen}] {art_num}: {question[:70]}...")
            except Exception as e:
                print(f"  [{total_gen}] FAIL {art_num}: {e}")

    # 保存
    out = "eval_article_test_set.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(test_set, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"测评集已保存: {out}")
    print(f"共 {len(test_set)} 题，{len(set(t['source_law'] for t in test_set))} 部法律")

    by_law = {}
    for t in test_set:
        by_law.setdefault(t["source_law"], 0)
        by_law[t["source_law"]] += 1
    for law, n in sorted(by_law.items()):
        print(f"  {law}: {n} 题")


if __name__ == "__main__":
    main()
