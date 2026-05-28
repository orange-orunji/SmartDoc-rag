import json
from collections.abc import AsyncIterator

from app.services.llm import complete, stream_complete


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_done() -> str:
    return "data: [DONE]\n\n"


async def generate_reply(message: str) -> str:
    """生成完整回复（非流式）。"""
    return await complete(message)


async def stream_chat(message: str) -> AsyncIterator[str]:
    """流式输出，SSE 格式。"""
    try:
        async for chunk in stream_complete(message):
            yield _sse({"content": chunk})
    except Exception as exc:
        yield _sse({"error": str(exc)})
    yield _sse_done()
