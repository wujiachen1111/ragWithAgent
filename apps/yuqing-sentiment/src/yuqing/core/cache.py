import redis
from typing import Optional, Any, Dict, Tuple
import json
import pickle
import asyncio
import time
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


class MemoryCache:
    """简易内存缓存，用于无Redis环境的本地/测试降级。

    注意：该实现仅用于本地开发与单进程测试，不适合生产。
    """

    def __init__(self):
        # key -> (value_bytes, expire_ts or None)
        self._store: Dict[str, Tuple[bytes, Optional[float]]] = {}

    async def get(self, key: str) -> Optional[Any]:
        now = time.time()
        item = self._store.get(key)
        if not item:
            return None
        value_bytes, expire_ts = item
        if expire_ts is not None and expire_ts < now:
            # expired
            self._store.pop(key, None)
            return None
        try:
            return pickle.loads(value_bytes)
        except Exception:
            return None

    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        try:
            value_bytes = pickle.dumps(value)
            expire_ts = time.time() + expire if expire else None
            self._store[key] = (value_bytes, expire_ts)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    async def exists(self, key: str) -> bool:
        now = time.time()
        item = self._store.get(key)
        if not item:
            return False
        _, expire_ts = item
        if expire_ts is not None and expire_ts < now:
            self._store.pop(key, None)
            return False
        return True

    async def expire(self, key: str, ttl: int) -> bool:
        if key not in self._store:
            return False
        value_bytes, _ = self._store[key]
        self._store[key] = (value_bytes, time.time() + ttl)
        return True

    def ping(self) -> bool:
        return True


# 全局缓存客户端实例（优先Redis；若未要求严格且不可用则回退内存）
try:
    _tmp_client = RedisClient()
    if _tmp_client.ping():
        redis_client = _tmp_client
    else:
        if getattr(settings, "require_external_services", False) or getattr(settings, "require_redis", False):
            app_logger.error("Redis不可用，且严格模式开启，禁止回退")
            raise RuntimeError("Redis required but unavailable")
        app_logger.warning("Redis不可用，回退到内存缓存（仅本地/测试用途）")
        redis_client = MemoryCache()
except Exception:
    if getattr(settings, "require_external_services", False) or getattr(settings, "require_redis", False):
        raise
    app_logger.warning("初始化Redis失败，回退到内存缓存（仅本地/测试用途）")
    redis_client = MemoryCache()

# 为向后兼容提供别名
cache_manager = redis_client


def get_cache_key(prefix: str, *args) -> str:
    """生成缓存键"""
    return f"{prefix}:" + ":".join(str(arg) for arg in args)


def check_redis_connection() -> bool:
    """检查Redis连接；严格模式下返回真实状态，非严格模式失败则回退内存并视为可用。"""
    global redis_client, cache_manager
    try:
        if redis_client and redis_client.ping():
            return True
    except Exception:
        pass

    if getattr(settings, "require_external_services", False) or getattr(settings, "require_redis", False):
        return False

    # 非严格模式回退
    app_logger.warning("Redis连接检查失败，使用内存缓存降级模式")
    redis_client = MemoryCache()
    cache_manager = redis_client
    return True
