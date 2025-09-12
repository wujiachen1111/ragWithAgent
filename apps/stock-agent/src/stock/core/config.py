"""
Stock Agent 服务配置
"""
from __future__ import annotations
import os
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent

class ApiConfig(BaseModel):
    """API 配置"""
    host: str = "0.0.0.0"
    port: int = 8020
    debug: bool = False

class DatabaseConfig(BaseModel):
    """数据库配置"""
    uri: str = "mongodb://localhost:27017/"
    database: str = "stock_data"
    timeout: int = 5000
    
    def get_connection_uri(self) -> str:
        """获取连接URI"""
        if self.database not in self.uri:
            # 如果URI中没有指定数据库，则添加
            if self.uri.endswith('/'):
                return f"{self.uri}{self.database}"
            else:
                return f"{self.uri}/{self.database}"
        return self.uri
    
    def get_connection_info(self) -> dict:
        """获取连接信息（隐藏敏感信息）"""
        return {
            "host": "localhost",
            "port": 27017,
            "database": self.database,
            "auth_mode": "无认证"
        }

class DataFetcherConfig(BaseModel):
    """数据获取器配置"""
    request_timeout: float = 30.0
    request_delay: float = 0.5  # 增加默认延迟以避免IP被封
    retry_count: int = 3
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

class SystemConfig(BaseSettings):
    """系统总配置"""
    model_config = SettingsConfigDict(
        env_file=os.path.join(ROOT_DIR, ".env"),
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        env_prefix='STOCK_',  # 启用前缀以兼容环境变量名 STOCK_API__PORT 等
    )

    # 基础配置
    app_name: str = "Stock Agent"
    description: str = "提供股票数据和RAG集成的服务"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    # 组件配置
    api: ApiConfig = Field(default_factory=ApiConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    data: DataFetcherConfig = Field(default_factory=DataFetcherConfig)

# 全局配置实例
settings = SystemConfig()

def get_config() -> SystemConfig:
    """获取全局配置"""
    return settings
