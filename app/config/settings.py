from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
    upload_dir="/data/uploads",
    max_load_mb=10,
    allwoed_suffixes=(".txt","docx")
  )
  """
    同名映射
  """
  # API配置
  SILICONFLOW_API_KEY :str
  SILICONFLOW_BASE_URL : str = "https://api.siliconflow.cn/v1"
  SILICONFLOW_MODEL : str = "Qwen/Qwen2.5-7B-Instruct"

  #文件上传配置
  UPLOAD_DIR : str = "./data/storage/chroma_db"
  UPLOAD_MIR : str = "./data/sotrage"
  MAX_FILE_SIZE : int = 10
  ALLOWED_SUFFIXES : tuple[str] = (".txt",".docx", ".pdf", ".md")

#   文本切割配置
  CHUNK_SIZE : int = 500
  CHUNK_OVERLAP : int = 50


"""
  @lru_cache
  定义共用同一份settings作为缓存
"""
@lru_cache
def get_settings() -> settings:
  return settings()