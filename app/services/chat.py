from typing import AsyncIterator
from app.services.llm import build_content,stream_llm

async def stream_chat(message : str) -> AsyncIterator[bytes]:
  """
  流式输出接口
  """
  content_list = build_content(message)
  async for token in stream_llm(content_list):
    yield f"{token}".encode("utf-8")
  yield " \ndata:[DONE]\n".encode("utf-8")
