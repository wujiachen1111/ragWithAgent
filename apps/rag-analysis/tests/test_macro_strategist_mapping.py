import sys
from pathlib import Path
import pytest

_tests_dir = Path(__file__).resolve().parent
_src_dir = _tests_dir.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from analysis.models.agents import AnalysisRequestVO  # noqa: E402
from analysis.services.agents.enhanced_roles import MacroStrategist  # noqa: E402


@pytest.mark.asyncio
async def test_macro_strategist_risk_list_mapping(monkeypatch):
    ms = MacroStrategist()

    async def fake_macro(*args, **kwargs):
        return {"k": "v"}

    async def fake_risks(self, req, client):
        return [
            {"risk_type": "地缘政治", "impact_level": "high"},
            {"risk_type": "通胀", "impact_level": "medium"},
        ]

    monkeypatch.setattr(MacroStrategist, "_analyze_macro_environment", fake_macro)
    monkeypatch.setattr(MacroStrategist, "_assess_policy_impact", fake_macro)
    monkeypatch.setattr(MacroStrategist, "_analyze_cross_market_dynamics", fake_macro)
    monkeypatch.setattr(MacroStrategist, "_evaluate_secular_trends", fake_macro)
    monkeypatch.setattr(MacroStrategist, "_synthesize_macro_view", lambda *a, **k: {"market_regime": "neutral"})
    monkeypatch.setattr(MacroStrategist, "_identify_regime_changes", lambda *a, **k: ["signal"])
    monkeypatch.setattr(MacroStrategist, "_assess_global_risks", fake_risks)
    monkeypatch.setattr(MacroStrategist, "_analyze_currency_effects", fake_macro)

    req = AnalysisRequestVO(
        topic="话题",
        headline="标题",
        content="内容",
        symbols=["600519"],
        region="CN",
    )

    mv = await ms.analyze(req)
    assert isinstance(mv.global_risk_factors, list)
    assert all(isinstance(x, str) for x in mv.global_risk_factors)
