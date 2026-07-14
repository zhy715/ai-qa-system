"""文档解析与分块服务 —— 支持 PDF / TXT / MD / DOCX / CSV / HTML"""
import csv
import io
import os
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


class DocumentChunk:
    """文档分块"""

    def __init__(self, content: str, metadata: dict):
        self.content = content
        self.metadata = metadata


# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".csv", ".html", ".htm"}


class DocumentService:
    """文档服务：多格式文档解析 + 文本分块"""

    # 网格搜索最优参数（在 24914 字学术论文上评估得出）
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 50

    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)

    # ─── 各格式解析器 ─────────────────────────────────

    def _parse_pdf(self, path: str) -> str:
        reader = PdfReader(path)
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts)

    def _parse_txt(self, path: str) -> str:
        # 尝试多种编码
        for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
            try:
                with open(path, encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return ""

    def _parse_docx(self, path: str) -> str:
        try:
            from docx import Document
            doc = Document(path)
            parts = []
            # 段落文字
            for p in doc.paragraphs:
                if p.text and p.text.strip():
                    parts.append(p.text.strip())
            # 表格文字
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        parts.append(row_text)
            return "\n".join(parts)
        except Exception as e:
            raise ValueError(f"Word 文档解析失败: {e}")

    def _parse_csv(self, path: str) -> str:
        rows = []
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                with open(path, encoding=enc, newline="") as f:
                    reader = csv.reader(f)
                    for r in reader:
                        rows.append(" | ".join(r))
                break
            except (UnicodeDecodeError, csv.Error):
                continue
        return "\n".join(rows)

    def _parse_html(self, path: str) -> str:
        from bs4 import BeautifulSoup
        for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
            try:
                with open(path, encoding=enc) as f:
                    soup = BeautifulSoup(f.read(), "lxml")
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        # 移除 script / style 标签
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    # ─── 统一入口 ─────────────────────────────────────

    def parse_file(self, file_path: str, filename: str) -> str:
        """根据扩展名自动选择解析器，返回纯文本"""
        ext = os.path.splitext(filename)[1].lower()
        parsers = {
            ".pdf": self._parse_pdf,
            ".txt": self._parse_txt,
            ".md": self._parse_txt,
            ".docx": self._parse_docx,
            ".csv": self._parse_csv,
            ".html": self._parse_html,
            ".htm": self._parse_html,
        }
        parser = parsers.get(ext)
        if parser is None:
            raise ValueError(f"不支持的文件格式: {ext}")
        try:
            return parser(file_path)
        except ValueError:
            raise  # 重新抛出已包装的错误
        except Exception as e:
            raise ValueError(f"文档解析失败（{ext}）: {e}")

    # ─── 文本分块 ─────────────────────────────────────

    def chunk_text(self, text: str, filename: str) -> List[DocumentChunk]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
            length_function=len,
        )
        chunks = splitter.split_text(text)
        return [
            DocumentChunk(content=c, metadata={"source": filename, "chunk_index": i})
            for i, c in enumerate(chunks)
        ]

    # ─── 一站式处理 ───────────────────────────────────

    def process_file(self, file_path: str, filename: str) -> List[DocumentChunk]:
        """解析 + 分块，一站式"""
        text = self.parse_file(file_path, filename)
        if not text.strip():
            return []
        return self.chunk_text(text, filename)

    # ─── 兼容旧方法名 ─────────────────────────────────

    def parse_pdf(self, path: str) -> str:
        return self._parse_pdf(path)

    def process_pdf(self, file_path: str, filename: str) -> List[DocumentChunk]:
        return self.process_file(file_path, filename)
