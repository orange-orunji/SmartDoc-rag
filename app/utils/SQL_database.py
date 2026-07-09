import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.settings import get_settings

cfg = get_settings()

# 获取当前文件所在目录的上级目录（即项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "app.db")

# 定义数据库连接地址，使用 SQLite
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 创建连接引擎（配置连接池）
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=cfg.DB_POOL_SIZE,
    max_overflow=cfg.DB_MAX_OVERFLOW,
    pool_timeout=cfg.DB_POOL_TIMEOUT,
    pool_recycle=cfg.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # 每次使用前检测连接是否有效
    echo=cfg.is_dev,      # 开发环境打印 SQL
)

# SQLite 需要启用 WAL 模式以支持并发读写
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# 创建会话类,供外部使用
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 创建数据库模型基类, Base 是所有模型类的父类，继承它才能建表
Base = declarative_base()