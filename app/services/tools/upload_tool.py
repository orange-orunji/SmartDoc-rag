from langchain_core.tools import tool


@tool
def upload_document(filename: str, content: str) -> str:
    """上传文档到企业知识库。

    将用户提供的文档内容（支持 txt、docx、pdf、md 格式）异步上传到知识库，
    后台自动完成文本解析、分块、向量化入库，并返回上传任务 ID 供追踪进度。

    适用场景：用户明确表示要存储/上传一份文档时，如"帮我把这份文件存起来"、"把这个文档加到知识库"。
    不适用场景：用户只是讨论文档内容而非上传——此时应使用 search_knowledge_base。
    """
    pass
