from langchain_core.tools import tool

@tool(description="假想文档生成工具(HyDE)。"
                  "根据用户问题生成一段假设的相关文档内容，这段假想文档可作为 vector_search 的输入来提升语义检索精度。"
                  "适用场景：问题较短或表述不精确时，先生成假想文档再检索。")
def generate_hypothetical_doc() :
    pass