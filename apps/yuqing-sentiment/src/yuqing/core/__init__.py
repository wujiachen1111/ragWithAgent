"""
核心模块聚合（提供轻量级导入，避免在测试/本地环境触发重依赖）。
"""

from .config import settings
from .database import get_db, init_db, check_db_connection
from .cache import redis_client, get_cache_key, check_redis_connection
from .logging import app_logger


def get_chroma_client():
    # 懒加载，避免导入时初始化重依赖
    from . import vector_store as _vs

    return _vs.get_chroma_client()


def check_chroma_connection() -> bool:
    from . import vector_store as _vs

    return _vs.check_chroma_connection()


__all__ = [
    "settings",
    "get_db",
    "init_db",
    "check_db_connection",
    "redis_client",
    "get_cache_key",
    "check_redis_connection",
    "get_chroma_client",
    "check_chroma_connection",
    "app_logger",
]
