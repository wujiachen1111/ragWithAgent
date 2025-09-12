from __future__ import annotations

from typing import Any, Dict
from datetime import datetime, timezone

import asyncio
import pytest
from fastapi.testclient import TestClient

from yuqing.main import app
from yuqing.core.database import get_db
from yuqing.models.database_models import NewsItem, StockAnalysis
from yuqing.services.hot_news_discovery import hot_news_discovery
from yuqing.services.google_news_service import google_news_service


@pytest.fixture(scope="function")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def ensure_db() -> None:
    # Ensure tables exist in case app startup wasn't triggered yet
    from yuqing.core.database import init_db
    init_db()


def _db_count() -> int:
    db = next(get_db())
    try:
        return db.query(NewsItem).count()
    finally:
        db.close()


def test_hot_discovery_persist_and_dedup() -> None:
    base: Dict[str, Any] = {
        "title": "热点-苹果新品发布",
        "content": "苹果公司发布新品，市场关注度上升",
        "source_url": "https://example.com/hot-apple",
        "published_at": datetime.now(timezone.utc),
        "summary": "新品发布",
    }
    # use unique URL per test run
    import uuid
    uid = uuid.uuid4().hex[:8]
    items = [
        {**base, "source_url": f"https://example.com/hot-apple-{uid}"},
        {**base, "source_url": f"https://example.com/hot-apple-{uid}"},
    ]
    before = _db_count()
    # Run coroutine in a dedicated loop to avoid interference
    loop = asyncio.new_event_loop()
    saved_1 = loop.run_until_complete(hot_news_discovery.save_to_database(items))
    assert saved_1 >= 1
    saved_2 = loop.run_until_complete(hot_news_discovery.save_to_database(items))
    loop.close()
    assert saved_2 == 0
    after = _db_count()
    assert after >= before + 1


def test_google_news_persist_and_list(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    import uuid
    uid1 = uuid.uuid4().hex[:8]
    uid2 = uuid.uuid4().hex[:8]
    gitems = [
        {
            "title": f"GoogleNews-测试1-{uid1}",
            "content": "测试内容1",
            "summary": "测试内容1",
            "source": "google_news",
            "source_url": f"https://example.com/gn-1-{uid1}",
            "published_at": now,
            "collected_at": now,
            "language": "zh",
            "region": "CN",
        },
        {
            "title": f"GoogleNews-测试2-{uid2}",
            "content": "测试内容2",
            "summary": "测试内容2",
            "source": "google_news",
            "source_url": f"https://example.com/gn-2-{uid2}",
            "published_at": now,
            "collected_at": now,
            "language": "zh",
            "region": "CN",
        },
    ]
    loop = asyncio.new_event_loop()
    saved = loop.run_until_complete(google_news_service.save_to_database(gitems))
    loop.close()
    assert saved >= 1

    # Validate stats endpoints
    r_stats = client.get("/api/news/stats", params={"hours": 48})
    assert r_stats.status_code == 200
    stats = r_stats.json()
    assert "total_news" in stats and stats["total_news"] >= 1

    r_src = client.get("/api/news/sources/stats", params={"hours": 48})
    assert r_src.status_code == 200
    sstats = r_src.json()
    assert "sources" in sstats and isinstance(sstats["sources"], dict)


def test_comprehensive_and_analysis_stats(client: TestClient) -> None:
    # Insert one analyzed news
    db = next(get_db())
    try:
        import uuid
        uid = uuid.uuid4().hex[:8]
        n = NewsItem(
            title=f"综合-已分析新闻-{uid}",
            source="test_source",
            url=f"https://example.com/comprehensive-1-{uid}",
            content="测试已分析内容",
            collected_at=datetime.now(timezone.utc),
        )
        db.add(n)
        db.commit()
        db.refresh(n)
        
        # 使用当前模型定义的正确字段来创建测试数据
        a = StockAnalysis(
            news_id=n.id,
            stock_code="000001",
            sentiment="neutral",
            confidence=0.55,
            analysis_summary="这是一个测试摘要",
        )
        db.add(a)
        db.commit()
    finally:
        db.close()

    # Comprehensive endpoint
    r = client.get("/api/news/comprehensive", params={"hours": 48, "limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert "data" in body and isinstance(body["data"], list)
    assert "summary" in body and "total_analyzed" in body["summary"]

    # Analysis list
    r2 = client.get("/api/analysis", params={"limit": 10})
    assert r2.status_code == 200
    d2 = r2.json()
    assert "data" in d2 and isinstance(d2["data"], list)

    # Sentiment stats and timeline
    r3 = client.get("/api/analysis/stats/sentiment", params={"hours": 48})
    assert r3.status_code == 200
    r4 = client.get("/api/analysis/stats/timeline", params={"hours": 48, "interval": 12})
    assert r4.status_code == 200


def test_data_status_endpoint(client: TestClient) -> None:
    resp = client.get("/api/data/status")
    assert resp.status_code == 200
    payload = resp.json()
    assert "database_status" in payload
    assert "services" in payload
