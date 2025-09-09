"""
股票数据 API 路由
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from datetime import datetime

from ..models.base import StockQuery, BatchProcessResult
from ..services.stock_service import StockService
from ..core.database import db_manager

router = APIRouter(prefix="/api/v1/stocks", tags=["股票数据"])

# 依赖注入
def get_stock_service() -> StockService:
    return StockService()


@router.get("/", summary="查询股票列表")
async def query_stocks(
    codes: Optional[List[str]] = Query(None, description="股票代码列表"),
    industries: Optional[List[str]] = Query(None, description="行业列表"),
    areas: Optional[List[str]] = Query(None, description="地区列表"),
    min_market_cap: Optional[float] = Query(None, description="最小市值(亿元)"),
    max_market_cap: Optional[float] = Query(None, description="最大市值(亿元)"),
    min_pe: Optional[float] = Query(None, description="最小市盈率"),
    max_pe: Optional[float] = Query(None, description="最大市盈率"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    service: StockService = Depends(get_stock_service)
):
    """
    根据条件查询股票数据
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        query = StockQuery(
            codes=codes,
            industries=industries,
            areas=areas,
            min_market_cap=min_market_cap,
            max_market_cap=max_market_cap,
            min_pe=min_pe,
            max_pe=max_pe,
            start_date=start_date,
            end_date=end_date
        )
        
        results = await service.query_stocks(query)
        
        return {
            "success": True,
            "data": results,
            "total": len(results),
            "message": f"查询到 {len(results)} 只股票"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询股票数据失败: {str(e)}")


@router.get("/{stock_code}", summary="获取单只股票详情")
async def get_stock_detail(
    stock_code: str,
    service: StockService = Depends(get_stock_service)
):
    """
    根据股票代码获取详细信息
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        result = await service.get_stock_by_code(stock_code)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"未找到股票 {stock_code} 的数据")
        
        return {
            "success": True,
            "data": result,
            "message": f"获取股票 {stock_code} 数据成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票数据失败: {str(e)}")


@router.get("/codes/all", summary="获取所有股票代码")
async def get_all_stock_codes(
    service: StockService = Depends(get_stock_service)
):
    """
    获取所有A股股票代码列表
    """
    try:
        codes = await service.get_all_stock_codes()
        
        return {
            "success": True,
            "data": codes,
            "total": len(codes),
            "message": f"获取到 {len(codes)} 个股票代码"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票代码失败: {str(e)}")


@router.get("/industries/all", summary="获取所有行业")
async def get_all_industries(
    service: StockService = Depends(get_stock_service)
):
    """
    获取所有行业列表
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        industries = await service.get_industries()
        
        return {
            "success": True,
            "data": industries,
            "total": len(industries),
            "message": f"获取到 {len(industries)} 个行业"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取行业列表失败: {str(e)}")


@router.get("/areas/all", summary="获取所有地区")
async def get_all_areas(
    service: StockService = Depends(get_stock_service)
):
    """
    获取所有地区列表
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        areas = await service.get_areas()
        
        return {
            "success": True,
            "data": areas,
            "total": len(areas),
            "message": f"获取到 {len(areas)} 个地区"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取地区列表失败: {str(e)}")


@router.get("/industry/{industry}/codes", summary="获取行业股票代码")
async def get_industry_stock_codes(
    industry: str,
    service: StockService = Depends(get_stock_service)
):
    """
    获取指定行业的所有股票代码
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        codes = await service.get_stocks_by_industry(industry)
        
        return {
            "success": True,
            "data": codes,
            "total": len(codes),
            "industry": industry,
            "message": f"{industry} 行业有 {len(codes)} 只股票"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取行业股票代码失败: {str(e)}")


@router.post("/fetch/single", summary="获取单只股票数据")
async def fetch_single_stock(
    stock_code: str,
    service: StockService = Depends(get_stock_service)
):
    """
    获取并保存单只股票的完整数据
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        success = await service.fetch_and_save_stock(stock_code)
        
        if success:
            return {
                "success": True,
                "data": {"stock_code": stock_code},
                "message": f"股票 {stock_code} 数据获取成功"
            }
        else:
            raise HTTPException(status_code=500, detail=f"股票 {stock_code} 数据获取失败")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票数据失败: {str(e)}")


@router.post("/fetch/batch", summary="批量获取股票数据")
async def fetch_batch_stocks(
    stock_codes: List[str],
    batch_size: int = Query(50, description="批处理大小"),
    service: StockService = Depends(get_stock_service)
):
    """
    批量获取并保存股票数据
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        result = await service.batch_fetch_stocks(stock_codes, batch_size)
        
        return {
            "success": True,
            "data": result,
            "message": f"批量处理完成: 成功 {result.success}/{result.total}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量获取股票数据失败: {str(e)}")


@router.get("/stats/database", summary="获取数据库统计")
async def get_database_stats(
    service: StockService = Depends(get_stock_service)
):
    """
    获取数据库统计信息
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        stats = await service.get_database_stats()
        
        return {
            "success": True,
            "data": stats,
            "message": "数据库统计信息获取成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据库统计失败: {str(e)}")


@router.get("/health", summary="健康检查")
async def health_check():
    """
    服务健康检查
    """
    try:
        # 检查数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        # 简单查询测试
        count = db_manager.stocks_collection.count_documents({})
        
        return {
            "success": True,
            "status": "healthy",
            "database": "connected",
            "stock_count": count,
            "timestamp": datetime.now(),
            "message": "Stock Agent 服务运行正常"
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(),
            "message": "Stock Agent 服务异常"
        }

