import sys
from pathlib import Path
import pytest

_tests_dir = Path(__file__).resolve().parent
_src_dir = _tests_dir.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from fastapi.testclient import TestClient  # noqa: E402
from analysis.models.agents import AnalysisRequestVO, TimeHorizon, RiskAppetite  # noqa: E402
from analysis.models.enhanced_agents import EnhancedAnalysisResponseVO  # noqa: E402


@pytest.mark.asyncio
async def test_api_execute_endpoint(monkeypatch):
    import importlib
    app = importlib.import_module("main").app

    async def exec_stub(self, request: AnalysisRequestVO) -> EnhancedAnalysisResponseVO:
        return EnhancedAnalysisResponseVO(
            success=True,
            message="ok",
            request_id="req-1",
            findings=None,
            decision=None,
            enhanced_decision={"risk_adjusted_confidence": 0.8},
            committee_minutes=None,
            analysis_duration_seconds=0.01,
            data_quality_score=0.9,
        )

    monkeypatch.setattr(
        "analysis.services.orchestrator.AnalysisOrchestrator.execute",
        exec_stub,
    )

    client = TestClient(app)
    payload = {
        "topic": "AI技术突破",
        "headline": "某公司发布革命性AI产品",
        "content": "预计将改变行业格局…",
        "symbols": ["000001", "600036"],
        "time_horizon": TimeHorizon.medium,
        "risk_appetite": RiskAppetite.balanced,
        "region": "CN",
        "max_iterations": 1,
    }
    resp = client.post("/api/v1/analysis/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["enhanced_decision"]["risk_adjusted_confidence"] == 0.8
