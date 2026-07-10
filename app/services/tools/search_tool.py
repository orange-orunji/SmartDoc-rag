from langchain_core.tools import tool
from app.services.llm import get_rag_chain


@tool
def search_knowledge_base(query: str) -> str:
    """搜索企业知识库，返回最相关的文档内容。

    内部自动执行 HyDE 语义扩展 → 向量检索 + BM25 关键词检索 → 结果合并 → Rerank 重排序，
    最终返回精选后的 top-3 文档片段。

    适用场景：所有知识库问答，包括概念性问题（如"什么是 JVM"）和精确术语查找（如"HashMap 的 put 方法"）。
    不适用场景：闲聊、查询天气等知识库外的内容。
    """
    # 复用现有的 RAG 链（已包含 HyDE + 向量 + BM25 + Rerank 全流程）
    chain = get_rag_chain(user_id="agent")
    result = chain.invoke({"input": query})
    return result
