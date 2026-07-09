import logging
import redis
from app.config.settings import settings as st

logger = logging.getLogger("rag.redis")

_redis_client = None

def get_redis():
    """懒加载 Redis 连接，连接失败返回 None 而不是崩溃"""
    global _redis_client
    if _redis_client is None:
        try:
            s = st()
            kwargs = {
                "host": s.REDIS_HOST,
                "port": s.REDIS_PORT,
                "db": s.REDIS_DB,
                "decode_responses": True,
            }
            if s.REDIS_PASSWORD:
                kwargs["password"] = s.REDIS_PASSWORD
            _redis_client = redis.Redis(**kwargs)
            _redis_client.ping()
            logger.info("Redis 连接成功: host=%s, port=%s, db=%s", s.REDIS_HOST, s.REDIS_PORT, s.REDIS_DB)
        except redis.ConnectionError:
            logger.warning("Redis 未连接，缓存功能将不可用")
            _redis_client = None
    return _redis_client

redis_client_connect = get_redis()
