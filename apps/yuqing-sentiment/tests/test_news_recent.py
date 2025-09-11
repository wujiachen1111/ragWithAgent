import sys
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from types import SimpleNamespace

_tests_dir = Path(__file__).resolve().parent
_src_dir = _tests_dir.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from yuqing.api.news import router as news_router  # noqa: E402


class _DummyResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return SimpleNamespace(all=lambda: self._items)


class _DummyDB:
    def __init__(self):
        self._items = []

    def execute(self, *_args, **_kwargs):
        return _DummyResult(self._items)


def test_recent_returns_array_without_db():
    app = FastAPI()
    dummy = _DummyDB()

    # override dependency
    import yuqing.api.news as news_mod

    def get_db_override():
        return dummy

    news_mod.get_db = get_db_override  # type: ignore
    app.include_router(news_router, prefix="/api/v1/news")
    client = TestClient(app)

    r = client.get("/api/v1/news/recent?limit=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
