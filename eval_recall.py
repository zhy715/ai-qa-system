"""多法律文档召回率评估 — 对比嵌入检索 vs 嵌入+重排"""
import json
import os
import sys

sys.path.insert(0, ".")
os.environ["HF_HUB_OFFLINE"] = "1"

from app.services.vector_service import VectorService
from app.services.llm_service import LLMService


def load_test_set(path="eval_test_set.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_embed(vec, test_set, top_k=5):
    """仅嵌入检索（baseline）"""
    results = []
    for item in test_set:
        ret = vec.query(item["question"], top_k=top_k)
        metas = ret["metadatas"]
        hit_ranks, src_ranks = _find_hits(metas, item)
        results.append({
            "question": item["question"][:80],
            "source_law": item["source_law"],
            "chunk_index": item["chunk_index"],
            "hit": len(hit_ranks) > 0,
            "hit_ranks": hit_ranks,
            "source_hit": len(src_ranks) > 0,
            "source_hit_ranks": src_ranks,
        })
    return results


def evaluate_rerank(vec, llm, test_set, pool=20, top_k=5):
    """嵌入检索 top-N → LLM 精排 → 取 top-K"""
    results = []
    for item in test_set:
        # 1. 嵌入召回 top-N
        ret = vec.query(item["question"], top_k=pool)
        docs = ret["documents"]
        metas = ret["metadatas"]

        # 2. LLM 精排
        try:
            reranked_idx = llm.rerank(item["question"], docs, top_k)
            docs = [docs[i] for i in reranked_idx]
            metas = [metas[i] for i in reranked_idx]
        except Exception:
            docs = docs[:top_k]
            metas = metas[:top_k]

        hit_ranks, src_ranks = _find_hits(metas, item)
        results.append({
            "question": item["question"][:80],
            "source_law": item["source_law"],
            "chunk_index": item["chunk_index"],
            "hit": len(hit_ranks) > 0,
            "hit_ranks": hit_ranks,
            "source_hit": len(src_ranks) > 0,
            "source_hit_ranks": src_ranks,
        })
    return results


def _find_hits(metas, item):
    """检查 ground truth chunk 是否命中"""
    expected_source = item["source_law"]
    expected_chunk = item["chunk_index"]
    hit_ranks = []
    src_ranks = []
    for rank, meta in enumerate(metas, start=1):
        if meta and meta.get("source") == expected_source:
            src_ranks.append(rank)
            if meta.get("chunk_index") == expected_chunk:
                hit_ranks.append(rank)
    return hit_ranks, src_ranks


def calc_metrics(results, k):
    n = len(results) or 1
    strict = sum(1 for r in results if r["hit"] and any(rk <= k for rk in r["hit_ranks"])) / n
    loose = sum(1 for r in results if r["source_hit"] and any(rk <= k for rk in r["source_hit_ranks"])) / n
    mrr_vals = []
    for r in results:
        ranks = [rk for rk in r["hit_ranks"] if rk <= k]
        mrr_vals.append(1.0 / min(ranks) if ranks else 0.0)
    mrr = sum(mrr_vals) / n
    return strict, loose, mrr


def main():
    print("=" * 60)
    print("检索召回率对比: 嵌入 vs 嵌入+重排")
    print("=" * 60)

    vec = VectorService(persist_dir="chroma_db")
    llm = LLMService()
    test_set = load_test_set()
    print(f"\n测试集: {len(test_set)} 题 ({len(set(t['source_law'] for t in test_set))} 部法律)")

    # 跑两轮评估
    print("\n跑 baseline (仅嵌入)...")
    embed_results = evaluate_embed(vec, test_set, top_k=5)

    print("跑 rerank (嵌入+LLM精排)...")
    if llm.is_ready():
        rerank_results = evaluate_rerank(vec, llm, test_set, pool=20, top_k=5)
    else:
        print("  LLM 不可用，跳过重排评估")
        rerank_results = None

    # 对比表格
    print(f"\n{'='*60}")
    print(f"{'指标':<22} {'仅嵌入':>10} {'嵌入+重排':>10}")
    print(f"{'-'*44}")

    for label, k in [("严格 Recall@1", 1), ("严格 Recall@3", 3), ("严格 Recall@5", 5),
                      ("宽松 Recall@1", 1), ("宽松 Recall@3", 3), ("宽松 Recall@5", 5),
                      ("MRR (严格)", 5)]:
        e_s, e_l, e_m = calc_metrics(embed_results, k if k > 0 else 5)
        val_embed = e_s if "严格" in label else (e_l if "宽松" in label else e_m)
        if rerank_results:
            r_s, r_l, r_m = calc_metrics(rerank_results, k if k > 0 else 5)
            val_rerank = r_s if "严格" in label else (r_l if "宽松" in label else r_m)
        else:
            val_rerank = 0
        arrow = ""
        if rerank_results and val_rerank > val_embed:
            arrow = f"  +{(val_rerank-val_embed)*100:.0f}pp"
        elif rerank_results and val_rerank < val_embed:
            arrow = f"  {(val_rerank-val_embed)*100:.0f}pp"
        print(f"{label:<22} {val_embed:>9.1%} {val_rerank:>9.1%}{arrow}")

    # 按法律分组
    if rerank_results:
        print(f"\n{'='*60}")
        print("按法律分组 — 严格 Recall@5 对比")
        print(f"{'='*60}")
        print(f"{'法律':<22} {'仅嵌入':>8} {'+重排':>8} {'提升':>8}")
        print(f"{'-'*48}")
        by_law = {}
        for item in test_set:
            law = item["source_law"].replace(".md", "").replace(".txt", "")
            by_law.setdefault(law, []).append(item)

        for law in sorted(by_law):
            items = by_law[law]
            n = len(items)
            e_items = [r for r in embed_results if r["source_law"] in [i["source_law"] for i in items[:1]]]
            # Group results by law properly
            law_embed = [r for r, item in zip(embed_results, test_set) if item["source_law"].endswith(law + ".md") or item["source_law"].endswith(law + ".txt") or item["source_law"].replace(".md","").replace(".txt","") == law]
            law_rerank = [r for r, item in zip(rerank_results, test_set) if item["source_law"].endswith(law + ".md") or item["source_law"].endswith(law + ".txt") or item["source_law"].replace(".md","").replace(".txt","") == law]
            e_r5 = sum(1 for r in law_embed if r["hit"]) / len(law_embed) if law_embed else 0
            r_r5 = sum(1 for r in law_rerank if r["hit"]) / len(law_rerank) if law_rerank else 0
            diff = f"+{(r_r5-e_r5)*100:.0f}pp" if r_r5 >= e_r5 else f"{(r_r5-e_r5)*100:.0f}pp"
            print(f"{law:<22} {e_r5:>7.1%} {r_r5:>7.1%} {diff:>8}")


if __name__ == "__main__":
    main()
