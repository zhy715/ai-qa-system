"""文档解析服务测试"""
import os

from app.services.document_service import DocumentService, SUPPORTED_EXTENSIONS


class TestSupportedExtensions:
    def test_pdf_supported(self):
        assert ".pdf" in SUPPORTED_EXTENSIONS

    def test_docx_supported(self):
        assert ".docx" in SUPPORTED_EXTENSIONS

    def test_txt_supported(self):
        assert ".txt" in SUPPORTED_EXTENSIONS

    def test_html_supported(self):
        assert ".html" in SUPPORTED_EXTENSIONS
        assert ".htm" in SUPPORTED_EXTENSIONS


class TestDocumentService:
    def test_init_creates_dir(self, temp_dir):
        upload_dir = os.path.join(temp_dir, "uploads")
        service = DocumentService(upload_dir=upload_dir)
        assert os.path.isdir(upload_dir)

    def test_parse_txt_utf8(self, temp_dir):
        service = DocumentService(upload_dir=temp_dir)
        path = os.path.join(temp_dir, "sample.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("测试中文内容")
        text = service.parse_file(path, "sample.txt")
        assert "测试中文内容" in text

    def test_parse_txt_gbk(self, temp_dir):
        service = DocumentService(upload_dir=temp_dir)
        path = os.path.join(temp_dir, "gbk_sample.txt")
        with open(path, "w", encoding="gbk") as f:
            f.write("GBK编码测试")
        text = service.parse_file(path, "gbk_sample.txt")
        assert "GBK编码测试" in text

    def test_chunk_text(self, temp_dir):
        service = DocumentService(upload_dir=temp_dir)
        text = "这是第一句。\n这是第二句。\n这是第三句。\n这是第四句。\n这是第五句。"
        chunks = service.chunk_text(text, "test.txt")
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata["source"] == "test.txt"
            assert "chunk_index" in chunk.metadata

    def test_process_file(self, temp_dir):
        service = DocumentService(upload_dir=temp_dir)
        path = os.path.join(temp_dir, "doc.txt")
        content = "第一章 总则\n第一条 为了规范市场秩序，制定本法。\n第二条 本法适用于中华人民共和国境内。"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        chunks = service.process_file(path, "doc.txt")
        assert len(chunks) > 0
        assert all(c.metadata["source"] == "doc.txt" for c in chunks)

    def test_unsupported_format(self, temp_dir):
        service = DocumentService(upload_dir=temp_dir)
        with __import__("pytest").raises(ValueError):
            service.parse_file("dummy.xyz", "dummy.xyz")

    def test_html_uses_html_parser(self, temp_dir):
        """验证 HTML 文件使用 _parse_html 而非 _parse_txt"""
        from app.services.document_service import DocumentService as DS
        service = DS(upload_dir=temp_dir)
        path = os.path.join(temp_dir, "test.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write("<html><body><p>测试内容</p><script>alert(1)</script></body></html>")
        text = service.parse_file(path, "test.html")
        # HTML 解析器会去除 script 标签，但 _parse_txt 不会
        assert "alert" not in text
        assert "测试内容" in text
