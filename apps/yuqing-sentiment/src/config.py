"""
YuQing舆情分析系统配置
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

# 设置.env文件路径为项目根目录
# BASE_DIR 会指向 .../ragWithAgent/apps/yuqing-sentiment/src
# 因此，项目根目录是 BASE_DIR.parent.parent.parent
# 这样做可以确保无论在哪里运行脚本，都能正确加载.env
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

class DatabaseSettings(BaseModel):
    """数据库配置"""
    url: str = "postgresql://postgres:postgres@localhost:5432/news_analytics"

class RedisSettings(BaseModel):
    """Redis配置"""
    url: str = "redis://localhost:6379/0"

class ChromaSettings(BaseModel):
    """ChromaDB配置"""
    persist_directory: str = str(ROOT_DIR / "data" / "yuqing" / "chromadb")

class AppSettings(BaseModel):
    """应用配置"""
    app_name: str = "YuQing舆情分析系统"
    app_version: str = "2.0.0"
    debug: bool = False
    log_level: str = "INFO"
    api_keys_file: str = str(ROOT_DIR / "configs" / "api_keys.txt")


class Settings(BaseSettings):
    """
    主配置类，聚合所有配置并通过pydantic-settings从.env文件加载
    """
    # 指定.env文件位置和编码
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding='utf-8',
        # 允许从环境变量名称的前缀来匹配配置项
        # 例如, `DATABASE_URL` 会被加载到 `db.url`
        env_nested_delimiter='__'
    )

    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    chroma: ChromaSettings = ChromaSettings()
    app: AppSettings = AppSettings()

# 创建一个全局可用的配置实例
settings = Settings()

# 为了兼容旧代码，仍然保留一些顶层变量
# 但推荐使用 `settings.db.url` 这种方式访问
DATABASE_URL = settings.db.url
REDIS_URL = settings.redis.url
CHROMA_PERSIST_DIRECTORY = settings.chroma.persist_directory
APP_NAME = settings.app.app_name
APP_VERSION = settings.app.app_version
DEBUG = settings.app.debug
LOG_LEVEL = settings.app.log_level
API_KEYS_FILE = settings.app.api_keys_file
BASE_DIR = Path(__file__).resolve().parent.parent # 保持BASE_DIR的原始定义以防其他地方使用

