from langchain_core.tools import tool


@tool
def get_document_status() -> str:
    """查询知识库统计信息。

    返回当前知识库中的文档总数、各类型文档数量、最后更新时间等统计信息。
    适用场景：用户询问"知识库有什么"、"有多少文档"、"最近更新了哪些"等问题时。
    不适用场景：用户询问具体的文档内容——此时应使用 search_knowledge_base。
    """
    pass
