import json
import uuid
from pathlib import Path

from langchain_core.tools import tool

from app.api.auth import current_user_ctx
from app.config.settings import get_settings
from app.services.KnowledgeBase_md5_service import KnowledgeBaseService
from app.services.bm25_service import BM25Service
from app.services.vector_store import vector_store_service
from app.utils.rabbitmq import rabbitmq
from app.utils.redis_client import get_redis
from app.utils.task_status import TaskTracker, TaskStatus


@tool
async def upload_document(rep_input: str):
    """
    上传文档到企业知识库。

    将用户提供的文档内容（支持 txt、docx、pdf、md 格式）异步上传到知识库，
    后台自动完成文本解析、分块、向量化入库，并返回上传任务 ID 供追踪进度。

    适用场景：用户明确表示要存储/上传一份文档时，如"帮我把这份文件存起来"、"把这个文档加到知识库"。
    不适用场景：用户只是讨论文档内容而非上传——此时应使用 search_knowledge_base。

    参数说明：
    - filename: 文档名称（用户指定的文件名，如"简历整理笔记"）
    - content: 文档的完整文本内容（用户要求存储的原文，不要省略或改写）

    """
    # 兼容两种传参方式：JSON 和纯文本（filename\ncontent）
    try:
        loads = json.loads(rep_input, strict=False)
        filename = loads["filename"]
        content = loads["content"]
    except (json.JSONDecodeError, KeyError):
        # LLM 直接传了 "文件名.md\n\n内容..." 的纯文本
        parts = rep_input.split("\n", 1)
        filename = parts[0].strip()
        content = parts[1].strip() if len(parts) > 1 else rep_input

    # 确保 filename 有合法后缀（Worker 按后缀选解析器，无后缀默认当 .txt）
    s = get_settings()
    suffix = Path(filename).suffix.lower()
    if suffix not in s.ALLOWED_SUFFIXES:
        filename = filename + ".txt"

    user_id = current_user_ctx.get()
    task_id = uuid.uuid4().hex

    # 内容存 Redis（600s 过期），Worker 取走时用 bytes.fromhex 还原原始字节
    redis = get_redis()
    if redis:
        redis.setex(f"file:content:{task_id}", 600, content.encode("utf-8").hex())

    TaskTracker.set_status(task_id, TaskStatus.PENDING, {"filename": filename})

    try:
        await rabbitmq.publish("document.upload", {
            "task_id": task_id,
            "filename": filename,
            "user_id": user_id,
        })
    except Exception:
        # RabbitMQ 不可用时降级为同步处理
        KnowledgeBaseService().upload_by_str(content, filename, user_id=user_id)
        BM25Service().build_index(vector_store_service.get_all_documents())
        return f"文档 {filename} 已同步入库（消息队列不可用，降级处理）"

    return f"文档{filename}已提交异步处理，任务 ID：{task_id}"

