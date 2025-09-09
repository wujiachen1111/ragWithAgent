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

class DataFetcherConfig(BaseModel):
    """数据获取器配置"""
    timeout: float = 30.0
    max_retries: int = 3
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

class SystemConfig(BaseSettings):
    """系统总配置"""
    model_config = SettingsConfigDict(
        env_file=os.path.join(ROOT_DIR, ".env"),
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        env_prefix='STOCK_'  # 添加前缀以避免与其他服务的环境变量冲突
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
    fetcher: DataFetcherConfig = Field(default_factory=DataFetcherConfig)

# 全局配置实例
settings = SystemConfig()

def get_config() -> SystemConfig:
    """获取全局配置"""
    return settings
