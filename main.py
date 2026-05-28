from fastapi import FastAPI
from app.api.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="RAG Personal API")
"""
    演示案例
    from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
"""
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

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", reload=True)


