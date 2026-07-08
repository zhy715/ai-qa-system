"""向量数据库服务"""
import os
from typing import List, Dict, Any

import chromadb
from chromadb.utils import embedding_functions


class VectorService:
    """向量数据库服务：负责文档的向量化存储和检索

    使用 ChromaDB + 多语言 sentence-transformers 模型，支持中英文语义检索。
    """

    MULTILINGUAL_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, persist_dir: str = "chroma_db"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir)

        # 多语言嵌入模型（支持中文 + 50+ 语言）
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.MULTILINGUAL_MODEL,
        )

        # 集合名加上模型后缀，避免和旧英文模型的向量维度不兼容
        collection_name = "knowledge_base_multilingual"
        try:
            self.client.delete_collection("knowledge_base")
        except Exception:
            pass

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "AI知识库（多语言）", "model": self.MULTILINGUAL_MODEL},
        )

    def add_documents(self, chunks: List[Any]) -> int:
        """将文档分块存入向量数据库"""
        if not chunks:
            return 0

        # 过滤掉空白分块，避免 ChromaDB 报错
        valid = [
            (i, chunk)
            for i, chunk in enumerate(chunks)
            if chunk.content and chunk.content.strip()
        ]
        if not valid:
            return 0

        base = self.collection.count()
        ids = [f"chunk_{base + j}" for j in range(len(valid))]
        documents = [chunk.content.strip() for _, chunk in valid]
        metadatas = [chunk.metadata for _, chunk in valid]

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        return len(valid)

    def query(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """根据问题检索最相关的文档片段"""
        results = self.collection.query(
            query_texts=[question],
            n_results=top_k,
        )

        # 整理返回结果
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        return {
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances,
        }

    def get_all_sources(self) -> List[str]:
        """获取所有已存储的文档来源"""
        if self.collection.count() == 0:
            return []

        result = self.collection.get()
        metadatas = result.get("metadatas", [])
        sources = set()
        for meta in metadatas:
            if meta and "source" in meta:
                sources.add(meta["source"])
        return list(sources)

    def count(self) -> int:
        """返回当前存储的分块数量"""
        return self.collection.count()
