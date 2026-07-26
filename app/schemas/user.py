from sqlalchemy import String,Column,Integer
from pydantic import BaseModel
from app.utils.SQL_database import Base

# ── ORM 模型 ──

class User(Base):
    __tablename__ = "users"

    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True,index=True)
    hashed_password = Column(String)

# ── Pydantic 响应模型 ──

class AuthResponse(BaseModel):
    """登录/注册响应"""
    message: str = ""
    access_token: str | None = None
    token_type: str | None = None