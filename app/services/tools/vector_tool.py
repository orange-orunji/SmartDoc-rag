from langchain_core.tools import tool

@tool(description="语义向量检索工具。"
                  "根据查询语句在知识库中搜索语义相似的文档片段。"
                  "适用场景：用户问概念性问题、需要理解语义的问题（如'什么是XXX'、'XXX的原理是什么'）。"
                  "不适用场景：精确关键词匹配（如'XXX函数签名'），此时应使用 keyword_search。"
)
def vector_search(query : str) -> str:
    pass