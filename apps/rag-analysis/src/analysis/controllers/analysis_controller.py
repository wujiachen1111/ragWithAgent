from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, HTTPException

from ..models.agents import AnalysisRequestVO, AnalysisResponseVO
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


@router.post("/v1/analysis/execute", response_model=AnalysisResponseVO)
async def execute_analysis(request: AnalysisRequestVO):
    try:
        return await orchestrator.execute(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
