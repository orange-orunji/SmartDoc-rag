from langchain_core.tools import tool


@tool(description="关键词检索工具(BM25)。"
                  "基于分词匹配在知识库中搜索包含关键词的文档片段。"
                  "适用场景：精确术语查找、函数名/API名搜索、代码片段搜索。不适用场景：语义理解类问题，"
                  "此时应使用 vector_search。")
def bm25_search(query : str) -> str:
    pass