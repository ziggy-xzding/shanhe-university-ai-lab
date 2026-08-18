"""PDF / 文本分块器（用于风电文档等新增知识库）"""
from langchain_text_splitters import RecursiveCharacterTextSplitter


CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SEPARATORS = ["\n\n", "\n", "。", ".", "！", "!", "？", "?", "；", ";", "，", ",", " ", ""]


class TextChunker:
    """通用文本分块器"""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=SEPARATORS,
            length_function=len,
        )

    def split_text(self, text: str) -> list[dict]:
        """切分文本 → [{content, chunk_index}]"""
        docs = self._splitter.create_documents(texts=[text])
        return [
            {"content": d.page_content, "chunk_index": i}
            for i, d in enumerate(docs)
        ]

    def split_with_metadata(self, text: str, meta: dict = None) -> list[dict]:
        """切分文本，每个 chunk 带元数据"""
        chunks = self.split_text(text)
        if meta:
            for c in chunks:
                c.update(meta.copy())
        return chunks
