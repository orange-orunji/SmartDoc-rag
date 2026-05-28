
from fastapi import APIRouter


router = APIRouter

@router.post("/upload")
async def document_upload() :
  pass