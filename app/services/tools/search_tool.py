from langchain_core.tools import tool

from app.services.hyde import hyde_plus_rerank_bm25_retrieve
import logging


@tool
def search_knowledge_base(query: str) -> str:
    """在企业知识库中搜索文档内容。

    内部流程：自动完成 HyDE 语义扩展 → 向量检索 + BM25 关键词检索 → 去重 → Rerank 重排序。
    返回：top-3 最相关文档片段。

    ✅ 必须调用的情况：
    - "XX文档里怎么说的"
    - "有没有关于XX的资料"
    - "知识库里XX是什么"

    ❌ 不要调用的情况：
    - "今天天气怎么样"（知识库没有）
    - "帮我写一段代码"（这是生成任务，不是检索）
    - 用户只是闲聊
    """
    logger = logging.getLogger("rag.tools")
    logger.info("Agent 调用了 search_knowledge_base | query=%s", query)

    # 复用假想文本生成（已包含 HyDE + 向量 + BM25 + Rerank 全流程）
    return hyde_plus_rerank_bm25_retrieve(query)
