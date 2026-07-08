"""文档解析与分块服务"""
import os
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


class DocumentChunk:
    """文档分块"""

    def __init__(self, content: str, metadata: dict):
        self.content = content
        self.metadata = metadata


class DocumentService:
    """文档服务：负责 PDF 解析和文本分块"""

    # 分块参数
    CHUNK_SIZE = 500       # 每个文本块的最大字符数
    CHUNK_OVERLAP = 100    # 相邻块之间的重叠字符数

    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)

    def parse_pdf(self, file_path: str) -> str:
        """解析 PDF 文件，提取全部文字"""
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)

    def chunk_text(self, text: str, filename: str) -> List[DocumentChunk]:
        """将长文本切分成适合检索的小块"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
            length_function=len,
        )

        chunks = splitter.split_text(text)
        return [
            DocumentChunk(
                content=chunk,
                metadata={"source": filename, "chunk_index": i},
            )
            for i, chunk in enumerate(chunks)
        ]

    def process_pdf(self, file_path: str, filename: str) -> List[DocumentChunk]:
        """处理 PDF 文件：解析 + 分块，一站式"""
        text = self.parse_pdf(file_path)
        if not text.strip():
            return []
        return self.chunk_text(text, filename)
