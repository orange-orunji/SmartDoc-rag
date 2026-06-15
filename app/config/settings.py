from pathlib import Path
from typing import Tuple
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取项目根目录（settings.py 位于 app/config/ 下，往上三层才是根目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),   # 同时让 .env 路径也用绝对路径
        env_file_encoding="utf-8",
        extra="ignore"
    )
    # API 配置...
    SILICON_API_KEY: str
    SILICON_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICON_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"

    # chroma 配置
    CHROMA_DIR: str = str(BASE_DIR / "app/data/storage/chroma_db")
    CHROMA_NAME: str = "enterprise_knowledge"

    # md5 配置
    MD5_PATH: str = str(BASE_DIR / "app/data/storage/md5_records.txt")

    # 文件上传
    MAX_FILE_SIZE: int = 10
    ALLOWED_SUFFIXES: Tuple[str, ...] = (".txt", ".docx", ".pdf", ".md")
    UPLOAD_DIR: str = "/data/uploads"   # 若为本地临时目录，也可用 BASE_DIR / "data/uploads"

    # 文本切割
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    SEPARATORS: list[str] = ["\n\n", "\n", "\t", " ", ".", ",", "!", "?", ";", "。", "，"]

    # 向量检索数量
    VECTOR_MAX_NUM: int = 3

    # 聊天历史存储路径 —— 使用绝对路径，固定在 app/data/chat_history
    CHAT_HISTORY_STORAGY_PATH: str = str(BASE_DIR / "app/data/chat_history")

    # redis 配置
    REDIS_HOST = "localhost"
    REDIS_POST = 6379
    REDIS_DB = 1

@lru_cache
def get_settings() -> settings:
    return settings()