"""启动时扫描 builtin_docs/，自动将新文档索引入库"""
import logging
import os

from app.services.document_service import DocumentService, SUPPORTED_EXTENSIONS
from app.services.vector_service import VectorService

logger = logging.getLogger("lvda.seed")


class SeedService:
    """内置文档种子服务 —— 启动时扫描 builtin_docs/ 目录，将未入库的新文档自动索引"""

    def __init__(
        self,
        builtin_dir: str,
        doc_service: DocumentService,
        vec_service: VectorService,
    ):
        self.builtin_dir = builtin_dir
        self.doc_service = doc_service
        self.vec_service = vec_service
        os.makedirs(builtin_dir, exist_ok=True)

    def seed(self) -> int:
        """扫描 builtin_docs/，索引新文档，返回新增分块总数"""
        if not os.path.isdir(self.builtin_dir):
            logger.warning("内置文档目录不存在: %s", self.builtin_dir)
            return 0

        existing_sources = set(self.vec_service.get_all_sources())
        files = [
            f for f in os.listdir(self.builtin_dir)
            if os.path.isfile(os.path.join(self.builtin_dir, f))
            and os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
        ]

        new_files = [f for f in files if f not in existing_sources]
        if not new_files:
            logger.info("内置文档: 全部已索引 (%d 个文件)", len(files))
            return 0

        total_chunks = 0
        for filename in new_files:
            file_path = os.path.join(self.builtin_dir, filename)
            try:
                chunks = self.doc_service.process_file(
                    file_path, filename, source_type="builtin"
                )
                if chunks:
                    n = self.vec_service.add_documents(chunks)
                    total_chunks += n
                    logger.info(
                        "内置文档入库: %s → %d 块", filename, n
                    )
                else:
                    logger.warning("内置文档无内容: %s", filename)
            except Exception as e:
                logger.error("内置文档处理失败: %s, 错误: %s", filename, str(e))

        logger.info("内置文档索引完成: 新增 %d 块 (%d 个新文件)", total_chunks, len(new_files))
        return total_chunks
