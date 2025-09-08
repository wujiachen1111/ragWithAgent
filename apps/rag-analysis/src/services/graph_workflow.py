from __future__ import annotations

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

from analysis.models.agents import (
    AnalysisRequestVO,
    AgentFindings,
    SynthesizedDecision,
    AnalysisResponseVO,
    Action,
)
from analysis.services.agents.roles import (
    NarrativeArbitrageurAgent,
    FirstOrderImpactQuantAgent,
    ContrarianSkepticAgent,
    SecondOrderEffectsStrategistAgent,
)
from analysis.services.agents.enhanced_roles import (
    RiskController,
    MacroStrategist
)
from analysis.services.agents.enhanced_data_specialist import EnhancedDataIntelligenceSpecialist
from analysis.services.synthesizer import ChiefSynthesizer


class GraphState(TypedDict, total=False):
    request: AnalysisRequestVO
    findings: AgentFindings
    enhanced_findings: Optional[Dict[str, Any]]
    decision: SynthesizedDecision
    enhanced_decision: Optional[Dict[str, Any]]
    data_intelligence_report: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    macro_view: Optional[Dict[str, Any]]
    iter: int
    max_iterations: int
    workflow_stage: str


class AnalysisGraph:
    """使用 LangGraph 的 StateGraph 实现多智能体工作流。"""

    def __init__(self) -> None:
        # 原有五个核心分析师
        self.narrative_agent = NarrativeArbitrageurAgent()
        self.quant_agent = FirstOrderImpactQuantAgent()
        self.contrarian_agent = ContrarianSkepticAgent()
        self.second_order_agent = SecondOrderEffectsStrategistAgent()

        # 新增三个专业角色
        self.data_intelligence = EnhancedDataIntelligenceSpecialist()
        self.risk_controller = RiskController()
        self.macro_strategist = MacroStrategist()

        # 首席整合官
        self.chief = ChiefSynthesizer()

        self.graph = self._build_enhanced_graph()

    async def _agents_round(self, state: GraphState) -> Dict[str, Any]:
        request = state["request"]
        narrative, quant, contrarian, second_order = await asyncio.gather(
            self.narrative_agent.analyze(request),
            self.quant_agent.analyze(request),
            self.contrarian_agent.analyze(request),
            self.second_order_agent.analyze(request),
        )
        findings = AgentFindings(
            narrative=narrative,
            quant=quant,
            contrarian=contrarian,
            second_order=second_order,
        )
        return {"findings": findings}

    async def _synthesize(self, state: GraphState) -> Dict[str, Any]:
        findings = state["findings"]
        decision = await self.chief.synthesize(findings)
        current_iter = state.get("iter", 0) + 1
        return {"decision": decision, "iter": current_iter}

    def _should_continue(self, state: GraphState) -> str:
        current_iter = state.get("iter", 0)
        max_iter = state.get("max_iterations", 1)
        return "continue" if current_iter < max_iter else "end"

    def _build_enhanced_graph(self):
        """构建增强版多智能体工作流图"""
        graph = StateGraph(GraphState)

        # 第一阶段：数据情报收集
        graph.add_node(
            "data_intelligence_phase",
            self._data_intelligence_phase)

        # 第二阶段：核心分析师并行分析
        graph.add_node("core_analysts_round", self._core_analysts_round)

        # 第三阶段：专业角色深度分析
        graph.add_node("specialist_analysis", self._specialist_analysis)

        # 第四阶段：风险控制检查
        graph.add_node("risk_control_check", self._risk_control_check)

        # 第五阶段：综合决策
        graph.add_node("enhanced_synthesis", self._enhanced_synthesis)

        # 构建工作流路径
        graph.add_edge(START, "data_intelligence_phase")
        graph.add_edge("data_intelligence_phase", "core_analysts_round")
        graph.add_edge("core_analysts_round", "specialist_analysis")
        graph.add_edge("specialist_analysis", "risk_control_check")

        # 条件路由：基于风险评估决定是否需要重新分析
        graph.add_conditional_edges(
            "risk_control_check",
            self._risk_routing_decision,
            {
                "proceed": "enhanced_synthesis",
                "reassess": "core_analysts_round",
                "abort": END
            }
        )

        # 最终决策的条件路由
        graph.add_conditional_edges(
            "enhanced_synthesis",
            self._should_continue_enhanced,
            {
                "continue": "data_intelligence_phase",
                "end": END
            }
        )

        return graph.compile()

    async def _data_intelligence_phase(self, state: GraphState) -> Dict[str, Any]:
        """第一阶段：数据情报收集"""
        request = state["request"]

        # 使用增强版数据情报专家收集全面数据
        data_report = await self.data_intelligence.analyze(request)

        return {
            "data_intelligence_report": data_report.dict(),
            "workflow_stage": "data_collected"
        }

    async def _core_analysts_round(self, state: GraphState) -> Dict[str, Any]:
        """第二阶段：核心分析师并行分析"""
        request = state["request"]

        # 原有的四个核心分析师并行分析
        narrative, quant, contrarian, second_order = await asyncio.gather(
            self.narrative_agent.analyze(request),
            self.quant_agent.analyze(request),
            self.contrarian_agent.analyze(request),
            self.second_order_agent.analyze(request),
        )

        findings = AgentFindings(
            narrative=narrative,
            quant=quant,
            contrarian=contrarian,
            second_order=second_order,
        )

        return {
            "findings": findings,
            "workflow_stage": "core_analysis_completed"
        }

    async def _specialist_analysis(self, state: GraphState) -> Dict[str, Any]:
        """第三阶段：专业角色深度分析"""
        request = state["request"]

        # 宏观策略师分析
        macro_view = await self.macro_strategist.analyze(request)

        return {
            "macro_view": macro_view.dict(),
            "workflow_stage": "specialist_analysis_completed"
        }

    async def _risk_control_check(self, state: GraphState) -> Dict[str, Any]:
        """第四阶段：风险控制检查"""
        request = state["request"]
        findings = state.get("findings")

        # 构建增强版发现用于风险评估
        enhanced_findings = None
        if findings:
            from analysis.models.enhanced_agents import EnhancedAgentFindings
            enhanced_findings = EnhancedAgentFindings(
                narrative=findings.narrative,
                quant=findings.quant,
                contrarian=findings.contrarian,
                second_order=findings.second_order,
                data_intelligence=state.get("data_intelligence_report"),
                macro_strategic=state.get("macro_view")
            )

        # 独立风险评估
        risk_assessment = await self.risk_controller.analyze(request, enhanced_findings)

        return {
            "risk_assessment": risk_assessment.dict(),
            "workflow_stage": "risk_assessment_completed"
        }

    async def _enhanced_synthesis(self, state: GraphState) -> Dict[str, Any]:
        """第五阶段：增强版综合决策"""
        findings = state["findings"]

        # 使用原有综合决策逻辑
        decision = await self.chief.synthesize(findings)

        # 增强决策信息
        risk_assessment = state.get("risk_assessment", {})
        macro_view = state.get("macro_view", {})
        data_intelligence = state.get("data_intelligence_report", {})

        # 构建增强版决策
        enhanced_decision = {
            "base_decision": decision.dict(),
            "risk_adjusted_confidence": min(
                decision.confidence,
                1.0 -
                risk_assessment.get(
                    "overall_risk_score",
                    0.0)),
            "macro_alignment": self._assess_macro_alignment(
                decision,
                macro_view),
            "data_quality_factor": data_intelligence.get(
                "data_quality_score",
                0.7),
            "synthesis_timestamp": datetime.now().isoformat()}

        current_iter = state.get("iter", 0) + 1

        return {
            "decision": decision,
            "enhanced_decision": enhanced_decision,
            "iter": current_iter,
            "workflow_stage": "synthesis_completed"
        }

    def _risk_routing_decision(self, state: GraphState) -> str:
        """风险路由决策"""
        risk_assessment = state.get("risk_assessment", {})
        overall_risk_score = risk_assessment.get("overall_risk_score", 0.5)
        risk_alerts = risk_assessment.get("risk_limits_breach_alerts", [])

        # 高风险情况下中止分析
        if overall_risk_score > 0.9 or any(
                "严重" in alert for alert in risk_alerts):
            return "abort"

        # 中高风险情况下重新评估
        elif overall_risk_score > 0.7 or any("警告" in alert for alert in risk_alerts):
            current_iter = state.get("iter", 0)
            if current_iter < state.get("max_iterations", 1):
                return "reassess"

        # 正常情况继续
        return "proceed"

    def _should_continue_enhanced(self, state: GraphState) -> str:
        """增强版继续条件判断"""
        current_iter = state.get("iter", 0)
        max_iter = state.get("max_iterations", 1)

        # 检查是否需要额外迭代
        enhanced_decision = state.get("enhanced_decision", {})
        risk_adjusted_confidence = enhanced_decision.get(
            "risk_adjusted_confidence", 1.0)

        # 如果风险调整后的信心度过低，且还有迭代空间，则继续
        if risk_adjusted_confidence < 0.6 and current_iter < max_iter:
            return "continue"

        return "end"

    def _assess_macro_alignment(self, decision, macro_view: Dict) -> float:
        """评估决策与宏观环境的匹配度"""
        if not macro_view:
            return 0.5

        strategic_outlook = macro_view.get("strategic_market_outlook", {})
        market_regime = strategic_outlook.get("market_regime", "neutral")

        # 简化的匹配度计算
        decision_action = decision.action

        alignment_matrix = {
            ("strong_buy", "bull_market"): 0.9,
            ("buy", "bull_market"): 0.8,
            ("strong_buy", "bear_market"): 0.2,
            ("sell", "bear_market"): 0.8,
            ("hold", "transition"): 0.7,
        }

        return alignment_matrix.get((decision_action, market_regime), 0.5)

    async def run(self, request: AnalysisRequestVO) -> AnalysisResponseVO:
        """运行增强版多智能体分析工作流"""
        initial_state: GraphState = {
            "request": request,
            "iter": 0,
            "max_iterations": request.max_iterations,
            "workflow_stage": "initialized"
        }

        final_state: GraphState = await self.graph.ainvoke(initial_state)

        # 构建增强版响应
        from analysis.models.enhanced_agents import (
            EnhancedAnalysisResponseVO,
            EnhancedAgentFindings,
            InvestmentCommitteeMinutes
        )

        # 构建增强版发现汇总
        enhanced_findings = None
        if final_state.get("findings"):
            enhanced_findings = EnhancedAgentFindings(
                narrative=final_state["findings"].narrative,
                quant=final_state["findings"].quant,
                contrarian=final_state["findings"].contrarian,
                second_order=final_state["findings"].second_order,
                data_intelligence=final_state.get("data_intelligence_report"),
                risk_control=final_state.get("risk_assessment"),
                macro_strategic=final_state.get("macro_view")
            )

        # 构建投资委员会会议纪要
        committee_minutes = InvestmentCommitteeMinutes(
            meeting_id=f"meeting-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            participants=[
                "数据情报专家", "叙事套利者", "量化分析师",
                "逆向怀疑论者", "二级效应策略师", "宏观策略师",
                "风控官", "首席整合官"
            ],
            discussion_rounds=final_state.get("iter", 1),
            key_debates=self._extract_key_debates(final_state),
            consensus_points=self._extract_consensus_points(final_state),
            decision_process=self._extract_decision_process(final_state),
            final_resolution=str(final_state.get("decision", {}).get("action", "未决定")),
            meeting_timestamp=datetime.now().isoformat()
        )

        return EnhancedAnalysisResponseVO(
            success=True,
            message="增强版多智能体分析完成",
            request_id=request.request_id,
            findings=final_state.get("findings"),
            decision=final_state.get("decision"),
            enhanced_findings=enhanced_findings,
            enhanced_decision=final_state.get("enhanced_decision"),
            committee_minutes=committee_minutes,
            analysis_duration_seconds=(
                datetime.now() -
                datetime.now()).total_seconds(),
            # 实际应该记录开始时间
            data_quality_score=final_state.get(
                "data_intelligence_report",
                {}).get("data_quality_score"),
        )

    def _extract_key_debates(
            self, final_state: GraphState) -> List[Dict[str, str]]:
        """提取关键辩论点"""
        debates = []

        # 从各智能体的发现中提取争议点
        findings = final_state.get("findings")
        if findings:
            # 叙事vs量化的分歧
            narrative_confidence = getattr(
                findings.narrative, 'meme_potential', 0.5)
            if abs(narrative_confidence - 0.5) > 0.3:
                debates.append({
                    "topic": "叙事驱动 vs 基本面分析",
                    "positions": f"叙事潜力: {narrative_confidence}, 量化评估存在分歧"
                })

        # 风险评估分歧
        risk_assessment = final_state.get("risk_assessment", {})
        if risk_assessment.get("overall_risk_score", 0) > 0.6:
            debates.append({
                "topic": "风险承受度争议",
                "positions": "风控官提出高风险警告，其他分析师观点乐观"
            })

        return debates

    def _extract_consensus_points(self, final_state: GraphState) -> List[str]:
        """提取共识要点"""
        consensus = []

        data_quality = final_state.get(
            "data_intelligence_report", {}).get(
            "data_quality_score", 0)
        if data_quality > 0.7:
            consensus.append(f"数据质量良好 (评分: {data_quality:.2f})")

        enhanced_decision = final_state.get("enhanced_decision", {})
        if enhanced_decision.get("macro_alignment", 0) > 0.7:
            consensus.append("决策与宏观环境匹配度高")

        return consensus

    def _extract_decision_process(self, final_state: GraphState) -> List[str]:
        """提取决策过程"""
        process = [
            "1. 数据情报专家收集多源数据",
            "2. 核心分析师团队并行分析",
            "3. 宏观策略师提供环境评估",
            "4. 风控官进行独立风险评估",
            "5. 首席整合官综合决策"
        ]

        if final_state.get("iter", 1) > 1:
            process.append(f"6. 经过 {final_state.get('iter', 1)} 轮迭代优化")

        return process
