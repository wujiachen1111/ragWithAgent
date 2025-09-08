from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from yuqing.services.data_orchestrator import data_collection_orchestrator
from yuqing.services.entity_analysis_orchestrator import entity_analysis_orchestrator
from yuqing.services.data_cleanup_service import data_cleanup_service
from yuqing.core.logging import app_logger

router = APIRouter(prefix="/api/data", tags=["data_collection"])


class CollectionRequest(BaseModel):
    sources: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class CompanyNewsRequest(BaseModel):
    companies: List[str]
    sources: Optional[List[str]] = None


@router.post("/collect/analyze")
async def collect_and_analyze(background_tasks: BackgroundTasks):
    """采集数据并进行实体分析"""
    try:
        # 在后台运行完整管道
        background_tasks.add_task(run_full_pipeline_with_analysis)
        
        return {
            "message": "数据采集和分析任务已启动",
            "status": "started",
            "note": "采集和分析将在后台进行，包含实体识别功能"
        }
    except Exception as e:
        app_logger.error(f"启动数据采集和分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/recent")
async def analyze_recent_news(hours_back: int = 1):
    """分析最近采集的新闻"""
    try:
        results = await data_collection_orchestrator.analyze_collected_news(hours_back)
        
        return {
            "message": "新闻分析完成",
            "results": results
        }
    except Exception as e:
        app_logger.error(f"新闻分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/keywords")
async def collect_by_keywords(request: CollectionRequest):
    """按关键词采集数据"""
    try:
        if not request.keywords:
            raise HTTPException(status_code=400, detail="请提供关键词")
        
        results = await data_collection_orchestrator.collect_by_keywords(
            keywords=request.keywords,
            sources=request.sources
        )
        
        return {
            "message": "关键词采集完成",
            "results": results
        }
    except Exception as e:
        app_logger.error(f"关键词采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/companies")
async def collect_company_news(request: CompanyNewsRequest):
    """采集公司相关新闻"""
    try:
        results = await data_collection_orchestrator.collect_company_news(request.companies)
        
        return {
            "message": "公司新闻采集完成",
            "results": results
        }
    except Exception as e:
        app_logger.error(f"公司新闻采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_collection_status():
    """获取数据采集状态"""
    try:
        status = await data_collection_orchestrator.get_collection_status()
        return status
    except Exception as e:
        app_logger.error(f"获取采集状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_data(days_to_keep: int = 30):
    """清理旧数据"""
    try:
        if days_to_keep < 1:
            raise HTTPException(status_code=400, detail="保留天数必须大于0")
        
        results = await data_collection_orchestrator.cleanup_old_data(days_to_keep)
        
        return {
            "message": "数据清理完成",
            "results": results
        }
    except Exception as e:
        app_logger.error(f"数据清理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/google-news")
async def test_google_news():
    """测试Google News采集"""
    try:
        from yuqing.services.google_news_service import google_news_service
        
        # 测试采集
        results = await google_news_service.search_finance_news("股票", 5)
        
        return {
            "message": "Google News测试完成",
            "count": len(results),
            "samples": results[:3] if results else []
        }
    except Exception as e:
        app_logger.error(f"Google News测试失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/twitter")
async def test_twitter():
    """测试Twitter采集"""
    try:
        # Twitter服务未实现
        return {
            "message": "Twitter服务尚未实现",
            "status": "not_implemented"
        }
        
        return {
            "message": "Twitter测试完成",
            "count": len(results),
            "samples": results[:3] if results else []
        }
    except Exception as e:
        app_logger.error(f"Twitter测试失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/chinese-finance")
async def test_chinese_finance():
    """测试中文财经网站采集"""
    try:
        # 中文财经服务未实现
        return {
            "message": "中文财经服务尚未实现",
            "status": "not_implemented"
        }
    except Exception as e:
        app_logger.error(f"中文财经网站测试失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/gdelt")
async def test_gdelt():
    """测试GDELT采集"""
    try:
        # GDELT服务未实现
        return {
            "message": "GDELT服务尚未实现",
            "status": "not_implemented"
        }
    except Exception as e:
        app_logger.error(f"GDELT测试失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_data(days_to_keep: int = Query(3, description="保留数据的天数")):
    """清理旧数据"""
    try:
        hours_to_keep = days_to_keep * 24
        
        app_logger.info(f"开始清理 {days_to_keep} 天前的数据...")
        result = data_cleanup_service.cleanup_old_data(retention_hours=hours_to_keep)
        
        return {
            "message": f"数据清理完成，保留最近 {days_to_keep} 天的数据",
            "result": result
        }
    except Exception as e:
        app_logger.error(f"数据清理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/database")
async def get_database_stats():
    """获取数据库统计信息"""
    try:
        stats = data_cleanup_service.get_database_stats()
        return {
            "message": "数据库统计信息",
            "stats": stats
        }
    except Exception as e:
        app_logger.error(f"获取数据库统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_full_collection():
    """后台运行完整采集"""
    try:
        app_logger.info("开始后台数据采集...")
        results = await data_collection_orchestrator.collect_all_sources()
        app_logger.info(f"后台采集完成: {results}")
    except Exception as e:
        app_logger.error(f"后台采集失败: {e}")


async def run_full_pipeline_with_analysis():
    """后台运行完整管道和分析"""
    try:
        app_logger.info("开始后台完整管道执行...")
        results = await data_collection_orchestrator.full_pipeline_execution(enable_analysis=True)
        app_logger.info(f"后台完整管道执行完成: {results}")
    except Exception as e:
        app_logger.error(f"后台完整管道执行失败: {e}")
