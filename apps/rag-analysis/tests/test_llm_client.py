import os
import sys
from pathlib import Path

_tests_dir = Path(__file__).resolve().parent
_src_dir = _tests_dir.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from analysis.services.llm_client import LLMClient  # noqa: E402


def test_llm_client_endpoint_normalization(monkeypatch):
    # Case 1: gateway root
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://api.deepseek.com/v1")
    c1 = LLMClient(timeout=1)
    assert c1.endpoint.endswith("/v1/chat/completions")

    # Case 2: already full endpoint
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://api.deepseek.com/v1/chat/completions")
    c2 = LLMClient(timeout=1)
    assert c2.endpoint.endswith("/v1/chat/completions")

    # Case 3: host without suffix
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://localhost:8002")
    c3 = LLMClient(timeout=1)
    assert c3.endpoint.endswith("/v1/chat/completions")
