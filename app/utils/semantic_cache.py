import os
import hashlib
import numpy as np
from langchain_community.embeddings import DashScopeEmbeddings
from app.config.settings import get_settings
from app.utils.redis_client import get_redis


class SemanticCache:
    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold
        self._embedding = DashScopeEmbeddings(
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )
        self._question_vecs: list[np.ndarray] = []
        self._redis_keys: list[str] = []
        self._settings = get_settings()

    def _encode(self, text: str) -> np.ndarray:
        vec = self._embedding.embed_query(text)
        arr = np.array(vec, dtype=np.float32)
        arr = arr / np.linalg.norm(arr)
        return arr

    #  查缓存
    def lookup(self, question: str, user_id: str) -> str | None:
        if not self._question_vecs:
            return None

        redis_client = get_redis()
        if not redis_client:
            return None

        query_vec = self._encode(question)
        matrix = np.vstack(self._question_vecs)
        scores = np.dot(matrix, query_vec)
        best_idx = int(np.argmax(scores))

        if scores[best_idx] >= self.threshold:
            key = self._redis_keys[best_idx]
            cached = redis_client.get(key)
            if cached:
                return cached
        return None

    # 存缓存
    def store(self, question: str, user_id: str, answer: str):
        redis_client = get_redis()
        if not redis_client:
            return

        qhash = hashlib.md5(question.encode()).hexdigest()[:12]
        key = f"{self._settings.REDIS_USER_PREFIX}:semantic:{user_id}:{qhash}"

        self._question_vecs.append(self._encode(question))
        self._redis_keys.append(key)

        redis_client.setex(name=key, value=answer, time=self._settings.REDIS_EXPIRE)


semantic_cache = SemanticCache()
