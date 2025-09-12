import sys
from pathlib import Path
from loguru import logger
from yuqing.core.config import settings


def setup_logging():
    """配置日志系统，输出到控制台与仓库内 logs/yuqing 目录。"""

    logger.remove()

    # 控制台
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # 文件路径（项目根/logs/yuqing）
    try:
        project_root = Path(__file__).resolve().parents[5]
    except Exception:
        project_root = Path.cwd()
    logs_dir = project_root / "logs" / "yuqing"
    logs_dir.mkdir(parents=True, exist_ok=True)

    app_log = logs_dir / "app.log"
    err_log = logs_dir / "error.log"

    logger.add(
        app_log.as_posix(),
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    logger.add(
        err_log.as_posix(),
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="50 MB",
        retention="60 days",
        compression="zip",
        encoding="utf-8",
    )

    return logger


# 初始化日志
app_logger = setup_logging()
