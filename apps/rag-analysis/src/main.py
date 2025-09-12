"""
多智能体分析编排服务 (Analysis Orchestrator)
面向Java集成的HTTP API：FastAPI
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from fastapi import FastAPI

# 确保本服务的 src 目录优先于项目根目录，避免与根级 `services` 包冲突
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from analysis.controllers.analysis_controller import (
    router as analysis_router,
    execute_analysis as _execute_analysis,
)
from config.settings import settings


app = FastAPI(
    title="Analysis Orchestrator",
    description="多智能体辩证分析编排服务",
    version="0.1.0",
)

app.include_router(analysis_router, prefix="/api/v1/analysis", tags=["Analysis"])

# Back-compat alias without /api prefix
app.add_api_route("/v1/analysis/execute", _execute_analysis, methods=["POST"])


@app.get("/meta")
async def meta():
    return {
        "service": "analysis_orchestrator",
        "version": "0.1.0",
    }


if __name__ == "__main__":
    import uvicorn
    # 使用settings对象来获取配置，不再硬编码
    uvicorn.run(
        app, 
        host=settings.api.host, 
        port=settings.api.port,
        reload=settings.api.debug
    )
