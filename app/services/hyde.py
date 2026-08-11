import time
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.services.bm25_service import bm25_service
from app.services.rerank import rerank
from app.config.settings import get_settings
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("rag.retrieval")

s = get_settings()
_vs = VectorStoreService(embedding_model=None)
service = bm25_service

llm = ChatOpenAI(
    model=s.SILICON_MODEL,
    api_key=s.SILICON_API_KEY,
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
def hyde_retrieve(question : str,k : int = 3):
    return _vs.get_vector(query=generate_hypothetical(question),k=k)

# rerank后hyde检索
def hyde_plus_rerank_retrieve(question : str, k : int = 3):
    vector = _vs.get_vector(query=generate_hypothetical(question), k=k)
    return rerank(query=question,docs=vector,top_k=k)

    #hy​de检索后进行BM25计算后返回rank
def hyde_plus_rerank_bm25_retrieve(question : str, k_vector: int = 15, k_keyword: int = 10, final_k: int = 3):
    t_start = time.time()
    # 1.HyDE 假想向量检索
    t0 = time.time()
    hypo_text = generate_hypothetical(question)
    vector = _vs.get_vector(query=hypo_text, k=k_vector)
    logger.info("HyDE 生成+向量检索 | 耗时=%.2fs | 召回=%d | query=%s", time.time() - t0, len(vector), question[:50])

    # 2.BM25 关键词检索
    t0 = time.time()
    search = service.search(question, top_k=k_keyword)
    logger.info("BM25 关键词检索 | 耗时=%.2fs | 召回=%d", time.time() - t0, len(search))

    # 3. 合并去重
    t0 = time.time()
    contains = {}
    for doc in vector + search:
        if doc.page_content not in contains:
            contains[doc.page_content] = doc
    unique_docs = list(contains.values())
    logger.info("合并去重 | 耗时=%.2fs | 合并前=%d | 去重后=%d",
                time.time() - t0, len(vector) + len(search), len(unique_docs))

    # 4. Rerank 重排序
    t0 = time.time()
    result = rerank(question, unique_docs, top_k=final_k)
    logger.info("Rerank 重排序 | 耗时=%.2fs | 最终=%d | 总耗时=%.2fs",
                time.time() - t0, len(result), time.time() - t_start)

    return result
if __name__ == "__main__":
    q = "java相关资料？"
    docs = hyde_plus_rerank_retrieve(q)
    print("检索到的文档片段：")
    for doc in docs:
        print(doc.page_content[:200])