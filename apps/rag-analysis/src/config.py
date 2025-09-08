"""
RAG分析服务配置
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# YuQing API配置
YUQING_API_URL = os.getenv("YUQING_API_URL", "http://localhost:8000")

# LLM网关配置
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:8002")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v3")

# 应用配置
APP_NAME = "RAG分析服务"
APP_VERSION = "0.1.0"
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
