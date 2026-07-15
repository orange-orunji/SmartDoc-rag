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
def send_email(to : str = "", subject : str = "", body : str = "", attachment : str = "") :
    """

    参数：
    - to: 收件人邮箱
    - subject: 邮件主题
    - body: 邮件正文
    - attachment: 附件文件名（可选），如 "Java_1784020972.md"

    适用场景：用户说"发邮件"、"发送给XX"、"把报告发过去"
    不适用场景：用户询问具体的文档内容——此时应使用 search_knowledge_base。
    :return:
    """
    s = get_settings()
    #     流程：
    #       1. 用 smtplib 连接 SMTP 服务器
    import smtplib
    smtp_obj = smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT)
    smtp_obj.starttls()
    smtp_obj.login(s.SMTP_USER, s.SMTP_PASSWORD)

    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    #       2. 构建 MIMEMultipart 邮件（支持正文 + 附件）
    msg = MIMEMultipart()
    msg["From"] = s.SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    from email import encoders
    from email.mime.base import MIMEBase
    #       3. 如果有附件，从 report 目录读取并附加
    if attachment:
        file_path = f"{s.REPORT_FILE_PATH}/{attachment}"
        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")  # 通用二进制类型
            part.set_payload(f.read())                      # 读入原始字节
            encoders.encode_base64(part)                    # 转 Base64
            part.add_header("Content-Disposition", f"attachment; filename={attachment}")
            msg.attach(part)                                # 附加附件

    #       4. 发送邮件
    smtp_obj.sendmail(s.SMTP_USER, to, msg.as_string())
    smtp_obj.quit()
    return f"邮件已发送至 {to}，主题：{subject}"


@tool
def convert_format(filename : str = "", target_format : str = "") :
    """转换报告文件格式。

    参数：
    - filename: 源文件名（如 Redis_1784021277.md）
    - target_format: 目标格式（"docx"/"md"/"txt"）

    适用场景：用户说"把这个转成 Word"、"导出为 txt"等。
    """

    # 1. 从 app/data/report/ 读取源文件
    s = get_settings()
    with open(f"{s.REPORT_FILE_PATH}/{filename}", "r", encoding="utf-8") as f:
        content = f.read()

    filename = filename.split("_",1)[0]
    out_filename = f"{filename}.{target_format}"
    out_path = f"{s.REPORT_FILE_PATH}/{out_filename}"
  # 2. 根据格式转换
    import re

    def _strip_markdown(text: str) -> str:
        """清洗 Markdown 语法，转为纯文本"""
        t = text
        t = re.sub(r'^#{1,6}\s*', '', t)
        t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
        t = re.sub(r'\*(.+?)\*', r'\1', t)
        t = re.sub(r'`(.+?)`', r'\1', t)
        t = re.sub(r'^\s*[-*+]\s', '', t)
        t = re.sub(r'^\s*\d+\.\s', '', t)
        if t.strip().startswith('|'):
            t = '  '.join(c.strip() for c in t.split('|') if c.strip())
        return t

    if target_format == "docx":
        from docx import Document
        doc = Document()
        for line in content.split("\n"):
            cleaned = _strip_markdown(line)
            if cleaned.strip():
                doc.add_paragraph(cleaned)
        doc.save(out_path)
    elif target_format == "txt":
        # txt 也清洗 Markdown → 真正纯文本
        cleaned_lines = [_strip_markdown(l) for l in content.split("\n") if _strip_markdown(l).strip()]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(cleaned_lines))
    elif target_format == "md":
        # md 保持原样
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

  # 3. 返回 [REPORT_FILE] 标记 → chat.py 自动推送下载按钮
    return f"[REPORT_FILE]{out_filename}\n报告已生成，可点击下载：/reports/{out_filename}"

@tool
def schedule_task() :
    """TODO"""
    pass