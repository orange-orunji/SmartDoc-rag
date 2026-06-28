import uuid

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from app.schemas.response import UnifiedResponse
from app.services.document import validate_upload
from app.utils.auth import get_current_user
from app.utils.rabbitmq import rabbitmq
from app.utils.redis_client import get_redis
from app.utils.task_status import TaskTracker, TaskStatus

router = APIRouter()


@router.post("/upload", summary="异步上传文件", description="支持 .txt, .docx, .pdf, .md 格式，自动去重、分割、向量化存储")
async def document_upload(file: UploadFile = File(..., description="待上传的文件"), current_user: dict = Depends(get_current_user)) -> UnifiedResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # ★ 仅做校验（大小、格式），不处理内容
    error = validate_upload(content, file.filename)
    if error:
        return error

    task_id = uuid.uuid4().hex

    # ★ 文件内容存入 Redis（600秒过期），消息体只传元数据
    redis = get_redis()
    if redis:
        redis.setex(f"file:content:{task_id}", 600, content.hex())

    TaskTracker.set_status(task_id, TaskStatus.PENDING, {"filename": file.filename})

    await rabbitmq.publish("document.upload", {
        "task_id": task_id,
        "filename": file.filename,
        "user_id": current_user["user_id"],
    })

    return UnifiedResponse.success(
        code=202,
        data={"task_id": task_id},
        message=f"文件 {file.filename} 已接收，正在异步处理中"
    )

@router.get("/upload/status/{task_id}", summary="查询上传任务状态")
async def get_upload_status(task_id: str) -> UnifiedResponse:
    status = TaskTracker.get_status(task_id)
    if not status:
        return UnifiedResponse(code=404, message="任务不存在或已过期")
    return UnifiedResponse.success(data=status)