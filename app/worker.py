import asyncio

from app.utils.rabbitmq import rabbitmq
from app.utils.redis_client import get_redis
from app.utils.task_status import TaskTracker, TaskStatus
from app.services.document import _extract_text
from app.services.KnowledgeBase_md5_service import KnowledgeBaseService
from app.services.vector_store import vector_store_service
from app.services.bm25_service import BM25Service

from pathlib import Path


async def handle_document_upload(payload: dict):
    """消息队列异步处理文档上传任务"""
    task_id = payload["task_id"]
    filename = payload["filename"]
    user_id = payload.get("user_id", "system")

    redis = get_redis()
    content_hex = redis.get(f"file:content:{task_id}") if redis else None
    if not content_hex:
        TaskTracker.set_status(task_id, TaskStatus.FAILED, {"error": "文件内容已过期或丢失"})
        return
    content = bytes.fromhex(content_hex)
    # 取完后立即删除，释放内存
    redis.delete(f"file:content:{task_id}")

    TaskTracker.set_status(task_id, TaskStatus.PROCESSING)

    try:
        # 1. 解析文本
        suffix = Path(filename).suffix.lower()
        text = await _extract_text(content, suffix)

        if not text.strip():
            TaskTracker.set_status(task_id, TaskStatus.FAILED, {"error": "文件内容为空"})
            return

        # 2. 向量化存储
        kb_service = KnowledgeBaseService()
        result = kb_service.upload_by_str(text, filename, user_id=user_id)

        # 3. 重建 BM25 索引
        all_docs = vector_store_service.get_all_documents()
        BM25Service().build_index(all_docs)

        TaskTracker.set_status(task_id, TaskStatus.COMPLETED, {"filename": filename})

    except Exception as e:
        TaskTracker.set_status(task_id, TaskStatus.FAILED, {"error": str(e)})


async def main():
    await rabbitmq.connect()
    print("Worker 已启动，等待任务...")
    await rabbitmq.consume(
        queue_name="document.upload.queue",
        routing_keys=["document.upload"],
        callback=handle_document_upload,
        prefetch_count=2,  # 并发处理 2 个任务
    )


if __name__ == "__main__":
    asyncio.run(main())
