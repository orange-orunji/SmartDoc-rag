from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.api.document import router as document_router
from fastapi.middleware.cors import CORSMiddleware

from app.services import vector_store
from app.services.vector_store import VectorStoreService
from app.services.bm25_service import BM25Service
app = FastAPI(title="RAG Personal API")
# 添加拦截器
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由(将聊天接口加到主路由上)
app.include_router(chat_router,prefix="/api/chat",tags=["对话接口"])
app.include_router(document_router,prefix="/api/document",tags=["上传文件接口"])

@app.on_event("startup")
async def build_bm25_index():
    try:
        all_docs = VectorStoreService().get_all_documents()
    except AttributeError:
        # 手动获取chroma中的文件,执行逻辑和类本身的构建相同
        all_docs = vector_store.chroma.get()  # 返回字典，包含 'documents' 和 'metadatas'
        # 需要转换成 Document 列表
        from langchain_core.documents import Document
        all_docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(all_docs['documents'], all_docs['metadatas'])
        ]
    BM25Service().build_index(all_docs)
    print(f"BM25 索引构建完成，文档数：{len(all_docs)}")
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", reload=True)


