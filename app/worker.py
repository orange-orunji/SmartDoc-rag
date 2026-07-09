import asyncio
import logging
import sys

from app.utils.rabbitmq import rabbitmq
from app.utils.redis_client import get_redis
from app.utils.task_status import TaskTracker, TaskStatus
from app.services.document import _extract_text
from app.services.KnowledgeBase_md5_service import KnowledgeBaseService
from app.services.vector_store import vector_store_service
from app.services.bm25_service import BM25Service
from app.config.settings import get_settings

from pathlib import Path

# ── 独立 Worker 日志配置 ──
cfg = get_settings()
logging.basicConfig(
    level=getattr(logging, cfg.LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("rag.worker")

IDEMPOTENT_PREFIX = "task:processed:"  # 幂等键前缀
IDEMPOTENT_TTL = 86400  # 24 小时


async def handle_document_upload(payload: dict):
    """消息队列异步处理文档上传任务（带幂等防护）"""
    task_id = payload["task_id"]
    filename = payload["filename"]
    user_id = payload.get("user_id", "system")

    # ── 幂等性检查：防止同一任务重复处理 ──
    redis = get_redis()
    idempotent_key = f"{IDEMPOTENT_PREFIX}{task_id}"
    if redis and redis.exists(idempotent_key):
        logger.warning("重复消息已跳过 | task_id=%s", task_id)
        return

    content_hex = redis.get(f"file:content:{task_id}") if redis else None
    if not content_hex:
        TaskTracker.set_status(task_id, TaskStatus.FAILED, {"error": "文件内容已过期或丢失"})
        return
    content = bytes.fromhex(content_hex)
    redis.delete(f"file:content:{task_id}")

    TaskTracker.set_status(task_id, TaskStatus.PROCESSING)
    logger.info("开始处理文档 | task_id=%s | filename=%s", task_id, filename)

    try:
        # 1. 解析文本
        suffix = Path(filename).suffix.lower()
        text = await _extract_text(content, suffix)

        if not text.strip():
            TaskTracker.set_status(task_id, TaskStatus.FAILED, {"error": "文件内容为空"})
            return

        # 2. 向量化存储
        kb_service = KnowledgeBaseService()
        kb_service.upload_by_str(text, filename, user_id=user_id)

        # 3. 重建 BM25 索引
        all_docs = vector_store_service.get_all_documents()
        BM25Service().build_index(all_docs)

        # 4. 标记幂等 + 完成状态
        if redis:
            redis.setex(idempotent_key, IDEMPOTENT_TTL, "1")
        TaskTracker.set_status(task_id, TaskStatus.COMPLETED, {"filename": filename})
        logger.info("文档处理完成 | task_id=%s", task_id)

    except Exception as e:
        logger.exception("文档处理失败 | task_id=%s", task_id)
        # 不在这里标记幂等，允许重试
        raise  # 让 RabbitMQ 重试机制接管


async def main():
    await rabbitmq.connect()
    logger.info("Worker 已启动，等待任务...")
    await rabbitmq.consume(
        queue_name="document.upload.queue",
        routing_keys=["document.upload"],
        callback=handle_document_upload,
        prefetch_count=2,
        max_retries=cfg.MQ_MAX_RETRIES,
        retry_delay=cfg.MQ_RETRY_DELAY_SECONDS,
    )


if __name__ == "__main__":
    asyncio.run(main())
