import hashlib
import json
import logging
import os
import time

from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, Request
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.agent import get_agent
from app.api.auth import current_user_ctx
from app.schemas.chat import ChatRequest, RenameRequest, HistoryResponse, SessionListResponse, SessionActionResponse
from app.services.history_service import get_file_chat_history
from app.utils.auth import get_current_user
from app.utils.redis_client import redis_client_connect as redis
from app.utils.semantic_cache import semantic_cache
from app.config.settings import get_settings
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger("rag.chat")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()
s = get_settings()


def _sse_encode(text: str) -> str:
    """SSE 帧内容编码：JSON 字符串（含引号、真实换行）无损传输。

    之前用 text.replace('\\n', '\\\\n') 转义，会把真实换行与代码中的
    字面 \\n 混为一谈——前端还原时代码里的 \\n 字符串会被错误变成换行。
    JSON 编码语义明确：真实换行编码为 \\n，字面 \\n 编码为 \\\\\\n，
    前端 JSON.parse 即可无损还原。
    """
    return json.dumps(text, ensure_ascii=False)
"""
流式输出接口
"""
@router.post("/stream")
@limiter.limit("10/minute")
async def stream_chat(request: Request, body: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["user_id"])
    t_start = time.time()
    if redis:
        # 1. 语义相似度缓存
        cached_answer = semantic_cache.lookup(body.question, user_id)
        if cached_answer:
            async def cache_stream():
                yield f"data: {_sse_encode(cached_answer)}\n\n"
                yield "data: [DONE]\n\n"
            logger.info("缓存命中 | type=semantic | user=%s | 耗时=%.2fs", user_id, time.time() - t_start)
            return StreamingResponse(cache_stream(), 200, media_type="text/event-stream")

        # 2. MD5 精确匹配缓存（兜底）
        question_hash = hashlib.md5(body.question.encode()).hexdigest()
        user_key = f"{s.REDIS_USER_PREFIX}:{user_id}:{question_hash}"
        redis_chat_history = redis.get(user_key)
        if redis_chat_history:
            async def cache_stream():
                yield f"data: {_sse_encode(redis_chat_history)}\n\n"
                yield "data: [DONE]\n\n"
            logger.info("缓存命中 | type=md5 | user=%s | 耗时=%.2fs", user_id, time.time() - t_start)
            return StreamingResponse(cache_stream(), 200, media_type="text/event-stream")

    async def event_stream():
        t_start = time.time()
        all_request = ""
        chat_history = get_file_chat_history(user_id=user_id, session_id=body.session_id)
        try:
            # chain = get_rag_chain(user_id)
            current_user_ctx.set(user_id)
            chain = get_agent()
            # 格式化历史消息为结构化文本
            history_text = ""
            if chat_history.messages:
                lines = ["## 对话历史"]
                for m in chat_history.messages[-10:]:
                    role = "用户" if m.type == "human" else "助手"
                    lines.append(f"- {role}: {m.content}")
                history_text = "\n".join(lines) + "\n\n## 当前问题\n"

            async for event in chain.astream_events(
                {"input": history_text + body.question},
                version="v1",
            ):
                e = event["event"]
                if e == "on_tool_start":
                    # 工具调用提示（Agent 推理轮输出的 tool_calls 在这里触发）
                    tool_name = event.get("name", "?")
                    tool_input = str(event["data"].get("input", ""))[:80]
                    hint = f"[调用工具: {tool_name} | 输入: {tool_input}]"
                    yield f"data: {_sse_encode(hint)}\n\n"
                elif e == "on_chat_model_stream":
                    # token 级文本流：中间轮 function calling 的 content 为空会被跳过，
                    # 只有最终回答的文本会流出 → 打字机效果
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        text = "".join(
                            part.get("text", "") for part in content
                            if isinstance(part, dict) and part.get("type") == "text"
                        )
                    else:
                        text = ""
                    if not text:
                        continue
                    all_request += text
                    yield f"data: {_sse_encode(text)}\n\n"
                elif e == "on_tool_end":
                    # 检测报告生成 → 推送下载链接（直接推 HTML，marked 会原样渲染）
                    output = event["data"].get("output")
                    if output and "[REPORT_FILE]" in str(output):
                        filename = str(output).split("[REPORT_FILE]")[1].split("\n")[0]
                        dl_html = f"<p><a href='/reports/{filename}' download class='download-link'>📥 下载报告：{filename}</a></p>"
                        all_request += dl_html  # 持久化到历史
                        yield f"data: {_sse_encode(dl_html)}\n\n"
        except Exception as e:
            logger.exception("流式对话异常 | user_id=%s", user_id)
            if s.is_production:
                yield f"data: {_sse_encode('【系统错误】服务暂时不可用，请稍后重试')}\n\n"
            else:
                yield f"data: {_sse_encode('【系统错误】' + str(e))}\n\n"
        finally:
            if all_request and redis:
                question_hash = hashlib.md5(body.question.encode()).hexdigest()
                user_key = f"{s.REDIS_USER_PREFIX}:{user_id}:{question_hash}"
                redis.setex(name=user_key, value=all_request, time=s.REDIS_EXPIRE)
                semantic_cache.store(body.question, user_id, all_request)
            history = chat_history
            history.add_message(HumanMessage(content=body.question))
            history.add_message(AIMessage(content=all_request))
            logger.info("对话完成 | user=%s | 耗时=%.2fs | 回复长度=%d", user_id, time.time() - t_start, len(all_request))
            yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.get("/history/{session_id}", response_model=HistoryResponse)
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

@router.get("/sessions", response_model=SessionListResponse)
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


@router.delete("/session/{session_id}", response_model=SessionActionResponse)
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """删除指定会话"""
    user_id = str(current_user["user_id"])
    storage_path = s.CHAT_HISTORY_STORAGY_PATH
    file_path = os.path.join(storage_path, user_id, f"{session_id}.json")

    if not os.path.exists(file_path):
        return {"code": 404, "message": "会话不存在"}

    os.remove(file_path)
    return {"code": 200, "message": f"会话 {session_id} 已删除"}


@router.put("/session/{session_id}/rename", response_model=SessionActionResponse)
async def rename_session(session_id: str, request: RenameRequest, current_user: dict = Depends(get_current_user)):
    """重命名指定会话"""
    user_id = str(current_user["user_id"])
    storage_path = s.CHAT_HISTORY_STORAGY_PATH
    user_dir = os.path.join(storage_path, user_id)
    old_path = os.path.join(user_dir, f"{session_id}.json")
    new_name = request.new_name.strip()

    new_path = os.path.join(user_dir, f"{new_name}.json")
    if os.path.exists(new_path):
        return {"code": 409, "message": "该名称已存在，请使用其他名称"}

    # 确保用户目录存在
    os.makedirs(user_dir, exist_ok=True)

    if os.path.exists(old_path):
        os.rename(old_path, new_path)
    else:
        # 新会话还没有文件，直接创建空文件
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    return {"code": 200, "message": "重命名成功", "data": {"new_name": new_name}}