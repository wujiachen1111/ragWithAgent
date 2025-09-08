import sys
from loguru import logger
from yuqing.core.config import settings


def setup_logging():
    """配置日志系统"""
    
    # 移除默认日志处理器
    logger.remove()
    
    # 控制台日志
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True
    )
    
    # 文件日志
    logger.add(
        "/Users/junhaowu/Desktop/服务外包竞赛/ragWithAgent/logs/yuqing/app.log",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )
    
    # 错误日志
    logger.add(
        "/Users/junhaowu/Desktop/服务外包竞赛/ragWithAgent/logs/yuqing/error.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="50 MB",
        retention="60 days",
        compression="zip",
        encoding="utf-8"
    )
    
    return logger


# 初始化日志
app_logger = setup_logging()
