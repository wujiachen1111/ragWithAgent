# Repository Guidelines

## Project Structure & Module Organization
- apps: service apps at `apps/{yuqing-sentiment,rag-analysis,stock-agent,dashboard-ui}`. Each service uses `src/` for code and `tests/` for unit tests.
- libs: shared packages in `libs/{common,database,messaging}`.
- configs: environment and service configs in `configs/{environments,services}`.
- tooling: helper scripts in `scripts/` and `tools/`; data/logs in `data/` and `logs/`.
- deployments & infra: `docker-compose.yml`, `deployments/*`, and `infrastructure/*` for runtime setup.

## Build, Test, and Development Commands
- Install deps: `pip install -r requirements.txt` and per-service `pip install -r apps/<service>/requirements.txt`.
- Run locally (multi-service): `python start_all.py --services yuqing rag stock_agent`.
- Run a service: `cd apps/rag-analysis && python -m src.main` (similar for others).
- Docker: `docker-compose up -d` (start) and `docker-compose down` (stop).
- Lint/format: `ruff check --fix .` and `black apps/ libs/ tools/`.
- Pre-commit: `pre-commit install && pre-commit run -a`.
- Tests: `pytest -q` or scoped (e.g., `pytest apps/rag-analysis/tests -q`). Integration: `python apps/stock-agent/tests/test_rag_integration.py`.

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indent, type hints required for new/changed code.
- Black (line length 100) and Ruff enforced (E,W,F,I,B,C4,UP; ignores E501,B008,C901).
- Naming: modules/files snake_case; classes PascalCase; functions/vars snake_case; constants UPPER_SNAKE_CASE.
- Keep service code under `apps/<service>/src` and shared code in `libs/*`. Prefer Pydantic models for I/O schemas.

## Testing Guidelines
- Framework: pytest. Place tests under `apps/<service>/tests`, name files `test_*.py`.
- Use fixtures and `@pytest.mark.asyncio` for async behavior. Aim for ≥80% coverage on touched areas.
- Keep unit tests fast; use the integration script above for end-to-end checks when needed.

## Commit & Pull Request Guidelines
- Commits in history are mixed; adopt Conventional Commits going forward: `feat: …`, `fix: …`, `docs: …`, `chore: …`.
- PRs must: describe changes and rationale, reference issues, include test coverage for logic changes, pass lint/format/tests, and update docs if APIs/configs change. Add screenshots or curl examples for API changes when helpful.

## Security & Configuration Tips
- Copy `.env.example` to `.env`; never commit secrets. Local defaults fall back to SQLite/Redis-less where possible.
- Common envs: `DATABASE_URL`, `REDIS_URL`, `CHROMA_PERSIST_DIRECTORY`, service ports (`8000/8010/8020`).
