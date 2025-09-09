"""
Stock Agent 服务入口
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from stock.core.config import settings
from stock.core.database import db_manager
from stock.core.logging import logger
from stock.api.stock_api import router as stock_router
from stock.api.rag_api import router as rag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 Stock Agent 服务启动中...")
    
    # 连接数据库
    if db_manager.connect():
        logger.info("✅ 数据库连接成功")
    else:
        logger.error("❌ 数据库连接失败")
    
    logger.info(f"✅ Stock Agent 服务已启动 - {settings.api.host}:{settings.api.port}")
    
    yield
    
    # 关闭时
    logger.info("🛑 Stock Agent 服务关闭中...")
    db_manager.disconnect()
    logger.info("✅ Stock Agent 服务已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description=settings.description,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stock_router)
app.include_router(rag_router)


@app.get("/", summary="服务根路径")
async def root():
    """服务根路径"""
    return {
        "service": "stock-agent",
        "version": settings.version,
        "description": settings.description,
        "status": "running",
        "docs_url": "/docs",
        "api_prefix": "/api/v1"
    }


@app.get("/meta", summary="服务元信息")
async def meta():
    """服务元信息"""
    return {
        "service": "stock-agent",
        "version": settings.version,
        "description": settings.description,
        "api": {
            "prefix": "/api/v1",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "database": {
            "type": "MongoDB",
            "database": settings.database.database
        }
    }


if __name__ == "__main__":
    # 运行服务
    uvicorn.run(
        app,
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug
    )
