.PHONY: setup dev test build evaluate check
setup:
	uv sync --python 3.12
	cd frontend && npm ci
dev:
	uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
test:
	uv run pytest -q
	cd frontend && npm test -- --run
build:
	cd frontend && npm run build
evaluate:
	uv run python -m evaluations.run
check:
	uv run ruff check backend agent_engine incident_lab verification tests evaluations
	uv run mypy backend agent_engine
