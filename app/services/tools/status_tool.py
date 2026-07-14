import time

from langchain_core.tools import tool

from app.services.hyde import llm, hyde_plus_rerank_bm25_retrieve
from app.services.vector_store import vector_store_service as vss
from app.config.settings import get_settings


@tool
def get_document_status(keyword: str = "") -> str:
    """查询知识库统计信息。

    返回当前知识库中的文档总数、各文档的分块数和上传时间。

    参数 keyword：可选，按文件名关键词过滤。
    - 传 "java" → 只显示文件名包含 java 的文档
    - 不传或传 "" → 显示全部文档

    适用场景：用户询问"知识库有什么"、"有多少文档"、"有没有关于XX的文档"等问题时。
    不适用场景：用户询问具体的文档内容——此时应使用 search_knowledge_base。
    """
    documents = vss.get_all_documents()
    if not documents:
        return "知识库中暂无任何文档。"

    # 按文件名（metadata.source）分组
    file_map: dict[str, dict] = {}
    for doc in documents:
        source = doc.metadata.get("source", "未知文件")
        # 关键词过滤：keyword 非空时跳过不匹配的文件
        if keyword and keyword.lower() not in source.lower():
            continue
        if source not in file_map:
            file_map[source] = {
                "chunk_count": 0,
                "create_time": doc.metadata.get("create_time", "未知"),
            }
        file_map[source]["chunk_count"] += 1

    if not file_map:
        return f"知识库中未找到文件名包含「{keyword}」的文档。"

    # 拼接 LLM 可读的文本
    header = f"知识库统计信息（关键词：{keyword}）：" if keyword else "知识库统计信息："
    lines = [header, f"- 文档总数：{len(file_map)}", ""]
    for i, (filename, info) in enumerate(file_map.items(), 1):
        lines.append(f"  {i}. {filename}")
        lines.append(f"     分块数：{info['chunk_count']}  |  上传时间：{info['create_time']}")

    return "\n".join(lines)

@tool
def generate_report(topic : str = "", format : str = "md") :
    """查询知识库生成报告

    返回当前知识库中和 当前行为相符的总结文档操作

    参数：
    - topic: 报告主题关键词
    - format: 输出格式，"md" 或 "pdf"
    - 传 "java" → 只显示文件名包含 java 的文档
    - 不传或传 "" → 显示全部文档

    适用场景：用户询问"帮我总结一份关于XXX知识的文档"、"总结一份假期（其他事务）相关的PDF/md文档"等问题时。
    不适用场景：用户询问具体的文档内容——此时应使用 search_knowledge_base。

    :return:
    """
    # 1. 检索
    basa_context = hyde_plus_rerank_bm25_retrieve(topic)

    # 2.LLM 汇总
    content  = "\n".join(doc.page_content for doc in basa_context)
    result = llm.invoke(input="请帮我根据以下资料进行总结：" + content)

    s = get_settings()
    # 3.保存文件
    filename = f"{topic}_{int(time.time())}.{format}"
    filepath  = f"{s.REPORT_FILE_PATH}/{filename}"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result.content)
    return f"[REPORT_FILE]{filename}\n报告已生成，可点击下载：/reports/{filename}"

@tool
def send_email() :
    """TODO"""
    pass


@tool
def convert_format() :
    """TODO"""
    pass

@tool
def schedule_task() :
    """TODO"""
    pass