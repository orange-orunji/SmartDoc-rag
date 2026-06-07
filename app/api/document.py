from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException
from app.schemas.response import UnifiedResponse
from app.services.document import upload_documents

router = APIRouter()


@router.post("/upload", summary="上传单个文件", description="支持 .txt, .docx, .pdf, .md 格式，自动去重、分割、向量化存储")
async def document_upload(file: UploadFile = File(..., description="待上传的文件")) -> UnifiedResponse:
    """
  单文件上传接口

  使用方式:
  - Swagger UI: 直接点击文件选择框选择单个文件
  - 多文件上传: 多次调用此接口，或使用 curl 批量上传

  示例 (curl 批量上传):
  curl -X POST http://127.0.0.1:8000/api/document/upload \
       -F 'file=@file1.txt' \
       -F 'file=@file2.pdf'
       -F 'file=@file2.pdf'
  """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    result = await upload_documents(content, file.filename)

    # 确保返回字典格式
    if hasattr(result, "model_dump"):
        result_data = result.model_dump()
    else:
        result_data = result

    return UnifiedResponse.success(
        code=200,
        data=result_data,
        message=f"[Success] {file.filename} 上传成功"
    )
