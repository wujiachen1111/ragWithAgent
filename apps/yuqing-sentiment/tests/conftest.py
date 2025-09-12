from __future__ import annotations

import os
import sys
from pathlib import Path


def pytest_sessionstart(session):  # noqa: D401
    """Extend sys.path so tests can import yuqing.* directly."""
    repo_root = Path(__file__).resolve().parents[3]
    src_path = repo_root / "apps" / "yuqing-sentiment" / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Ensure .env is respected; DATABASE_URL/REDIS_URL may already be set by user
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
