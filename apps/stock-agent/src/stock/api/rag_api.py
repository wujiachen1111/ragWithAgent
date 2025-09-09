"""
RAG-Analysis 系统集成 API
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel

from ..services.rag_integration import RAGIntegrationAdapter
from ..core.database import db_manager

router = APIRouter(prefix="/api/v1/rag", tags=["RAG集成"])


class MarketContextRequest(BaseModel):
    """市场上下文请求模型"""
    symbols: List[str]
    time_horizon: str = "medium"


class SectorAnalysisRequest(BaseModel):
    """行业分析请求模型"""
    industry: str
    limit: int = 20


class ComparativeAnalysisRequest(BaseModel):
    """对比分析请求模型"""
    symbols: List[str]


# 依赖注入
def get_rag_adapter() -> RAGIntegrationAdapter:
    return RAGIntegrationAdapter()


@router.post("/market-context", summary="获取市场上下文")
async def get_market_context(
    request: MarketContextRequest,
    adapter: RAGIntegrationAdapter = Depends(get_rag_adapter)
):
    """
    为 RAG-Analysis 系统提供市场上下文数据
    
    支持的时间范围:
    - immediate: 实时数据
    - short: 短期(1-7天)
    - medium: 中期(1-4周)
    - long: 长期(1-3月)
    - extended: 扩展期(3月以上)
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        context = await adapter.provide_market_context(
            request.symbols,
            request.time_horizon
        )
        
        return {
            "success": True,
            "data": context,
            "message": f"获取 {len(request.symbols)} 只股票的市场上下文成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取市场上下文失败: {str(e)}")


@router.post("/sector-analysis", summary="获取行业分析")
async def get_sector_analysis(
    request: SectorAnalysisRequest,
    adapter: RAGIntegrationAdapter = Depends(get_rag_adapter)
):
    """
    获取指定行业的分析数据
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        analysis = await adapter.get_sector_analysis(
            request.industry,
            request.limit
        )
        
        if "error" in analysis:
            raise HTTPException(status_code=400, detail=analysis["error"])
        
        return {
            "success": True,
            "data": analysis,
            "message": f"获取 {request.industry} 行业分析成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取行业分析失败: {str(e)}")


@router.post("/comparative-analysis", summary="获取对比分析")
async def get_comparative_analysis(
    request: ComparativeAnalysisRequest,
    adapter: RAGIntegrationAdapter = Depends(get_rag_adapter)
):
    """
    获取多只股票的对比分析数据
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        analysis = await adapter.get_comparative_analysis(request.symbols)
        
        if "error" in analysis:
            raise HTTPException(status_code=400, detail=analysis["error"])
        
        return {
            "success": True,
            "data": analysis,
            "message": f"获取 {len(request.symbols)} 只股票的对比分析成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对比分析失败: {str(e)}")


@router.get("/market-context/{symbol}", summary="获取单只股票上下文")
async def get_single_stock_context(
    symbol: str,
    time_horizon: str = Query("medium", description="时间范围"),
    adapter: RAGIntegrationAdapter = Depends(get_rag_adapter)
):
    """
    获取单只股票的市场上下文数据
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        context = await adapter.provide_market_context([symbol], time_horizon)
        
        return {
            "success": True,
            "data": context,
            "message": f"获取股票 {symbol} 的市场上下文成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票上下文失败: {str(e)}")


@router.get("/sectors/{industry}/summary", summary="获取行业摘要")
async def get_industry_summary(
    industry: str,
    limit: int = Query(10, description="返回股票数量"),
    adapter: RAGIntegrationAdapter = Depends(get_rag_adapter)
):
    """
    获取行业摘要信息（简化版）
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        analysis = await adapter.get_sector_analysis(industry, limit)
        
        if "error" in analysis:
            raise HTTPException(status_code=400, detail=analysis["error"])
        
        # 返回摘要信息
        summary = {
            "industry": analysis["industry"],
            "total_companies": analysis["total_companies"],
            "sector_metrics": analysis["sector_metrics"],
            "top_companies": analysis["companies"][:5]  # 只返回前5家公司
        }
        
        return {
            "success": True,
            "data": summary,
            "message": f"获取 {industry} 行业摘要成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取行业摘要失败: {str(e)}")


@router.get("/integration/test", summary="RAG集成测试")
async def test_rag_integration(
    adapter: RAGIntegrationAdapter = Depends(get_rag_adapter)
):
    """
    测试 RAG-Analysis 系统集成
    """
    try:
        # 确保数据库连接
        if not db_manager.client:
            db_manager.connect()
            
        # 使用示例数据进行测试
        test_symbols = ["000001", "600036", "000002"]
        
        # 测试市场上下文
        context = await adapter.provide_market_context(test_symbols, "medium")
        
        # 测试行业分析
        sector = await adapter.get_sector_analysis("银行", 5)
        
        # 测试对比分析
        comparison = await adapter.get_comparative_analysis(test_symbols[:2])
        
        return {
            "success": True,
            "data": {
                "market_context_test": "success" if "data" in context else "failed",
                "sector_analysis_test": "success" if "companies" in sector else "failed",
                "comparative_analysis_test": "success" if "comparison" in comparison else "failed",
                "test_symbols": test_symbols,
                "integration_status": "ready"
            },
            "message": "RAG集成测试完成"
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": {
                "integration_status": "error",
                "error": str(e)
            },
            "message": f"RAG集成测试失败: {str(e)}"
        }

