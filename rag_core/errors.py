"""RAG 模块的领域异常。"""


class RAGError(RuntimeError):
    """RAG 模块基础异常。"""


class RAGConfigurationError(RAGError):
    """配置缺失或配置值无效。"""


class RAGServiceUnavailableError(RAGError):
    """Milvus 或模型服务不可用。"""


class DocumentParseError(RAGError):
    """文档无法解析。"""
