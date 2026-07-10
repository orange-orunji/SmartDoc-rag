from langchain_core.tools import tool

@tool(description="知识库统计工具。返回当前知识库中的文档总数、各类型文档数量、最后更新时间等统计信息。"
                  "适用场景：用户询问'知识库有什么'、'有多少文档'等问题时。"
)
def rerank_documents() -> str :
    pass