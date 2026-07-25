import asyncio
import logging
import sys

from app.utils.rabbitmq import rabbitmq
from app.utils.task_handler import handle_document_upload
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


async def handle_document_upload_service(payload: dict):
    """消息队列异步处理文档上传任务（带幂等防护）"""
    await handle_document_upload(payload)


async def main():
    await rabbitmq.connect()
    logger.info("Worker 已启动，等待任务...")
    await rabbitmq.consume(
        queue_name="document.upload.queue",
        routing_keys=["document.upload"],
        callback=handle_document_upload_service,
        prefetch_count=2,
        max_retries=cfg.MQ_MAX_RETRIES,
        retry_delay=cfg.MQ_RETRY_DELAY_SECONDS,
    )


if __name__ == "__main__":
    asyncio.run(main())
