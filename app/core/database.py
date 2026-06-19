"""SQLAlchemy 数据库连接与依赖"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 创建 SQLAlchemy 引擎，支持 SQLite 和 SQL Server
_connect_args = getattr(settings, 'DATABASE_CONNECT_ARGS', None)

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=_connect_args if _connect_args else {},
    pool_pre_ping=True if not settings.DATABASE_URL.startswith('sqlite') else False,
    pool_recycle=3600 if not settings.DATABASE_URL.startswith('sqlite') else -1,
)

# SessionLocal 用于创建数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类，所有 ORM 模型继承此类
Base = declarative_base()


def get_db():
    """FastAPI 依赖：获取数据库会话，请求结束后自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
