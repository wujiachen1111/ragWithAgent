"""
Tests for entity extraction and sentiment persistence with LLM calls mocked.

Requires Postgres + Redis running and reachable via env config.
"""
from __future__ import annotations

from typing import Any, Dict, List

import asyncio
import pytest
from fastapi.testclient import TestClient

from yuqing.main import app
from yuqing.core.database import get_db
from yuqing.models.database_models import NewsItem, StockAnalysis, MentionedCompany
from yuqing.services.deepseek_service import (
    deepseek_service,
    SentimentResult,
    EntityAnalysisResult,
    EntityInfo,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _insert_news(title: str = "用于实体测试的新闻") -> int:
    db = next(get_db())
    try:
        import uuid
        uid = uuid.uuid4().hex[:8]
        item = NewsItem(
            title=title,
            source="test_source",
            url=f"https://example.com/{title}-{uid}",
            content="苹果公司发布新芯片，预期将提振供应链。",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return int(item.id)
    finally:
        db.close()


def test_entity_extract_endpoint_persists(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    news_id = _insert_news("实体提取-1")

    async def fake_extract_entities(news_item: NewsItem) -> EntityAnalysisResult:
        companies: List[EntityInfo] = [
            EntityInfo(
                name="苹果公司",
                type="company",
                confidence=0.9,
                impact_type="direct",
                impact_direction="positive",
                impact_magnitude=0.8,
                additional_info={"stock_code": "AAPL", "exchange": "NASDAQ"},
            )
        ]
        persons: List[EntityInfo] = []
        return EntityAnalysisResult(
            companies=companies,
            persons=persons,
            industries=[{"name": "科技", "impact_direction": "positive", "impact_magnitude": 0.7}],
            events=[{"type": "product", "title": "新品发布", "market_significance": "major"}],
        )

    monkeypatch.setattr(deepseek_service, "extract_entities", fake_extract_entities)

    # Invoke endpoint
    resp = client.post("/api/analysis/entities/extract", params={"news_id": str(news_id)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["news_id"] == str(news_id)

    # Verify DB persistence
    db = next(get_db())
    try:
        analyses = db.query(StockAnalysis).filter(StockAnalysis.news_id == news_id).all()
        assert len(analyses) >= 1
        companies = db.query(MentionedCompany).all()
        assert len(companies) >= 1
    finally:
        db.close()


def test_sentiment_persist_and_list(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    news_id = _insert_news("情感分析-1")

    async def fake_analyze_single_news(news_item: NewsItem) -> SentimentResult:
        return SentimentResult(
            sentiment="positive",
            confidence=0.88,
            keywords=["芯片", "供应链"],
            summary="新品芯片发布利好供应链",
            market_impact="high",
            reasoning="技术迭代+成本下降预期",
        )

    monkeypatch.setattr(deepseek_service, "analyze_single_news", fake_analyze_single_news)

    # Use sync wrapper to persist analysis
    result: Dict[str, Any] = deepseek_service.sync_analyze_news(
        {
            "id": news_id,
            "title": "情感分析-1",
            "content": "苹果公司发布新芯片",
            "source": "test_source",
            "published_at": None,
        }
    )
    assert result is not None

    # Verify list endpoint returns the analysis
    resp = client.get("/api/analysis", params={"limit": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    rows = data["data"]
    assert any(r["news"]["id"] == news_id for r in rows)
