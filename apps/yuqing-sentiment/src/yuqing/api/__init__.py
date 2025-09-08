"""
API路由模块
"""

from fastapi import APIRouter

# 导入各个API模块
from .news import router as news_router
from .analysis import router as analysis_router
from .data_collection import router as data_collection_router

# 创建API路由器
api_router = APIRouter()

# 注册子路由
api_router.include_router(news_router, prefix="/news", tags=["新闻"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["分析"])
api_router.include_router(data_collection_router, prefix="/data-collection", tags=["数据采集"])

# 根路由
@api_router.get("/")
async def api_root():
    return {
        "message": "新闻舆情分析API",
        "version": "1.0.0",
        "endpoints": {
            "news": "/api/news",
            "analysis": "/api/analysis",
            "docs": "/docs"
        }
    }
