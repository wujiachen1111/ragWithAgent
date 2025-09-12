"""
E2E-style tests for news ingestion and listing.

Requires a running Postgres and Redis per env vars (DATABASE_URL, REDIS_URL).
"""
from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from yuqing.main import app
from yuqing.core.database import get_db
from yuqing.models.database_models import NewsItem
from yuqing.services.cailian_news_service import cailian_news_service
import asyncio


@pytest.fixture(scope="function")
def client() -> TestClient:
    # Using context manager ensures startup/shutdown events run
    with TestClient(app) as c:
        yield c


def _count_news_with_url(url: str) -> int:
    db = next(get_db())
    try:
        return db.query(NewsItem).filter(NewsItem.url == url).count()
    finally:
        db.close()


def test_seed_sample_and_recent_list(client: TestClient) -> None:
    # Seed sample news
    resp = client.post("/api/news/seed/sample", params={"count": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    inserted = data["inserted"]
    assert inserted >= 0

    # Recent list returns an array, capped by limit
    resp2 = client.get("/api/news/recent", params={"limit": 3})
    assert resp2.status_code == 200
    arr = resp2.json()
    assert isinstance(arr, list)
    assert len(arr) <= 3
    if arr:
        assert set(["id", "title", "source"]).issubset(arr[0].keys())


@pytest.mark.parametrize("dup_same", [True, False])
def test_cailian_save_to_database_dedup(dup_same: bool) -> None:
    # Build two items with same or different url to verify dedup path
    # Use unique content per test run so first save inserts
    import uuid
    uid = uuid.uuid4().hex[:8]
    base: Dict[str, Any] = {
        "title": f"财联社测试新闻-{uid}",
        "content": f"这是用于入库与去重的测试内容-{uid}",
        "source": "cailian",
        "source_url": "https://www.cls.cn/",  # normalized to homepage, will be hashed
        "published_at": "2024-01-01T00:00:00+00:00",
    }
    items = [base.copy(), base.copy()]
    if not dup_same:
        items[1]["title"] = "财联社测试新闻-变体"

    # Pre-count for the normalized URL after hashing
    # We don't know final URL suffix; just call and verify non-zero saved count and idempotency on second call
    saved_1 = asyncio.run(cailian_news_service.save_to_database(items))
    assert isinstance(saved_1, int)
    assert saved_1 >= 1

    saved_2 = asyncio.run(cailian_news_service.save_to_database(items))
    # Second save should not insert duplicates for identical payloads
    if dup_same:
        assert saved_2 == 0
    else:
        assert saved_2 >= 0
