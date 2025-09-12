import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    app_name: str = "新闻舆情股票分析系统"
    app_version: str = "1.0.0"
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "your_secret_key_here"
    
    # 数据库配置
    database_url: str = "postgresql://postgres:your_password@localhost:5432/news_analytics"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis配置
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600  # 1小时
    cache_ttl: int = 3600  # 兼容字段
    
    # Chroma向量数据库配置
    chroma_persist_directory: str = "./data/chromadb"
    chroma_collection_name: str = "news_embeddings"
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # DeepSeek API配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: int = 30
    deepseek_max_retries: int = 3
    
    # 多API密钥配置
    deepseek_api_keys: list = []
    
    # Twitter API配置
    twitter_bearer_token: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    
    # 数据采集配置
    news_fetch_interval: int = 300  # 5分钟
    gdelt_fetch_interval: int = 900  # 15分钟
    max_news_per_fetch: int = 100
    
    # 性能配置
    max_workers: int = 4
    batch_size: int = 10
    api_timeout: int = 30
    
    # Celery配置
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # 安全配置
    access_token_expire_minutes: int = 1440

    # 严格外部依赖（生产建议开启）。当开启时，服务不会回退到内存/SQLite。
    require_external_services: bool = False  # 全局严格模式
    require_redis: bool = False  # 仅Redis严格
    # 可按需扩展：require_postgres/require_chromadb
    
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # 忽略未声明的环境变量，避免跨服务变量导致报错
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_api_keys()
    
    def load_api_keys(self):
        """从文件加载多个API密钥"""
        try:
            # 使用Pathlib构建更健壮的路径
            root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
            keys_file = root_dir / "configs" / "api_keys.txt"
            
            if keys_file.exists():
                with open(keys_file, 'r', encoding='utf-8') as f:
                    keys = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.strip().startswith('#') and line.strip().startswith('sk-')
                    ]
                    
                    if keys:
                        self.deepseek_api_keys = keys
                        if not self.deepseek_api_key:
                            self.deepseek_api_key = keys[0]
                        print(f"已加载 {len(keys)} 个DeepSeek API密钥")
                    else:
                        print("未找到有效的API密钥")
            else:
                print(f"API密钥文件不存在: {keys_file}")
        except Exception as e:
            print(f"加载API密钥失败: {e}")
    
    # 注意：Pydantic v2 不允许同时定义 Config 和 model_config，这里仅使用 model_config。


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
