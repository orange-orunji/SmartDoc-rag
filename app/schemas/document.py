from pydantic import BaseModel, Field

class upload_document(BaseModel):
  filename: str = Field(description="原始文件名")
  saved_path: str = Field(description="磁盘保存路径")
  chunk_count: int = Field(description="将该文件分成几份")
  chars: int | None = Field(default=None,description="解析后的总字符数")
# 失败时用 FastAPI 的 HTTPException（400/413），不必单独 schema。

