#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportUnusedImport=false
"""
Utility to reset or cleanup YuQing (news sentiment) tables for local testing.

Usage examples:
  - Drop and recreate all tables:
      python tools/db/yuqing_reset.py --recreate
  - Truncate data only:
      python tools/db/yuqing_reset.py --truncate

DATABASE_URL is taken from environment or from yuqing settings.
"""
from __future__ import annotations

import argparse
import os
from sqlalchemy import create_engine, text
from pathlib import Path
import sys

# Explicitly load .env from the project root to ensure DATABASE_URL is correct.
try:
    from dotenv import load_dotenv
    repo_root = Path(__file__).resolve().parents[2]
    dotenv_path = repo_root / ".env"
    if dotenv_path.exists():
        print(f"Loading environment from: {dotenv_path}")
        load_dotenv(dotenv_path=dotenv_path)
except ImportError:
    print("Warning: python-dotenv not installed, unable to load .env file.")


def _ensure_yuqing_on_path() -> None:
    """Add yuqing-sentiment/src to sys.path so imports work when run from repo root."""
    try:
        repo_root = Path(__file__).resolve().parents[2]
        src_path = repo_root / "apps" / "yuqing-sentiment" / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
    except Exception:
        pass


def _get_database_url() -> str:
    # Prefer env var to avoid importing app settings during failures
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Fallback to app settings
    _ensure_yuqing_on_path()
    from yuqing.core.database import engine

    return str(engine.url)


def _mask_url(url: str) -> str:
    try:
        # hide password in output
        if "@" in url and "://" in url:
            scheme, rest = url.split("://", 1)
            creds, host = rest.split("@", 1)
            if ":" in creds:
                user, _pwd = creds.split(":", 1)
                creds = f"{user}:****"
            return f"{scheme}://{creds}@{host}"
    except Exception:
        pass
    return url


def recreate_all() -> None:
    _ensure_yuqing_on_path()
    from yuqing.models.database_models import Base

    url = _get_database_url()
    # Prefer IPv4 loopback to avoid potential localhost/::1 auth rule issues
    url = url.replace("@localhost:", "@127.0.0.1:")
    print(f"Using DATABASE_URL={_mask_url(url)}")
    engine = create_engine(url, future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Recreated all yuqing tables.")


def truncate_all() -> None:
    _ensure_yuqing_on_path()
    from yuqing.models.database_models import (
        NewsItem,
        StockAnalysis,
        MentionedCompany,
        MentionedPerson,
        IndustryImpact,
        KeyEvent,
        Base,
    )

    url = _get_database_url().replace("@localhost:", "@127.0.0.1:")
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        # Disable FK checks for faster truncation when supported
        try:
            conn.execute(text("SET session_replication_role = 'replica';"))
        except Exception:
            pass

        for table in [
            KeyEvent.__table__,
            IndustryImpact.__table__,
            MentionedPerson.__table__,
            MentionedCompany.__table__,
            StockAnalysis.__table__,
            NewsItem.__table__,
        ]:
            conn.execute(text(f'TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE;'))

        try:
            conn.execute(text("SET session_replication_role = 'origin';"))
        except Exception:
            pass
    print("Truncated yuqing tables (with RESTART IDENTITY CASCADE).")


def main() -> None:
    parser = argparse.ArgumentParser(description="YuQing DB reset/cleanup helper")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--recreate", action="store_true", help="Drop and recreate all tables")
    g.add_argument("--truncate", action="store_true", help="Truncate data and reset sequences")
    args = parser.parse_args()

    if args.recreate:
        recreate_all()
    else:
        truncate_all()


if __name__ == "__main__":
    main()
