from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from yuqing.core.config import settings
from yuqing.core.logging import app_logger

# 导入所有模型以确保表创建
from yuqing.models.database_models import Base

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
    future=True
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)

# 创建基础模型类（使用导入的Base）
metadata = MetaData()


def get_db():
    """数据库会话依赖注入"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        app_logger.error(f"数据库会话错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """初始化数据库"""
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        app_logger.info("数据库表创建成功")
    except Exception as e:
        app_logger.error(f"数据库初始化失败: {e}")
        raise


def check_db_connection():
    """检查数据库连接"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        app_logger.info("数据库连接正常")
        return True
    except Exception as e:
        app_logger.error(f"数据库连接失败: {e}")
        return False
