"""
数据库连接管理
"""

import pymongo
from typing import Optional
from loguru import logger

from .config import settings


class DatabaseManager:
    """MongoDB数据库管理器"""
    
    def __init__(self):
        self._client: Optional[pymongo.MongoClient] = None
        self._db = None
        
    def connect(self) -> bool:
        """连接数据库"""
        try:
            # 获取连接URI
            connection_uri = settings.database.get_connection_uri()
            
            # 创建客户端连接
            self._client = pymongo.MongoClient(connection_uri)
            
            # 测试连接
            self._client.admin.command('ping')
            self._db = self._client[settings.database.database]
            
            # 记录连接信息（隐藏敏感信息）
            conn_info = settings.database.get_connection_info()
            logger.info(f"✅ 成功连接到MongoDB")
            logger.info(f"   主机: {conn_info['host']}:{conn_info['port']}")
            logger.info(f"   数据库: {conn_info['database']}")
            logger.info(f"   认证: {conn_info['auth_mode']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ MongoDB连接失败: {e}")
            logger.error(f"   请检查MongoDB服务是否运行，以及连接配置是否正确")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB连接已关闭")
    
    @property
    def client(self) -> Optional[pymongo.MongoClient]:
        """获取数据库客户端"""
        return self._client
    
    @property
    def db(self):
        """获取数据库实例"""
        return self._db
    
    @property
    def stocks_collection(self):
        """获取股票数据集合"""
        if self._db is None:
            raise RuntimeError("数据库未连接")
        return self._db.stocks
    
    @property
    def tasks_collection(self):
        """获取任务集合"""
        if self._db is None:
            raise RuntimeError("数据库未连接")
        return self._db.tasks
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# 全局数据库管理器实例
db_manager = DatabaseManager()
