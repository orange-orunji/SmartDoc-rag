from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.api.document import router as document_router
from fastapi.middleware.cors import CORSMiddleware
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

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", reload=True)


