"""DeepSeek RAG 答案生成客户端。"""

from typing import Any

from openai import OpenAI

from rag_core.config import RAGSettings, get_settings
from rag_core.errors import RAGConfigurationError, RAGServiceUnavailableError


SYSTEM_PROMPT = """你是《三国演义》知识问答助手。
你只能依据用户消息中提供的“问答参考”和“原文参考”回答，不得混入其他名著或外部知识。
如果参考内容不足，请回答“当前知识库中没有足够依据回答该问题”。
回答应简洁、准确，并在相关陈述后标注参考编号，例如 [问答1] 或 [文档2]。
不要输出内部思维过程，不要捏造章节、人物或情节。"""


class LLMClient:
    def __init__(
        self,
        settings: RAGSettings | None = None,
        *,
        client: Any | None = None,
    ):
        self.settings = settings or get_settings()
        if client is not None:
            self._client = client
        else:
            if not (self.settings.llm_api_key or self.settings.dashscope_api_key):
                raise RAGConfigurationError(
                    "缺少 DEEPSEEK_API_KEY，请在 .env 中配置 DeepSeek API Key"
                )
            self._client = OpenAI(
                api_key=self.settings.llm_api_key or self.settings.dashscope_api_key,
                base_url=self.settings.llm_base_url or self.settings.dashscope_base_url,
                timeout=20,
            )

    @staticmethod
    def build_context(qa_sources: list[dict], document_sources: list[dict]) -> str:
        parts: list[str] = []
        for index, item in enumerate(qa_sources, start=1):
            parts.append(
                "\n".join(
                    [
                        f"[问答{index}] 来源：{item.get('source_chapter') or '三国演义'}",
                        f"问题：{item.get('question', '')}",
                        f"答案：{item.get('answer', '')}",
                        f"说明：{item.get('explanation', '')}",
                        f"依据：{item.get('evidence', '')}",
                    ]
                )
            )
        for index, item in enumerate(document_sources, start=1):
            parts.append(
                "\n".join(
                    [
                        f"[文档{index}] 来源：{item.get('book_name', '')} / {item.get('chapter') or '未标注章节'}",
                        item.get("content") or item.get("text", ""),
                    ]
                )
            )
        return "\n\n---\n\n".join(parts)

    def generate_rag_answer(
        self,
        question: str,
        qa_sources: list[dict],
        document_sources: list[dict],
    ) -> str:
        context = self.build_context(qa_sources, document_sources)
        if not context:
            return "当前知识库中没有足够依据回答该问题。"
        try:
            response = self._client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"参考内容：\n{context}\n\n用户问题：{question}",
                    },
                ],
                temperature=0.2,
                max_tokens=1200,
            )
            answer = response.choices[0].message.content
            if not answer or not answer.strip():
                raise ValueError("模型返回空答案")
            return answer.strip()
        except Exception as exc:
            raise RAGServiceUnavailableError(f"调用 DeepSeek 生成答案失败：{exc}") from exc

    def generate_growth_reply(self, system_prompt: str, user_prompt: str) -> str:
        """生成学生成长陪伴回复，调用失败由上层服务降级。"""
        try:
            response = self._client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
                max_tokens=700,
            )
            answer = response.choices[0].message.content
            if not answer or not answer.strip():
                raise ValueError("模型返回空答案")
            return answer.strip()
        except Exception as exc:
            raise RAGServiceUnavailableError(f"调用 DeepSeek 成长 Agent 失败：{exc}") from exc
