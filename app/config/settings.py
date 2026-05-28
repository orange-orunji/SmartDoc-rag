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
  SILICONFLOW_API_KEY :str
  SILICONFLOW_BASE_URL : str = "https://api.siliconflow.cn/v1"
  SILICONFLOW_MODEL : str = "Qwen/Qwen2.5-7B-Instruct"

"""
  @lru_cache
  定义共用同一份settings作为缓存
"""
@lru_cache
def get_settings() -> settings:
  return settings()