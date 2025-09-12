import sys
from pathlib import Path
import pytest

_tests_dir = Path(__file__).resolve().parent
_src_dir = _tests_dir.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from analysis.models.agents import (
    AnalysisRequestVO,
    TimeHorizon,
    RiskAppetite,
    NarrativeFinding,
    QuantImpact,
    ContrarianRisk,
    SecondOrderEffects,
)
from analysis.models.enhanced_agents import (
    DataIntelligenceReport,
    RiskControlAssessment,
    MacroStrategicView,
)


@pytest.mark.asyncio
async def test_graph_workflow_runs_with_stubs(monkeypatch):
    # Stub all agent analyses to avoid external I/O
    async def nf_analyze(self, req):
        return NarrativeFinding(
            one_liner="AI技术突破",
            meme_potential=0.6,
            influencers_take=["正面传播", "关注度高"],
            lifecycle_days=5,
            priced_in=False,
        )

    async def qi_analyze(self, req):
        return QuantImpact(
            pnl_line="P&L",
            magnitude="tens_of_millions",
            kpi_shifts_pct={"revenue_pct": 1.0},
            recurring=True,
        )

    async def cr_analyze(self, req):
        return ContrarianRisk(
            red_flags=["验证样本有限"],
            data_validity_risks=["渠道一致性"],
            overreaction_signals=["社媒热度偏高"],
        )

    async def so_analyze(self, req):
        return SecondOrderEffects(
            competitor_moves=["促销跟进"],
            regulatory_watchpoints=["关注消费者权益"],
            supply_chain_shift=["上游议价上升"],
            consumer_behavior_change=["短期转化提升"],
        )

    async def synthesize_stub(self, findings):
        from analysis.models.agents import SynthesizedDecision
        return SynthesizedDecision(
            action="hold",
            confidence=0.7,
            rationale="stub",
            key_drivers=["meme_potential"],
            risk_checks=[],
        )

    async def data_intel_stub(self, req):
        return DataIntelligenceReport(
            market_snapshot={"overall_sentiment": {"positive": 0.5}},
            sentiment_indicators={},
            key_financial_metrics={},
            market_anomalies=[],
            data_quality_score=0.8,
            data_sources_reliability={"sentiment_api": 0.8},
        )

    async def risk_stub(self, req, findings=None):
        return RiskControlAssessment(
            overall_risk_score=0.3,
            market_risk_metrics={},
            liquidity_risk_assessment={},
            concentration_risk_analysis={},
            regulatory_compliance_check={},
            decision_coherence_risk={},
            risk_control_recommendations=["正常监控"],
            stress_test_scenarios=[],
            risk_limits_breach_alerts=[],
            assessment_timestamp="2025-01-01T00:00:00",
        )

    async def macro_stub(self, req):
        return MacroStrategicView(
            macro_economic_backdrop={},
            policy_regime_analysis={},
            cross_market_correlations={},
            secular_trend_assessment={},
            strategic_market_outlook={"market_regime": "neutral"},
        )

    monkeypatch.setattr(
        "analysis.services.agents.roles.NarrativeArbitrageurAgent.analyze", nf_analyze
    )
    monkeypatch.setattr(
        "analysis.services.agents.roles.FirstOrderImpactQuantAgent.analyze", qi_analyze
    )
    monkeypatch.setattr(
        "analysis.services.agents.roles.ContrarianSkepticAgent.analyze", cr_analyze
    )
    monkeypatch.setattr(
        "analysis.services.agents.roles.SecondOrderEffectsStrategistAgent.analyze", so_analyze
    )
    monkeypatch.setattr(
        "analysis.services.synthesizer.ChiefSynthesizer.synthesize", synthesize_stub
    )
    monkeypatch.setattr(
        "analysis.services.agents.enhanced_data_specialist.EnhancedDataIntelligenceSpecialist.analyze",
        data_intel_stub,
    )
    monkeypatch.setattr(
        "analysis.services.agents.enhanced_roles.RiskController.analyze", risk_stub
    )
    monkeypatch.setattr(
        "analysis.services.agents.enhanced_roles.MacroStrategist.analyze", macro_stub
    )

    from analysis.services.graph_workflow import AnalysisGraph

    graph = AnalysisGraph()
    req = AnalysisRequestVO(
        topic="某公司发布革命性AI产品",
        headline="AI技术突破",
        content="预计将改变行业格局…",
        symbols=["000001", "600036"],
        time_horizon=TimeHorizon.medium,
        risk_appetite=RiskAppetite.balanced,
        region="CN",
        max_iterations=1,
    )
    result = await graph.run(req)

    assert result.success is True
    assert result.decision is not None
    assert result.enhanced_decision is not None
    assert result.findings is not None
