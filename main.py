import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.chat import router as chat_router, limiter
from app.api.document import router as document_router
from app.api.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

from app.services import vector_store
from app.services.KnowledgeBase_md5_service import KnowledgeBaseService
from app.services.document import _extract_text
from app.services.vector_store import VectorStoreService
from app.services.bm25_service import BM25Service
from app.utils.SQL_database import engine, Base
from app.utils.rabbitmq import rabbitmq
from app.utils.redis_client import get_redis
from app.utils.task_status import TaskTracker, TaskStatus
from app.services.vector_store import vector_store_service as vs_svc
from app.config.settings import get_settings

# ── 日志系统初始化 ──
cfg = get_settings()

logging.basicConfig(
    level=getattr(logging, cfg.LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("rag")


async def _handle_document_upload(payload: dict):
    """消息队列异步处理文档上传任务（内嵌 Worker，带幂等防护）"""
    task_id = payload["task_id"]
    filename = payload["filename"]
    user_id = payload.get("user_id", "system")

    # ── 幂等性检查 ──
    idempotent_key = f"task:processed:{task_id}"
    redis = get_redis()
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
        suffix = Path(filename).suffix.lower()
        text = await _extract_text(content, suffix)
        if not text.strip():
            TaskTracker.set_status(task_id, TaskStatus.FAILED, {"error": "文件内容为空"})
            return
        kb_service = KnowledgeBaseService()
        kb_service.upload_by_str(text, filename, user_id=user_id)
        all_docs = vs_svc.get_all_documents()
        BM25Service().build_index(all_docs)
        if redis:
            redis.setex(idempotent_key, 86400, "1")
        TaskTracker.set_status(task_id, TaskStatus.COMPLETED, {"filename": filename})
        logger.info("文档处理完成 | task_id=%s", task_id)
    except Exception as e:
        logger.exception("文档处理失败 | task_id=%s", task_id)
        raise  # 让 RabbitMQ 重试机制接管


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = None
    mq_connected = False

    # ── RabbitMQ 连接（可选：开发环境不可用时不阻塞启动）──
    try:
        await rabbitmq.connect()
        mq_connected = True
        worker_task = asyncio.create_task(
            rabbitmq.consume(
                queue_name="document.upload.queue",
                routing_keys=["document.upload"],
                callback=_handle_document_upload,
                prefetch_count=2,
                max_retries=cfg.MQ_MAX_RETRIES,
                retry_delay=cfg.MQ_RETRY_DELAY_SECONDS,
            )
        )
        logger.info("RabbitMQ 已连接，内嵌 Worker 已启动")
    except Exception:
        logger.warning("RabbitMQ 不可用，文档异步上传功能将禁用")

    # ── 构建 BM25 索引 ──
    try:
        all_docs = VectorStoreService().get_all_documents()
    except AttributeError:
        from langchain_core.documents import Document
        all_docs = vector_store.chroma.get()
        all_docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(all_docs["documents"], all_docs["metadatas"])
        ]
    BM25Service().build_index(all_docs)
    Base.metadata.create_all(bind=engine)
    logger.info("BM25 索引构建完成，文档数: %d", len(all_docs))

    yield  # ← FastAPI 在此运行

    # ── 关闭时：取消 Worker 并断开 ──
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    if mq_connected:
        await rabbitmq.close()


app = FastAPI(title="RAG Personal API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(chat_router, prefix="/api/chat", tags=["对话接口"])
app.include_router(document_router, prefix="/api/document", tags=["上传文件接口"])
app.include_router(auth_router, prefix="/api/auth", tags=["用户登录注册相关接口"])


@app.get("/")
async def redirect_to_frontend():
    """根路径重定向到前端页面"""
    return RedirectResponse(url="/static/index.html")


# 静态文件服务（HTML 前端）
# ── 限流中间件 ──
if cfg.RATE_LIMIT_ENABLED:
    from slowapi.middleware import SlowAPIASGIMiddleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIASGIMiddleware)

app.mount("/static", StaticFiles(directory="app/static", html=True), name="static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("未捕获异常 | path=%s method=%s", request.url.path, request.method)
    if cfg.is_production:
        message = "服务器内部错误，请联系管理员"
    else:
        message = f"服务器内部错误: {str(exc)}"
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": message, "data": None}
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "RAG Personal API"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", reload=True)
