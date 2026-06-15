import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base

# 获取当前文件所在目录的上级目录（即项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "app.db")

# 定义数据库连接地址，使用 SQLite
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 创建连接引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# 创建会话类,供外部使用
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建数据库模型基类, Base 是所有模型类的父类，继承它才能建表
Base = declarative_base()

# 创建redis连接
