from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.schemas.response import UnifiedResponse
from app.services.chat import generate_reply, stream_chat as stream_chat_service

router = APIRouter()

_STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


@router.post("/")
async def chat(request: ChatRequest) -> dict:
    reply = await generate_reply(request.message)
    return UnifiedResponse.success(data={"message": reply})


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_chat_service(request.message),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
    )
