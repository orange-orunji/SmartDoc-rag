from langchain_core.tools import tool

from app.config.settings import get_settings
from app.services.vector_store import vector_store_service
from app.services.bm25_service import bm25_service
from app.services.KnowledgeBase_md5_service import delete_md5
"""删除工具"""

@tool
def delete_document(filename: str = "") -> str:
    """在企业知识库中删除文档内容。

    参数：
        filename: 文件名

    返回：
        删除结果

    适用场景：删除文件，从企业知识库中删除指定文件，释放空间，或者删除错误上传的文件
    不适用场景：删除单个文件的某一部分内容，因为工具只能删除整个文件，不能删除文件中的某一部分内容
    """
    s = get_settings()
    result = vector_store_service.chroma.get(where={"source": filename})
    if not result["ids"]:
        return f"文件：{filename} 不存在"
    # ① 删除 Chroma 中的全部切片
    vector_store_service.chroma.delete(where={"source": filename})
    # ② 清理 MD5 记录（同一文件的所有切片共享同一 md5，去重后逐条删除）
    md5s = {meta["md5"] for meta in result["metadatas"]}
    for m in md5s:
        delete_md5(s.MD5_PATH, m)
    # ③ 重建 BM25 索引
    bm25_service.build_index(vector_store_service.get_all_documents())
    return f"已删除文件：{filename}"


