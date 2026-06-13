from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.services.rerank import rerank
from app.config.settings import get_settings
from app.services.vector_store import VectorStoreService

s = get_settings()
_vs = VectorStoreService(embedding_model=None)

llm = ChatOpenAI(
    model=s.SILICON_MODEL,
    base_url=s.SILICON_BASE_URL,
    streaming=True,
    callbacks=[]
)

def generate_hypothetical(question : str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个文档写作助手。请根据用户的问题，写一段可能出现在相关文档中的答案/假想文本"),
        ("human", "{question}")
    ])
    messages = prompt.format_messages(question=question)
    content = llm.invoke(messages)
    return content.content
# 原版hyde检索
# def hyde_retrieve(question : str,k : int = 3):
#     return _vs.get_vector(query=generate_hypothetical(question),k=k)

# rerank后hyde检索
def hyde_retrieve(question : str,k : int = 3):
    vector = _vs.get_vector(query=generate_hypothetical(question), k=k)
    return rerank(query=generate_hypothetical(question),docs=vector,top_k=k)
if __name__ == "__main__":
    q = "java相关资料？"
    docs = hyde_retrieve(q)
    print("检索到的文档片段：")
    for doc in docs:
        print(doc.page_content[:200])