from fastapi import Depends

from app.services.llm import get_rag_chain
from app.utils.auth import get_current_user


async def stream_chat(message: str,current_user: dict = Depends(get_current_user)):
  """
  流式输出接口
  """
  chain = get_rag_chain(current_user["user_id"])
  async for token in chain.astream(message):
        yield token.encode("utf-8")
  yield " \ndata:[DONE]\n".encode("utf-8")
