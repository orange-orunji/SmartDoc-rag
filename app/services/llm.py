from operator import itemgetter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory, RunnableLambda, RunnableParallel
from langchain_openai import ChatOpenAI

from app.config.settings import get_settings
from openai import AsyncOpenAI,APIError

from collections.abc import AsyncIterator
from app.services.hyde import hyde_plus_rerank_retrieve
from app.services.history_service import get_file_chat_history


# 获取模型API相关的信息
def _client() -> AsyncOpenAI:
  c = get_settings()
  return AsyncOpenAI(
    api_key= c.SILICON_API_KEY,
    base_url= c.SILICON_BASE_URL
  )
#
# 文本生成器
# def build_content(message: str) -> list[dict[str, str]]:
#     return [{"role": "user", "content": message}]


async def stream_llm(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    s = get_settings()
    client = _client()
    try:
        stream = await client.chat.completions.create(
            model=s.SILICON_MODEL,
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


def get_rag_chain(user_id: str):
    s = get_settings()
    llm = ChatOpenAI(
        model=s.SILICON_MODEL,
        api_key=s.SILICON_API_KEY,
        base_url=s.SILICON_BASE_URL,
        streaming=True,
        callbacks=[]
    )
    retrieve = RunnableLambda(lambda q  : hyde_plus_rerank_retrieve(question=q, k=25))

    prompt = ChatPromptTemplate.from_messages(
            messages=[
                ("system", "以提供的已知参考资料为主,"
                 "简洁和专业的回答用户问题，参考资料:{content}"),
                ("system","并且更根据历史信息来回答"),
                MessagesPlaceholder("history"),
                ("human","问题:{input}")
            ]
        )



    # 获取基础链对象
    chain = (
        RunnableParallel(
            {"input": itemgetter("input"),
             "content": itemgetter("input") | retrieve | RunnableLambda(__format_content),
             "history": itemgetter("history")}
        )  | prompt | llm | StrOutputParser()
    )

    # 创建一个绑定 user_id 的历史记录工厂函数
    def _session_history(session_id: str):
        return get_file_chat_history(session_id, user_id)

    # 获取增强链对象
    increase_chain = RunnableWithMessageHistory(
        chain,
        _session_history,
        input_messages_key="input",
        history_messages_key="history"
    )

    return increase_chain


def __format_content(documents):
    if not documents:
        return "无相关参考资料"
    else:
        document_str=""
        for doc in documents:
            document_str += f"文档片段：{doc.page_content}\n"
        return document_str

if __name__ == '__main__':
    configration = {
        "configurable": {
            "session_id": "user_0001"
        }
    }
    chain = get_rag_chain()
    stream = chain.stream({"input":"python和蟒蛇有什么关系"}, config=configration)
    for chunk in stream:
        print(chunk,end="",flush=True)
    # print(chain.invoke({"input": "什么是高考"}, config=configration))
