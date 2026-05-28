from app.config.settings import get_settings
from collections.abc import AsyncIterator
from openai import AsyncOpenAI,APIError
# 获取模型API相关的信息
def _client() -> AsyncOpenAI:
  c = get_settings()
  return AsyncOpenAI(
    api_key= c.SILICONFLOW_API_KEY,
    base_url= c.SILICONFLOW_BASE_URL
  )


def build_content(message: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": message}]


async def stream_llm(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    s = get_settings()
    client = _client()
    try:
        stream = await client.chat.completions.create(
            model=s.SILICONFLOW_MODEL,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except APIError:
        yield "【服务异常】请检查 API Key、模型名或网络"
        return
