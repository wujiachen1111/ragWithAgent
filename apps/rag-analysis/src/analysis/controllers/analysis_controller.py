from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.agents import AnalysisRequestVO, TimeHorizon, RiskAppetite
from ..models.enhanced_agents import EnhancedAnalysisResponseVO
from ..services.orchestrator import AnalysisOrchestrator

router = APIRouter()
orchestrator = AnalysisOrchestrator()


@router.get("/")
async def health_check():
    return {
        "service": "analysis_orchestrator",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


def _adapt_payload_to_request(payload: Dict[str, Any]) -> AnalysisRequestVO:
    """允许两种结构入参并映射为统一模型：
    1) 内部结构: AnalysisRequestVO 字段
    2) 外部结构: {query, stock_codes, user_id, ...}
    """
    try:
        return AnalysisRequestVO.model_validate(payload)
    except Exception:
        pass

    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        raise HTTPException(status_code=422, detail="query is required and must be string")

    symbols = payload.get("stock_codes") or []
    if not isinstance(symbols, list):
        raise HTTPException(status_code=422, detail="stock_codes must be a list")

    th = payload.get("time_horizon")
    try:
        time_horizon = TimeHorizon(th) if th else TimeHorizon.medium
    except Exception:
        time_horizon = TimeHorizon.medium

    ra = payload.get("risk_appetite")
    try:
        risk_appetite = RiskAppetite(ra) if ra else RiskAppetite.balanced
    except Exception:
        risk_appetite = RiskAppetite.balanced

    return AnalysisRequestVO(
        topic=query[:60],
        headline=payload.get("headline") or query[:60],
        content=query,
        symbols=symbols,
        region=payload.get("region"),
        time_horizon=time_horizon,
        risk_appetite=risk_appetite,
        max_iterations=payload.get("max_iterations") or 1,
        request_id=payload.get("user_id"),
    )


@router.post("/execute", response_model=EnhancedAnalysisResponseVO)
async def execute_analysis(payload: Dict[str, Any]):
    try:
        request = _adapt_payload_to_request(payload)
        return await orchestrator.execute(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
