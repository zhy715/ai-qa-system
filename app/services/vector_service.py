"""向量数据库服务"""
import os
from typing import List, Dict, Any

import chromadb
from chromadb.utils import embedding_functions


class VectorService:
    """向量数据库服务：负责文档的向量化存储和检索

    使用 ChromaDB 作为向量数据库，自带 ONNX 嵌入模型，无需 API Key。
    """

    def __init__(self, persist_dir: str = "chroma_db"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        # 创建持久化客户端
        self.client = chromadb.PersistentClient(path=persist_dir)

        # 使用内置的 ONNX 嵌入模型（all-MiniLM-L6-v2）
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self.embedding_fn,
            metadata={"description": "AI知识库"},
        )

    def add_documents(self, chunks: List[Any]) -> int:
        """将文档分块存入向量数据库"""
        if not chunks:
            return 0

        ids = [f"chunk_{self.collection.count() + i}" for i in range(len(chunks))]
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        return len(chunks)

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
