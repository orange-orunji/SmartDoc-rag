from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest
from app.services.history_service import get_file_chat_history
from app.services.llm import get_rag_chain
from app.utils.auth import get_current_user

router = APIRouter()

"""
流式输出接口
"""
@router.post("/stream")
async def stream_chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    async def event_stream():
        try:
            chain = get_rag_chain(user_id)
            async for chunk in chain.astream(
                {"input": request.question},
                config={"configurable": {"session_id": request.session_id, "user_id": user_id}}
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            # 发送错误消息给前端，避免连接突然中断
            yield f"data: 【系统错误】{str(e)}\n\n"
        finally:
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