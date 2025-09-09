"""
日志配置
"""

import sys
from loguru import logger
from pathlib import Path

from .config import settings


def setup_logging():
    """设置日志配置"""
    
    # 移除默认处理器
    logger.remove()
    
    # 控制台日志格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # 文件日志格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format=console_format,
        level="INFO" if not settings.api.debug else "DEBUG",
        colorize=True,
    )
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 添加文件处理器 - 普通日志
    logger.add(
        log_dir / "stock_agent.log",
        format=file_format,
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
    )
    
    # 添加文件处理器 - 错误日志
    logger.add(
        log_dir / "stock_agent_error.log",
        format=file_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )
    
    logger.info(f"日志系统已初始化，调试模式: {settings.api.debug}")


# 自动设置日志
setup_logging()

