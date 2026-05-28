from app.schemas.document import upload_document
from app.schemas.response import UnifiedResponse,error
async def document_upload(document:upload_document) -> UnifiedResponse|error:
  name_list = document.filename.split(".")
  end_name = name_list[len(name_list)-1]
  