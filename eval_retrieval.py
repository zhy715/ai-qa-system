"""
RAG 检索评估脚本
指标：Recall@K（召回率）、MRR（平均倒数排名）
方法：网格搜索不同 chunk_size / overlap，对比检索效果
"""
import os
import shutil
import json
import sys

# 确保在项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

from app.services.document_service import DocumentChunk, DocumentService
from app.services.vector_service import VectorService

# ─── 测试文档 ─────────────────────────────────────────────
TEST_DOC = "eval_real.docx"

# ─── 标注集：问题 → 答案中必须包含的关键词 ────────────────
# 每个问题对应论文中一个确定的事实，关键词是从原文中提取的
LABELED_QUESTIONS = [
    # (问题, 期望在检索结果中出现的关键词)
    ("本文对比了哪三种推荐算法？",               "ItemKNN"),
    ("实验使用了哪两个数据集？",                  "Amazon-Books"),
    ("评估模型使用了哪两个指标？",                "NDCG"),
    ("BPR-MF采用什么优化目标？",                 "pairwise"),
    ("FunkSVD采用什么优化方式？",                "pointwise"),
    ("DNS的全称是什么？",                        "Dynamic Negative Sampling"),
    ("哪类算法属于非参数方法？",                  "ItemKNN"),
    ("数据预处理中使用了什么过滤方法？",          "k-core"),
    ("在Amazon-Books数据集上哪个模型表现最好？",  "BPR-MF"),
    ("MovieLens-1M数据集的评分范围是多少？",      "1"),
]


def evaluate_config(doc_service, vec_service, chunk_size, chunk_overlap, top_k=5):
    """用指定参数跑一遍评估，返回每个问题的检索结果"""
    # 保存原始配置
    orig_size, orig_overlap = doc_service.CHUNK_SIZE, doc_service.CHUNK_OVERLAP
    doc_service.CHUNK_SIZE = chunk_size
    doc_service.CHUNK_OVERLAP = chunk_overlap

    # 清空旧数据 + 重新索引
    try:
        vec_service.client.delete_collection(vec_service.collection.name)
    except Exception:
        pass
    vec_service.collection = vec_service.client.get_or_create_collection(
        name=vec_service.collection.name,
        embedding_function=vec_service.embedding_fn,
    )

    chunks = doc_service.process_file(TEST_DOC, os.path.basename(TEST_DOC))
    if not chunks:
        doc_service.CHUNK_SIZE, doc_service.CHUNK_OVERLAP = orig_size, orig_overlap
        return None

    vec_service.add_documents(chunks)

    results = []
    for question, expected_keyword in LABELED_QUESTIONS:
        ret = vec_service.query(question, top_k=top_k)
        docs = ret["documents"]
        # 检查期望关键词是否出现在任意检索到的文档中
        hit_ranks = []
        for rank, doc in enumerate(docs, start=1):
            if expected_keyword.lower() in doc.lower():
                hit_ranks.append(rank)

        results.append({
            "question": question,
            "expected": expected_keyword,
            "hit": len(hit_ranks) > 0,
            "hit_at": hit_ranks,
            "retrieved_docs": docs,
        })

    # 还原配置
    doc_service.CHUNK_SIZE, doc_service.CHUNK_OVERLAP = orig_size, orig_overlap
    return results


def calc_metrics(results, k):
    """计算 Recall@k 和 MRR"""
    total = len(results)
    if total == 0:
        return 0, 0

    # Recall@k：在 top-k 中命中几个
    recall_hits = sum(
        1 for r in results if r["hit"] and any(rank <= k for rank in r["hit_at"])
    )
    recall = recall_hits / total

    # MRR：平均倒数排名（考虑第一个命中的位置）
    reciprocal_ranks = []
    for r in results:
        ranks = [rank for rank in r["hit_at"] if rank <= k]
        reciprocal_ranks.append(1.0 / min(ranks) if ranks else 0.0)
    mrr = sum(reciprocal_ranks) / total

    return recall, mrr


# ─── 主流程 ────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("RAG 检索评估 — 网格搜索最优参数")
    print("=" * 70)
    print(f"\n测试文档: {TEST_DOC}")
    print(f"标注问题数: {len(LABELED_QUESTIONS)}")
    print(f"嵌入模型: paraphrase-multilingual-MiniLM-L12-v2 (多语言)")

    # 注意：VectorService.__init__ 中会删除旧 knowledge_base 集合
    # 这里我们需要一个独立的评估环境
    import chromadb
    from chromadb.utils import embedding_functions

    eval_client = chromadb.PersistentClient(path="eval_chroma")
    eval_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )

    doc_service = DocumentService()

    # 网格搜索
    chunk_sizes = [200, 300, 500, 800, 1000, 1500]
    overlaps = [0, 50, 100, 150]

    print(f"\n网格规模: {len(chunk_sizes)} × {len(overlaps)} = {len(chunk_sizes) * len(overlaps)} 组")
    print("\n" + "-" * 70)

    best_score = -1
    best_config = None
    all_rows = []

    for cs in chunk_sizes:
        for ol in overlaps:
            if ol >= cs:  # 非法组合
                continue

            print(f"  测试 chunk_size={cs}, overlap={ol} ...", end=" ")

            # 为每组参数创建独立 collection
            col_name = f"eval_cs{cs}_ol{ol}"
            try:
                eval_client.delete_collection(col_name)
            except Exception:
                pass
            collection = eval_client.get_or_create_collection(
                name=col_name,
                embedding_function=eval_ef,
            )

            # 手动跑一遍：解析 → 分块 → 索引 → 查询
            doc_service.CHUNK_SIZE = cs
            doc_service.CHUNK_OVERLAP = ol
            chunks = doc_service.process_file(TEST_DOC, os.path.basename(TEST_DOC))
            if not chunks:
                print("解析失败")
                continue

            # 入库
            ids = [f"c{i}" for i in range(len(chunks))]
            docs = [c.content for c in chunks if c.content.strip()]
            if not docs:
                print("无有效分块")
                continue
            ids = ids[:len(docs)]
            collection.add(ids=ids, documents=docs)

            # 查询所有问题
            eval_results = []
            for question, expected_keyword in LABELED_QUESTIONS:
                ret = collection.query(query_texts=[question], n_results=5)
                ret_docs = ret.get("documents", [[]])[0]
                hit_ranks = []
                for rank, doc in enumerate(ret_docs, start=1):
                    if expected_keyword.lower() in doc.lower():
                        hit_ranks.append(rank)

                eval_results.append({
                    "question": question,
                    "expected": expected_keyword,
                    "hit": len(hit_ranks) > 0,
                    "hit_at": hit_ranks,
                })

            r3, mrr3 = calc_metrics(eval_results, 3)
            r5, mrr5 = calc_metrics(eval_results, 5)

            print(f"R@3={r3:.1%}  R@5={r5:.1%}  MRR@5={mrr5:.3f}")

            all_rows.append((cs, ol, len(docs), r3, r5, mrr5))

            # 用 MRR@5 作为综合评分
            score = mrr5
            if score > best_score:
                best_score = score
                best_config = (cs, ol, r3, r5, mrr5, len(docs))

            # 清理当前 collection
            try:
                eval_client.delete_collection(col_name)
            except Exception:
                pass

    # ─── 结果表格 ────────────────────────────────────────
    print("\n" + "=" * 70)
    print("评估结果（按 MRR@5 排序）")
    print("=" * 70)
    print(f"{'chunk_size':>10}  {'overlap':>8}  {'块数':>4}  {'R@3':>7}  {'R@5':>7}  {'MRR@5':>7}")
    print("-" * 55)

    all_rows.sort(key=lambda r: r[5], reverse=True)

    for cs, ol, nchunks, r3, r5, mrr5 in all_rows:
        marker = " <--" if (cs, ol) == (best_config[0], best_config[1]) else ""
        print(f"{cs:>10}  {ol:>8}  {nchunks:>4}  {r3:>7.1%}  {r5:>7.1%}  {mrr5:>7.3f}{marker}")

    # ─── 最佳配置 ────────────────────────────────────────
    print("\n" + "=" * 70)
    print("最优配置")
    print("=" * 70)
    best_cs, best_ol, best_r3, best_r5, best_mrr5, best_n = best_config
    print(f"  chunk_size  = {best_cs}")
    print(f"  overlap     = {best_ol}")
    print(f"  分块数      = {best_n}")
    print(f"  Recall@3    = {best_r3:.1%}  (top-3 中能找到答案的比例)")
    print(f"  Recall@5    = {best_r5:.1%}  (top-5 中能找到答案的比例)")
    print(f"  MRR@5       = {best_mrr5:.3f}  (正确答案的平均排名倒数)")

    # 当前配置对比
    print(f"\n对比当前配置 (500 / 100):")
    current = [r for r in all_rows if r[0] == 500 and r[1] == 100]
    if current:
        _, _, _, cr3, cr5, cmrr = current[0]
        print(f"  当前 Recall@3 = {cr3:.1%}, MRR@5 = {cmrr:.3f}")

    # 清理评估数据库
    shutil.rmtree("eval_chroma", ignore_errors=True)


if __name__ == "__main__":
    main()
