import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.utils.SQL_database import SessionLocal
from app.schemas.user import User
from app.utils.auth import generate_hash_password, verify_password, create_access_token
from pydantic import BaseModel

import contextvars

logger = logging.getLogger("rag.auth")
router = APIRouter()

current_user_ctx : contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_user",default="agent"
)

# 请求体格式：{"username": "xxx", "password": "xxx"}
class AutoRequest(BaseModel):
    username: str
    password: str

# 定义获取连接对象类,用database下的SessionLocal会话类来获取
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
def register(request : AutoRequest,db : Session = Depends(get_db)):
    # 密码长度校验（bcrypt 限制 72 字节）
    if len(request.password.encode('utf-8')) > 72:
        raise HTTPException(status_code=400, detail="密码过长，请使用不超过 72 字节的密码（约 24 个中文字符）")
    #去重
    first = db.query(User).filter(User.username == request.username).first()
    if first:
        raise  HTTPException(status_code=400,detail="用户已存在")
    # 注册相关用户信息
    user = User(username=request.username, hashed_password=generate_hash_password(request.password))
    db.add(user)
    db.commit()
    return {"message":"用户注册成功"}


@router.post("/login")
def login(request : AutoRequest,db : Session = Depends(get_db)):
    target_user = db.query(User).filter(User.username == request.username).first()
    if not target_user or not verify_password(request.password,target_user.hashed_password):
        raise  HTTPException(status_code=400,detail="用户或密码错误")
    token = create_access_token(data={"sub": target_user.username, "user_id": target_user.id})
    return {"access_token": token, "token_type": "bearer"}

