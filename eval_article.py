"""方法 B：法条号直标召回率评估"""
import json
import os
import sys

sys.path.insert(0, ".")
os.environ["HF_HUB_OFFLINE"] = "1"

from app.services.vector_service import VectorService
from app.services.llm_service import LLMService


def load_test_set(path="eval_article_test_set.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_embed(vec, test_set, top_k=5):
    """仅嵌入检索"""
    results = []
    for item in test_set:
        ret = vec.query(item["question"], top_k=top_k)
        docs = ret["documents"]
        metas = ret["metadatas"]
        hit_ranks, src_ranks = _find_hits(docs, metas, item)
        results.append({
            "question": item["question"][:80],
            "source_law": item["source_law"],
            "article_number": item["article_number"],
            "hit": len(hit_ranks) > 0,
            "hit_ranks": hit_ranks,
            "source_hit": len(src_ranks) > 0,
            "source_hit_ranks": src_ranks,
        })
    return results


def evaluate_rerank(vec, llm, test_set, pool=20, top_k=5):
    """嵌入 + LLM 重排"""
    results = []
    for item in test_set:
        ret = vec.query(item["question"], top_k=pool)
        docs = ret["documents"]
        metas = ret["metadatas"]

        try:
            idx = llm.rerank(item["question"], docs, top_k)
            docs = [docs[i] for i in idx]
            metas = [metas[i] for i in idx]
        except Exception:
            docs = docs[:top_k]
            metas = metas[:top_k]

        hit_ranks, src_ranks = _find_hits(docs, metas, item)
        results.append({
            "question": item["question"][:80],
            "source_law": item["source_law"],
            "article_number": item["article_number"],
            "hit": len(hit_ranks) > 0,
            "hit_ranks": hit_ranks,
            "source_hit": len(src_ranks) > 0,
            "source_hit_ranks": src_ranks,
        })
    return results


def _find_hits(docs, metas, item):
    """检查法条号是否出现在检索结果中"""
    expected_article = item["article_number"]  # e.g. "第五百零二条"
    expected_source = item["source_law"]

    hit_ranks = []
    src_ranks = []
    for rank, (doc, meta) in enumerate(zip(docs, metas), start=1):
        if meta and meta.get("source") == expected_source:
            src_ranks.append(rank)
            if expected_article in doc:
                hit_ranks.append(rank)
    return hit_ranks, src_ranks


def calc_metrics(results, k):
    n = len(results) or 1
    strict = sum(1 for r in results if r["hit"] and any(rk <= k for rk in r["hit_ranks"])) / n
    loose = sum(1 for r in results if r["source_hit"] and any(rk <= k for rk in r["source_hit_ranks"])) / n
    mrr_vals = [1.0 / min(r["hit_ranks"]) if r["hit_ranks"] and min(r["hit_ranks"]) <= k else 0.0 for r in results]
    mrr = sum(mrr_vals) / n
    return strict, loose, mrr


def main():
    print("=" * 60)
    print("方法 B：法条号直标 — 召回率评估")
    print("=" * 60)

    vec = VectorService(persist_dir="chroma_db")
    llm = LLMService()
    test_set = load_test_set()
    print(f"\n测试集: {len(test_set)} 题 ({len(set(t['source_law'] for t in test_set))} 部法律)")

    print("\n跑 baseline (仅嵌入)...")
    embed_results = evaluate_embed(vec, test_set, top_k=5)

    print("跑 rerank (嵌入+LLM精排)...")
    if llm.is_ready():
        rerank_results = evaluate_rerank(vec, llm, test_set, pool=20, top_k=5)
    else:
        rerank_results = None

    # 指标
    print(f"\n{'='*60}")
    print(f"{'指标':<22} {'仅嵌入':>10} {'嵌入+重排':>10}")
    print(f"{'-'*44}")

    for label, k in [("法条 Recall@1", 1), ("法条 Recall@3", 3), ("法条 Recall@5", 5),
                      ("法律 Recall@5", 5), ("MRR (法条)", 5)]:
        e_s, e_l, e_m = calc_metrics(embed_results, k)
        val_embed = e_s if "法条" in label else (e_l if "法律" in label else e_m)
        if rerank_results:
            r_s, r_l, r_m = calc_metrics(rerank_results, k)
            val_rerank = r_s if "法条" in label else (r_l if "法律" in label else r_m)
        else:
            val_rerank = 0
        arrow = ""
        if rerank_results and val_rerank > val_embed:
            arrow = f"  +{(val_rerank-val_embed)*100:.0f}pp"
        elif rerank_results and val_rerank < val_embed:
            arrow = f"  {(val_rerank-val_embed)*100:.0f}pp"
        print(f"{label:<22} {val_embed:>9.1%} {val_rerank:>9.1%}{arrow}")

    # 按法律分组
    print(f"\n{'='*60}")
    print("按法律 — 法条 Recall@5 对比")
    print(f"{'='*60}")
    print(f"{'法律':<22} {'仅嵌入':>8} {'+重排':>8}")
    print(f"{'-'*40}")
    by_law = {}
    for t in test_set:
        law = t["source_law"]
        by_law.setdefault(law, [])
        by_law[law].append(t)

    for law in sorted(by_law):
        e_items = [r for r, t in zip(embed_results, test_set) if t["source_law"] == law]
        r_items = [r for r, t in zip(rerank_results, test_set) if t["source_law"] == law] if rerank_results else []
        e_r5 = sum(1 for r in e_items if r["hit"]) / len(e_items) if e_items else 0
        r_r5 = sum(1 for r in r_items if r["hit"]) / len(r_items) if r_items else 0
        print(f"{law:<22} {e_r5:>7.1%} {r_r5:>7.1%}")

    # 统计未命中案例
    misses = [r for r in embed_results if not r["hit"]]
    if misses:
        print(f"\n{'='*60}")
        print(f"仅嵌入未命中 ({len(misses)} 题)")
        print(f"{'='*60}")
        for r in misses[:10]:
            print(f"  {r['article_number']}: {r['question'][:60]}...")


if __name__ == "__main__":
    main()
