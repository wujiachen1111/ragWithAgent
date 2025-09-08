import redis
from typing import Optional, Any
import json
import pickle
import asyncio
from yuqing.core.config import settings
from yuqing.core.logging import app_logger


class RedisClient:
    """Redis客户端封装"""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=False,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            # 在线程池中运行同步redis操作
            loop = asyncio.get_event_loop()
            value = await loop.run_in_executor(None, self.redis_client.get, key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            app_logger.error(f"Redis GET 错误: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """设置缓存值"""
        try:
            serialized_value = pickle.dumps(value)
            loop = asyncio.get_event_loop()
            if expire:
                result = await loop.run_in_executor(
                    None, self.redis_client.setex, key, expire, serialized_value
                )
            else:
                result = await loop.run_in_executor(
                    None, self.redis_client.set, key, serialized_value
                )
            return bool(result)
        except Exception as e:
            app_logger.error(f"Redis SET 错误: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.redis_client.delete, key)
            return bool(result)
        except Exception as e:
            app_logger.error(f"Redis DELETE 错误: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.redis_client.exists, key)
            return bool(result)
        except Exception as e:
            app_logger.error(f"Redis EXISTS 错误: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        try:
            return bool(self.redis_client.expire(key, ttl))
        except Exception as e:
            app_logger.error(f"Redis EXPIRE 错误: {e}")
            return False
    
    def ping(self) -> bool:
        """检查连接状态"""
        try:
            return self.redis_client.ping()
        except Exception as e:
            app_logger.error(f"Redis PING 错误: {e}")
            return False


# 全局Redis客户端实例
redis_client = RedisClient()

# 为了向后兼容，提供cache_manager别名
cache_manager = redis_client


def get_cache_key(prefix: str, *args) -> str:
    """生成缓存键"""
    return f"{prefix}:" + ":".join(str(arg) for arg in args)


def check_redis_connection() -> bool:
    """检查Redis连接"""
    return redis_client.ping()
