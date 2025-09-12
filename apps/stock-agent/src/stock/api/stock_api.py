"""
股票数据 API 路由
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from datetime import datetime

from ..models.base import StockQuery, BatchProcessResult, RefreshTask
from ..services.stock_service import StockService
from ..services.scheduler import StockRefreshScheduler
from ..core.database import db_manager

router = APIRouter(prefix="/api/v1/stocks", tags=["股票数据"])

# 依赖注入
def get_stock_service() -> StockService:
    return StockService()

def get_scheduler() -> StockRefreshScheduler:
    """获取调度器实例"""
    # 导入全局调度器实例
    import sys
    main_module = sys.modules.get('main')
    if main_module and hasattr(main_module, 'scheduler') and main_module.scheduler:
        return main_module.scheduler
    
    # 如果全局实例不可用，创建临时实例
    from ..models.base import SchedulerConfig
    config = SchedulerConfig()
    return StockRefreshScheduler(config)


@router.get("/", summary="查询股票列表")
async def query_stocks(
    codes: Optional[List[str]] = Query(None, description="股票代码列表"),
    industries: Optional[List[str]] = Query(None, description="行业列表"),
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


# ==================== 数据刷新相关API ====================

@router.post("/refresh/single/{stock_code}", summary="刷新单只股票数据")
async def refresh_single_stock(
    stock_code: str,
    scheduler: StockRefreshScheduler = Depends(get_scheduler)
):
    """
    刷新指定股票的数据
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
        
        # 执行单只股票刷新
        task = await scheduler.refresh_single_stock(stock_code)
        
        return {
            "success": True,
            "data": {
                "task_id": task.task_id,
                "stock_code": stock_code,
                "status": task.status,
                "start_time": task.start_time,
                "result": task.result.model_dump() if task.result else None
            },
            "message": f"股票 {stock_code} 刷新任务已完成"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新股票 {stock_code} 失败: {str(e)}")


@router.post("/refresh/global", summary="触发全局股票数据刷新")
async def trigger_global_refresh(
    scheduler: StockRefreshScheduler = Depends(get_scheduler)
):
    """
    手动触发全局股票数据刷新
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
        
        # 创建异步任务执行全局刷新
        import asyncio
        task_id = f"manual_global_refresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 在后台执行全局刷新
        asyncio.create_task(scheduler._execute_global_refresh())
        
        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "status": "started",
                "message": "全局刷新任务已启动，正在后台执行"
            },
            "message": "全局股票数据刷新任务已启动"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发全局刷新失败: {str(e)}")


@router.get("/refresh/tasks", summary="获取刷新任务列表")
async def get_refresh_tasks(
    limit: int = Query(10, description="返回任务数量"),
    scheduler: StockRefreshScheduler = Depends(get_scheduler)
):
    """
    获取最近的刷新任务列表
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
        
        tasks = await scheduler.get_recent_tasks(limit)
        
        return {
            "success": True,
            "data": [task.model_dump() for task in tasks],
            "total": len(tasks),
            "message": f"获取到 {len(tasks)} 个刷新任务"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取刷新任务失败: {str(e)}")


@router.get("/refresh/tasks/{task_id}", summary="获取刷新任务状态")
async def get_refresh_task_status(
    task_id: str,
    scheduler: StockRefreshScheduler = Depends(get_scheduler)
):
    """
    获取指定刷新任务的状态
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
        
        task = await scheduler.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"未找到任务 {task_id}")
        
        return {
            "success": True,
            "data": task.model_dump(),
            "message": f"任务 {task_id} 状态获取成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/scheduler/status", summary="获取调度器状态")
async def get_scheduler_status(
    scheduler: StockRefreshScheduler = Depends(get_scheduler)
):
    """
    获取调度器运行状态和配置信息
    """
    try:
        status = scheduler.get_scheduler_status()
        
        return {
            "success": True,
            "data": status,
            "message": "调度器状态获取成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取调度器状态失败: {str(e)}")

