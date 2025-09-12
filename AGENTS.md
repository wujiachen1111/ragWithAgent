# Repository Guidelines

## Project Structure & Module Organization
- Services: `apps/{yuqing-sentiment,rag-analysis,stock-agent,dashboard-ui}`; code in `src/`, tests in `tests/`.
- Shared libs: `libs/{common,database,messaging}` for cross-service utilities.
- Config: `configs/{environments,services}`. Tooling/data/logs: `scripts/`, `tools/`, `data/`, `logs/`.
- Deploy/infra: `docker-compose.yml`, `deployments/*`, `infrastructure/*`.
- Place service logic under `apps/<service>/src`; prefer Pydantic models for I/O schemas.

## Build, Test, and Development Commands
- Install deps: `pip install -r requirements.txt` and per-service `pip install -r apps/<service>/requirements.txt`.
- Run multiple services: `python start_all.py --services yuqing rag stock_agent`.
- Run one service: `cd apps/rag-analysis && python -m src.main` (similar for others).
- Docker: `docker-compose up -d` (start) / `docker-compose down` (stop).
- Lint/format: `ruff check --fix .` and `black apps/ libs/ tools/`.
- Pre-commit: `pre-commit install && pre-commit run -a`.
- Tests: `pytest -q` or scoped `pytest apps/rag-analysis/tests -q`. Integration: `python apps/stock-agent/tests/test_rag_integration.py`.

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indent; include type hints for new/changed code.
- Formatting: Black (line length 100). Linting: Ruff (rules E,W,F,I,B,C4,UP; ignores E501,B008,C901).
- Naming: modules/files `snake_case`; classes `PascalCase`; functions/vars `snake_case`; constants `UPPER_SNAKE_CASE`.

## Testing Guidelines
- Framework: pytest; place tests under `apps/<service>/tests`, files `test_*.py`.
- Use fixtures and `@pytest.mark.asyncio` for async code.
- Target ≥80% coverage on touched areas; keep unit tests fast.

## Commit & Pull Request Guidelines
- Commits: Conventional Commits (e.g., `feat: add RAG chunker`, `fix: handle empty query`).
- PRs: description/rationale, linked issues, tests for logic changes, passing lint/format/tests, and docs updates when configs/APIs change. Include screenshots or `curl` examples for API changes.

## Security & Configuration Tips
- Copy `.env.example` to `.env`; never commit secrets.
- Common envs: `DATABASE_URL`, `REDIS_URL`, `CHROMA_PERSIST_DIRECTORY`, service ports (`8000/8010/8020`).
- Local defaults fall back to SQLite/Redis-less where possible.

