# Architecture

The React/Vite build is served by FastAPI under one HTTPS origin. A single small web process runs the control plane and instrumented ASGI service modules. Each observation executes a healthy baseline and faulty traffic against a fresh fixture. Logs and spans correlate actual gateway, orders, payments, and inventory requests.

## Investigation

A typed LangGraph state machine coordinates commander, telemetry investigator, root-cause reasoner, reproduction engineer, patch engineer, adversarial reviewer, and reporter. The model selects permissioned telemetry tools using Groq tool calling. Diagnosis, patches, and review use separate strict JSON-schema requests. Model discovery checks both configured models. Context selection excludes duplicate full traces; request/token/time/step/attempt budgets and provider reset headers constrain work.

Tool inputs accept only curated scenario IDs. Source paths, test commands, provider origins, and repository are server-owned. Evidence IDs are validated before accepting model claims. Patch policy checks AST syntax, function signature, names, calls, constants, and source size before generating a real Git diff.

## Execution boundary

Original reproduction executes only checked-in trusted buggy source. Candidate code runs in local subprocesses only under explicit development opt-in, or in ephemeral GitHub-hosted runners. Production removes the opt-in and refuses local candidate execution. CI receives source as data through environment variables, validates it, copies trusted tests into a temporary workspace, strips environment credentials, enforces time/resource limits, and uploads machine-readable results. Checkout does not persist credentials; the job token has read-only contents permissions. Backend retrieval verifies run ID, scenario, source hash, workflow conclusion, and actual test exit codes.

VERIFIED requires original failure, patched reproduction success, regression success, and accepted adversarial review. Owner approval is separate. The system never applies generated patches to production.

## Persistence and recovery

PostgreSQL stores incident snapshots and indexed run identity/status. Audit entities normalize events, evidence, hypotheses, tool calls, patch attempts, verification, reviews, and reports. Approvals are idempotent and independently stored. JSON snapshots contain graph checkpoints after each node. On restart unfinished runs become interrupted with evidence intact. Automatic full graph resumption is deliberately not claimed. Similar incidents use deterministic token Jaccard similarity, never proof of a repair.

SQLite supports local development. Alembic owns production schema revisions. Application connections use the Neon pooler; migrations use a separate direct connection. No vector database, worker service, or paid scheduler is required.
