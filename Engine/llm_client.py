"""DeepSeek chat client used by the agents and the local RAG pipeline."""

import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")

RAG_PROMPT = """你是山河大学知识检索助手。只能依据提供的参考内容回答。
先说明答案来自哪一本或哪几本书，再给出简洁、自然的解释；参考不足时明确说明知识库没有足够依据，不要编造章节或事实。

参考内容：
{context}

用户问题：
{question}
"""


class LLMClient:
    """DeepSeek chat completion client."""

    def __init__(self, api_key: str | None = None):
        load_dotenv()
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY", "")
        if not self._api_key:
            raise RuntimeError("缺少 DEEPSEEK_API_KEY，请在 .env 中配置 DeepSeek API Key")
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=os.getenv("LLM_BASE_URL", BASE_URL).rstrip("/"),
            timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
        )

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 1000,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=os.getenv("LLM_MODEL", LLM_MODEL),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        answer = response.choices[0].message.content or ""
        if not answer.strip():
            raise RuntimeError("DeepSeek 返回了空答案")
        return answer.strip()

    def stream(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 1000,
    ):
        """Yield answer text as soon as DeepSeek produces each content delta."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=os.getenv("LLM_MODEL", LLM_MODEL),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None) if delta else None
            if content:
                yield content

    def generate_rag_answer(self, question: str, contexts: list[dict], temperature: float = 0.3) -> str:
        context_parts = []
        for index, ctx in enumerate(contexts, start=1):
            source = ctx.get("book_name") or ctx.get("source") or f"参考片段{index}"
            chapter = ctx.get("chapter") or ctx.get("page") or "未标注位置"
            text = ctx.get("content") or ctx.get("text") or ""
            context_parts.append(f"【{source} / {chapter}】\n{text}")
        return self.generate(
            RAG_PROMPT.format(context="\n\n---\n\n".join(context_parts), question=question),
            system="你是严谨的大学图书知识库问答助手。",
            temperature=temperature,
            max_tokens=1200,
        )


_llm_instance: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient()
    return _llm_instance
