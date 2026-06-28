import json
from enum import Enum

from app.utils.redis_client import get_redis


class TaskStatus(str, Enum):
    """状态枚举类"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskTracker:
    """任务状态追踪器，用于在redis中设置和获取状态"""
    PREFIX = "task:document:"
    EXPIRE = 3600  # 1 小时过期

    @staticmethod
    def _key(task_id: str) -> str:
        return f"{TaskTracker.PREFIX}{task_id}"

    @staticmethod
    def set_status(task_id: str, status: TaskStatus, extra: dict | None = None):
        redis = get_redis()
        if not redis:
            return
        data = {"status": status.value, **(extra or {})}
        redis.setex(TaskTracker._key(task_id), TaskTracker.EXPIRE, json.dumps(data, ensure_ascii=False))

    @staticmethod
    def get_status(task_id: str) -> dict | None:
        redis = get_redis()
        if not redis:
            return None
        raw = redis.get(TaskTracker._key(task_id))
        return json.loads(raw) if raw else None
