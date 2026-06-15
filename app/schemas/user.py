from sqlalchemy import String,Column,Integer
from app.utils.SQL_database import Base

class User(Base):
    __tablename__ = "users" # 定义表名

    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True,index=True)
    hashed_password = Column(String) #存储加密后的暗文密码所以用字符串来接受,对比的是哈希值