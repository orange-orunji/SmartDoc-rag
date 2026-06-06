from functools import lru_cache
from typing import Tuple

from pydantic_settings import BaseSettings, SettingsConfigDict

class settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore"
  )
  """
    同名映射
  """
  # API配置
  SILICON_API_KEY :str
  SILICON_BASE_URL : str = "https://api.siliconflow.cn/v1"
  SILICON_MODEL : str = "Qwen/Qwen2.5-7B-Instruct"

  # chroma配置
  CHROMA_DIR : str = "./data/storage/chroma_db"
  CHROMA_NAME : str = "enterprise_knowledge"

  # md5配置
  MD5_PATH : str = "./data/storage/md5_records.txt"

  #文件上传配置
  MAX_FILE_SIZE : int = 10
  ALLOWED_SUFFIXES : Tuple[str,...] = (".txt",".docx", ".pdf", ".md")
  UPLOAD_DIR : str = "/data/uploads"

#   文本切割配置
  CHUNK_SIZE : int = 500
  CHUNK_OVERLAP : int = 50
  SEPARATORS : list[str] = ["\n\n", "\n", "\t", " ",".",",","!","?",";","。","，"]


"""
  @lru_cache
  定义共用同一份settings作为缓存
"""
@lru_cache
def get_settings() -> settings:
  return settings()