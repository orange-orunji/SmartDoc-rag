from pathlib import Path

from app.schemas.document import upload_document
from app.schemas.response import UnifiedResponse
from app.services.document import upload_documents
from fastapi import APIRouter,File,UploadFile
router = APIRouter()

@router.post("/upload")
async def document_upload(files : list[UploadFile] = File(...)) -> UnifiedResponse:
  """
    多文件上传接口
    支持去重、分割、向量化存储  :param document:单个文件
  :return: UnifiedResponse响应体
  """
  results = []

  for document in files:
    #   读取文件内容
    content = await  document.read()
    # 异步委托给服务层处理
    result = await upload_documents(content,document.filename)
    results.append(result)
  return UnifiedResponse.success(code=200,data=results,message="[Success] Upload Succeeded")