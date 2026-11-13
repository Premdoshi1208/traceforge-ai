# TraceForge AI

**Find the failure. Prove the fix.** An inspectable incident investigation and repair lab using real HTTP failures, Groq inference, LangGraph orchestration, and executable verification evidence.

## What works

Three controlled defects run against instrumented gateway, orders, payments, and inventory modules. A bounded investigation collects logs and spans, compares cited hypotheses, reproduces the defect, asks Groq for a constrained patch, runs original and patched tests, performs adversarial review, and produces a diff and postmortem. React exposes the full evidence chain, history, safety evaluations, and architecture.

These are intentionally seeded incidents. Service boundaries run in one process to fit free hosting; they are not separately deployed microservices. The UI never presents seeded failures as customer incidents or local verification as remote CI.

## Run locally

Requirements: Python 3.12+, uv, Node 22+, Git.

```sh
cp .env.example .env
# Configure GROQ_API_KEY in .env using your local editor.
make setup
make build
uv run alembic upgrade head
make dev
```

Open http://127.0.0.1:8000. `.env` is ignored by Git and Docker. Set `VERIFICATION_MODE=local` and `APP_ENV=development` for explicitly labeled isolated local verification. Production always forbids local candidate execution. SQLite is development-only; production requires PostgreSQL.

```sh
make test
make check
make evaluate
```

## Repository

- `backend/`: FastAPI, quotas, durable snapshots/audit entities, SSE, admin gates, GitHub integration, Alembic.
- `agent_engine/`: typed LangGraph, real Groq tool calling and strict schema stages, budgets/retries.
- `incident_lab/`: executable controlled scenarios, tests, actual HTTP telemetry.
- `verification/`: syntax/scope policy and isolated fixed-command test harness.
- `frontend/`: responsive React/TypeScript command center, code comparison, evidence inspectors.
- `evaluations/`: deterministic engineering evaluation results, separately labeled from LLM accuracy.

See [architecture](ARCHITECTURE.md), [security](SECURITY.md), [deployment](DEPLOYMENT.md), [evaluation](EVALUATION.md), and the [guided demo](DEMO.md). Public API specification: `/api/docs`.

## Honest limits

A fixture test verdict establishes correctness for that curated contract only. Model diagnosis/review are judgments. Execution history preserves unsuccessful attempts. Incomplete investigations are marked interrupted after restart; external actions are not automatically replayed. Remote verification requires GitHub Actions access and its actual artifacts. Patches are never automatically deployed. Free hosting can sleep and provider quotas can stop live runs.
