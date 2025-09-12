from __future__ import annotations

import sys
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from importlib.util import find_spec

# 确保本服务的 src 目录优先，避免与项目根级同名包冲突（如 services/*）
_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from yuqing.core import (
    settings,
    app_logger,
    init_db,
    check_db_connection,
    check_redis_connection,
    check_chroma_connection,
)
from yuqing.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    app_logger.info("正在启动新闻舆情分析系统...")
    
    # 检查数据库连接
    if not check_db_connection():
        app_logger.error("数据库连接失败，无法启动应用")
        raise Exception("数据库连接失败")
    
    # 初始化数据库（建表）
    try:
        init_db()
    except Exception as e:
        app_logger.error("数据库初始化失败，无法启动应用")
        raise
    
    # 检查Redis连接
    if not check_redis_connection():
        app_logger.error("Redis连接失败，无法启动应用")
        raise Exception("Redis连接失败")
    
    # 检查Chroma连接（可选，默认跳过以便本地/测试环境稳定）
    try:
        enable_vector = os.getenv("ENABLE_VECTOR_FEATURES", "0").lower() in {"1", "true", "yes"}
        if enable_vector and find_spec("chromadb") is not None:
            from yuqing.core import check_chroma_connection as _check_chroma
            if not _check_chroma():
                app_logger.warning("Chroma向量数据库连接失败，相关功能将受限")
        else:
            app_logger.info("已跳过Chroma向量数据库检查（设置 ENABLE_VECTOR_FEATURES=1 以启用）")
    except Exception as _e:
        app_logger.warning(f"跳过Chroma检查: {_e}")
    
    app_logger.info("系统启动完成")
    
    yield
    
    # 关闭时执行
    app_logger.info("正在关闭系统...")


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于多数据源的新闻舆情分析系统",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用新闻舆情股票分析系统",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    db_status = check_db_connection()
    redis_status = check_redis_connection()
    # 仅在启用向量功能时才检查
    try:
        enable_vector = os.getenv("ENABLE_VECTOR_FEATURES", "0").lower() in {"1", "true", "yes"}
        chroma_status = False
        if enable_vector and find_spec("chromadb") is not None:
            from yuqing.core import check_chroma_connection as _check_chroma
            chroma_status = _check_chroma()
    except Exception:
        chroma_status = False
    
    status = "healthy" if db_status and redis_status else "unhealthy"
    
    return JSONResponse(
        status_code=200 if status == "healthy" else 503,
        content={
            "status": status,
            "database": "connected" if db_status else "disconnected",
            "redis": "connected" if redis_status else "disconnected",
            "chroma": "connected" if chroma_status else "disconnected",
            "version": settings.app_version
        }
    )


# 注册API路由
app.include_router(api_router, prefix="/api")
# 提供版本化路径别名 /api/v1/*
app.include_router(api_router, prefix="/api/v1")

# 添加数据采集路由
from yuqing.api.data_collection import router as data_collection_router
app.include_router(data_collection_router)

# 添加实体分析路由
from yuqing.api.entity_analysis import router as entity_analysis_router
app.include_router(entity_analysis_router, prefix="/api")
app.include_router(entity_analysis_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "yuqing.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
