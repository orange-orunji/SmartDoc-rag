from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.api.chat import router as chat_router
from app.api.document import router as document_router
from app.api.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

from app.services import vector_store
from app.services.vector_store import VectorStoreService
from app.services.bm25_service import BM25Service
from app.utils.SQL_database import engine, Base

app = FastAPI(title="RAG Personal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/chat", tags=["对话接口"])
app.include_router(document_router, prefix="/api/document", tags=["上传文件接口"])
app.include_router(auth_router, prefix="/api/auth", tags=["用户登录注册相关接口"])


@app.get("/")
async def redirect_to_frontend():
    """根路径重定向到前端页面"""
    return RedirectResponse(url="/static/index.html")


# 静态文件服务（HTML 前端）
app.mount("/static", StaticFiles(directory="app/static", html=True), name="static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": f"服务器内部错误: {str(exc)}", "data": None}
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "RAG Personal API"}


@app.on_event("startup")
async def build_bm25_index():
    try:
        all_docs = VectorStoreService().get_all_documents()
    except AttributeError:
        from langchain_core.documents import Document
        all_docs = vector_store.chroma.get()
        all_docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(all_docs["documents"], all_docs["metadatas"])
        ]
    BM25Service().build_index(all_docs)
    print(f"BM25 索引构建完成，文档数：{len(all_docs)}")


@app.on_event("startup")
async def build_table_if_absent():
    Base.metadata.create_all(bind=engine)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", reload=True)
