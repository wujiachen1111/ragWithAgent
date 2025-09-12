from __future__ import annotations

from ..models.agents import AnalysisRequestVO
from ..models.enhanced_agents import EnhancedAnalysisResponseVO
from .graph_workflow import AnalysisGraph


class AnalysisOrchestrator:
    """多智能体编排器（基于 LangGraph 的 StateGraph）。"""

    def __init__(self):
        self.graph = AnalysisGraph()

    async def execute(self, request: AnalysisRequestVO) -> EnhancedAnalysisResponseVO:
        return await self.graph.run(request)
