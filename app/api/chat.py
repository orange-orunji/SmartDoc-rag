import hashlib

from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends

import os

from app.schemas.chat import ChatRequest
from app.services.history_service import get_file_chat_history
from app.services.llm import get_rag_chain
from app.utils.auth import get_current_user
from app.utils.redis_client import redis_client_connect as redis
from app.utils.semantic_cache import semantic_cache
from app.config.settings import get_settings

router = APIRouter()
s = get_settings()


def _sse_escape(text: str) -> str:
    """将换行符转义，防止破坏 SSE 协议格式"""
    return text.replace('\n', '\\n')
"""
流式输出接口
"""
@router.post("/stream")
async def stream_chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["user_id"])

    if redis:
        # 1. 语义相似度缓存
        cached_answer = semantic_cache.lookup(request.question, user_id)
        if cached_answer:
            async def cache_stream():
                yield f"data: {_sse_escape(cached_answer)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(cache_stream(), 200, media_type="text/event-stream")

        # 2. MD5 精确匹配缓存（兜底）
        question_hash = hashlib.md5(request.question.encode()).hexdigest()
        user_key = f"{s.REDIS_USER_PREFIX}:{user_id}:{question_hash}"
        redis_chat_history = redis.get(user_key)
        if redis_chat_history:
            async def cache_stream():
                yield f"data: {_sse_escape(redis_chat_history)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(cache_stream(), 200, media_type="text/event-stream")

    async def event_stream():
        all_request = ""
        try:
            chain = get_rag_chain(user_id)
            async for chunk in chain.astream(
                {"input": request.question},
                config={"configurable": {"session_id": request.session_id, "user_id": user_id}}
            ):
                all_request += chunk
                yield f"data: {_sse_escape(chunk)}\n\n"
        except Exception as e:
            yield f"data: 【系统错误】{_sse_escape(str(e))}\n\n"
        finally:
            if all_request and redis:
                question_hash = hashlib.md5(request.question.encode()).hexdigest()
                user_key = f"{s.REDIS_USER_PREFIX}:{user_id}:{question_hash}"
                redis.setex(name=user_key, value=all_request, time=s.REDIS_EXPIRE)
                semantic_cache.store(request.question, user_id, all_request)
            yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.get("/history/{session_id}")
async def get_history(session_id: str, current_user: dict = Depends(get_current_user)):
    history = get_file_chat_history(session_id,user_id=current_user["user_id"])
    # 将 BaseMessage 列表转为可序列化的字典列表
    messages = []
    for msg in history.messages:
        messages.append({
            "role": "human" if msg.type == "human" else "assistant",
            "content": msg.content
        })
    return {"messages": messages}

@router.get("/sessions")
async def get_user_sessions(current_user: dict = Depends(get_current_user)):
    """对话管理"""
    user_id = str(current_user["user_id"])
    storage_path = s.CHAT_HISTORY_STORAGY_PATH
    user_dir = os.path.join(storage_path, user_id)

    if not os.path.exists(user_dir):
        return {"sessions": []}

    # 列出该目录下所有 .json 文件，提取会话 ID（去掉 .json 后缀）
    sessions = [
        f.replace('.json', '')
        for f in os.listdir(user_dir)
        if f.endswith('.json')
    ]
    return {"sessions": sessions}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """删除指定会话"""
    user_id = str(current_user["user_id"])
    storage_path = s.CHAT_HISTORY_STORAGY_PATH
    file_path = os.path.join(storage_path, user_id, f"{session_id}.json")

    if not os.path.exists(file_path):
        return {"code": 404, "message": "会话不存在"}

    os.remove(file_path)
    return {"code": 200, "message": f"会话 {session_id} 已删除"}