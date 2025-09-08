"""
多智能体分析编排服务 (Analysis Orchestrator)
面向Java集成的HTTP API：FastAPI
"""

from __future__ import annotations

import os
from fastapi import FastAPI

from analysis.controllers.analysis_controller import router as analysis_router


app = FastAPI(
    title="Analysis Orchestrator",
    description="多智能体辩证分析编排服务",
    version="0.1.0",
)

app.include_router(analysis_router)


@app.get("/meta")
async def meta():
    return {
        "service": "analysis_orchestrator",
        "version": "0.1.0",
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8010"))
    uvicorn.run(app, host=host, port=port)
