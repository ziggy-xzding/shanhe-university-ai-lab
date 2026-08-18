"""按小说章节切分文本，并为每个切片补齐来源元数据。"""

from html import unescape
import re
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter


CHAPTER_PATTERN = re.compile(
    r"(?m)^(第[零〇一二三四五六七八九十百千兩两0-9]+回[^\r\n]*)\s*$"
)
SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", "，", ",", " ", ""]


def clean_text(text: str) -> str:
    """去除网页标签与冗余空白，保留正文和章节换行。"""
    if not isinstance(text, str):
        raise TypeError("text 必须是 str")
    value = unescape(text.replace("\ufeff", ""))
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"(?i)</?p[^>]*>", "\n", value)
    # 只删除形如 <span ...> 的单行 HTML 标签。不能使用 <[^>]+>，
    # 否则小说正文中的普通“小于号”可能一直吞到很远处的下一个大于号。
    value = re.sub(r"</?[A-Za-z][^>\r\n]{0,200}>", "", value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[\t\u00a0]+", " ", value)
    value = re.sub(r"[ ]{2,}", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


class TextChunker:
    """使用 RecursiveCharacterTextSplitter 的章节感知切片器。"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须大于等于 0 且小于 chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=SEPARATORS,
            length_function=len,
        )

    @staticmethod
    def _chapter_sections(text: str) -> list[tuple[str, str]]:
        matches = list(CHAPTER_PATTERN.finditer(text))
        if not matches:
            return [("", text)]

        sections: list[tuple[str, str]] = []
        prefix = text[: matches[0].start()].strip()
        if prefix:
            sections.append(("前言", prefix))

        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            chapter = match.group(1).strip()
            body = text[match.end() : end].strip()
            if body:
                sections.append((chapter, body))
        return sections

    def split(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict]:
        """返回包含 content、chapter、source 等字段的切片列表。"""
        normalized = clean_text(text)
        if not normalized:
            return []
        base = dict(metadata or {})
        chunks: list[dict] = []
        for chapter, section in self._chapter_sections(normalized):
            for content in self._splitter.split_text(section):
                content = content.strip()
                if not content:
                    continue
                item = {
                    **base,
                    "content": content,
                    "book_name": str(base.get("book_name", "")),
                    "chapter": chapter or str(base.get("chapter", "")),
                    "source": str(base.get("source", "")),
                    "chunk_index": len(chunks),
                    "char_count": len(content),
                }
                chunks.append(item)
        return chunks

    def split_text(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict]:
        """兼容直观方法名。"""
        return self.split(text, metadata)
