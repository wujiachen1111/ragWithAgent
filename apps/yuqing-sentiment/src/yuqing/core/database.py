from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from yuqing.core.config import settings
from yuqing.core.logging import app_logger
from pathlib import Path

# 导入所有模型以确保表创建
from yuqing.models.database_models import Base

# 延迟初始化的引擎与会话工厂，支持失败时回退到SQLite
engine = None
SessionLocal = None
metadata = MetaData()


def _create_engine(db_url: str):
    return create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.debug,
        future=True,
    )


def _fallback_sqlite_url() -> str:
    # 将SQLite文件放到仓库根的 data 目录下
    try:
        repo_root = Path(__file__).resolve().parents[5]
    except Exception:
        repo_root = Path.cwd()
    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'yuqing_local.db').as_posix()}"


def _ensure_engine() -> None:
    global engine, SessionLocal
    if engine is not None and SessionLocal is not None:
        return
    # 首选配置的数据库
    primary_url = getattr(settings, "database_url", None) or _fallback_sqlite_url()
    try:
        engine = _create_engine(primary_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
        # 试连一次
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        app_logger.info(f"数据库引擎初始化完成: {primary_url}")
    except Exception as e:
        app_logger.error(f"初始化主数据库失败({primary_url}): {e}")
        # 严格模式不回退
        if getattr(settings, "require_external_services", False):
            raise
        # 回退到SQLite
        fallback = _fallback_sqlite_url()
        app_logger.warning(f"回退到SQLite: {fallback}")
        engine = _create_engine(fallback)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db():
    """数据库会话依赖注入（自动初始化并在必要时回退SQLite）"""
    _ensure_engine()
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
    """初始化数据库（自动创建表；如有必要则回退SQLite）"""
    _ensure_engine()
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_minimal_schema_compat()
        app_logger.info("数据库表创建成功")
    except Exception as e:
        app_logger.error(f"数据库初始化失败: {e}")
        raise


def check_db_connection():
    """检查数据库连接；若失败则尝试回退到SQLite。"""
    global engine, SessionLocal
    _ensure_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        app_logger.info("数据库连接正常")
        return True
    except Exception as e:
        app_logger.error(f"数据库连接失败: {e}")
        # 尝试回退
        try:
            if getattr(settings, "require_external_services", False):
                return False
            fallback = _fallback_sqlite_url()
            app_logger.warning(f"尝试回退到SQLite: {fallback}")
            # 重新初始化
            engine_fallback = _create_engine(fallback)
            with engine_fallback.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine = engine_fallback
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
            app_logger.info("回退SQLite连接正常")
            return True
        except Exception as e2:
            app_logger.error(f"回退SQLite仍失败: {e2}")
            return False


def _ensure_minimal_schema_compat() -> None:
    """最小化的表结构兼容处理（主要用于本地/旧SQLite库）。

    说明：Base.metadata.create_all 不会为已存在的表添加新列，
    这里在检测到缺少关键列时，做一次性补充，避免插入时失败。
    生产环境建议使用 Alembic 维护 schema。
    """
    try:
        dialect = engine.dialect.name  # type: ignore
        with engine.begin() as conn:  # type: ignore
            required_cols = {
                "news_items": {
                    # 仅添加可能缺失且写入路径用到的列
                    "source_url": "TEXT",
                    "summary": "TEXT",
                    "language": "VARCHAR(50)",
                    "region": "VARCHAR(50)",
                    "raw_data": "TEXT",
                    "analysis_status": "VARCHAR(50)",
                    "collected_at": "DATETIME",
                },
            }

            if dialect == "sqlite":
                for table, cols in required_cols.items():
                    try:
                        rows = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
                        existing = {r[1] for r in rows}  # name is at index 1
                        for col, coltype in cols.items():
                            if col not in existing:
                                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"))
                                app_logger.info(f"已为 {table} 补充列: {col} {coltype}")
                    except Exception as e:
                        app_logger.warning(f"检查/补充表结构失败 {table}: {e}")
            else:
                # 非SQLite：仅记录提示，推荐用Alembic迁移
                app_logger.info("非SQLite数据库，跳过最小化结构补充；请使用Alembic迁移维护schema。")
    except Exception as e:
        app_logger.warning(f"最小化表结构兼容处理失败: {e}")
