import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from backend import storage
from backend.config import ROOT, settings
from backend.github import verify_on_github
from backend.security import actor_hash, admin_authorized, redact

logger = logging.getLogger("traceforge")
logging.basicConfig(level=logging.INFO, format="%(message)s")
_tasks: set[asyncio.Task] = set()
_launch_lock = asyncio.Lock()
TERMINAL = {"verified", "unverified", "failed", "interrupted", "awaiting_verification", "cancelled"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env == "production":
        if settings.database_url.get_secret_value().startswith("sqlite"):
            raise RuntimeError("Production requires durable PostgreSQL. Configure DATABASE_URL.")
        if not settings.session_secret.get_secret_value():
            raise RuntimeError("Production requires SESSION_SECRET.")
    storage.initialize()
    if settings.app_env == "development" and settings.effective_verification == "local":
        os.environ["TRACEFORGE_ALLOW_LOCAL_EXECUTION"] = "1"
    elif settings.app_env == "production":
        os.environ.pop("TRACEFORGE_ALLOW_LOCAL_EXECUTION", None)
    recovered = storage.recover_interrupted()
    logger.info(json.dumps({"event": "startup", "interrupted_runs": recovered,
                            "verification_mode": settings.effective_verification}))
    yield
    for task in _tasks:
        task.cancel()
    if _tasks:
        await asyncio.gather(*_tasks, return_exceptions=True)


app = FastAPI(title="TraceForge AI", version="1.0.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)


@app.middleware("http")
async def boundaries(request: Request, call_next):
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-origin write requests are not allowed."}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Cross-site write requests are not allowed."}, status_code=403)
        body = await request.body()
        if len(body) > settings.max_body_bytes:
            return JSONResponse({"detail": "Request body too large."}, status_code=413)
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(json.dumps({"event": "request_error", "request_id": request_id,
                                "type": type(exc).__name__}))
        response = JSONResponse({"detail": "The request could not be completed.", "request_id": request_id}, status_code=500)
    response.headers.update({"X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin",
        "X-Frame-Options": "DENY", "X-Request-ID": request_id,
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:; frame-ancestors 'none'"})
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    logger.info(json.dumps({"event": "http", "request_id": request_id, "method": request.method,
                           "path": request.url.path, "status": response.status_code,
                           "duration_ms": round((time.perf_counter() - started) * 1000, 2)}))
    return response


def client_identity(request: Request) -> str:
    # Use only the transport address; do not trust visitor-controlled forwarded headers.
    return actor_hash(request.client.host if request.client else "unknown")


@app.get("/healthz")
async def health():
    return {"status": "ok", "service": "traceforge", "version": "1.0.0"}


@app.get("/readyz")
async def ready():
    try:
        with storage.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "unavailable", "database": False}, status_code=503)
    return {"status": "ready", "database": True, "groq_configured": bool(settings.groq_api_key.get_secret_value())}


@app.get("/api/config")
async def config(request: Request):
    daily, session, active = storage.quota_counts(client_identity(request))
    return {"groq_configured": bool(settings.groq_api_key.get_secret_value()),
            "live_enabled": bool(settings.groq_api_key.get_secret_value()),
            "verification_mode": settings.effective_verification,
            "verification_notice": settings.verification_unavailable_reason,
            "models": [settings.reasoning_model, settings.efficient_model],
            "model_routing": {"reasoning": settings.reasoning_model, "efficient": settings.efficient_model},
            "limits": {"daily_runs": settings.daily_run_limit, "session_runs": settings.session_run_limit,
                       "concurrent_runs": settings.max_concurrent_runs, "model_requests": settings.max_model_requests,
                       "tokens": settings.max_tokens},
            "capacity": {"daily_remaining": max(0, settings.daily_run_limit - daily),
                         "session_remaining": max(0, settings.session_run_limit - session), "active": active},
            "github_url": f"https://github.com/{settings.github_repository}" if settings.github_repository else None,
            "storage": "postgresql" if not settings.database_url.get_secret_value().startswith("sqlite") else "sqlite-local",
            "controlled_scenarios": True, "deployment": settings.app_env}


@app.get("/api/scenarios")
async def scenarios():
    from incident_lab.scenarios import SCENARIOS
    return SCENARIOS


class Launch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: Literal["discount", "retry", "inventory"]


async def investigate(run: dict):
    from agent_engine import EngineConfig, execute
    async def save(current: dict):
        storage.save_run(redact(current))
    async def emit(agent: str, message: str, type: str = "step", data: dict | None = None):
        event = {"id": str(uuid.uuid4()), "type": type, "agent": agent, "message": message,
                 "data": data or {}, "created_at": datetime.now(UTC).isoformat()}
        run["events"].append(redact(event))
        await save(run)
        return event
    try:
        engine_config = EngineConfig(groq_api_key=settings.groq_api_key.get_secret_value(),
            reasoning_model=settings.reasoning_model, efficient_model=settings.efficient_model,
            verification_mode=settings.effective_verification, verify=verify_on_github,
            max_model_requests=settings.max_model_requests, max_tokens=settings.max_tokens,
            max_steps=settings.max_steps, max_duration_seconds=settings.max_duration_seconds,
            max_patch_attempts=settings.max_patch_attempts)
        await execute(run, emit, save, engine_config)
        # The public VERIFIED badge is gated by independently recorded tests and review.
        if run["status"] == "verified":
            verification = run.get("verification") or {}
            if not (verification.get("verified") and verification.get("before", {}).get("exit_code") not in (None, 0)
                    and verification.get("after", {}).get("exit_code") == 0
                    and verification.get("regression", {}).get("exit_code") == 0
                    and (run.get("review") or {}).get("approved")):
                run["status"] = "unverified"
                run["error"] = "Verification evidence did not satisfy every required condition."
        await save(run)
    except asyncio.CancelledError:
        run["status"] = "interrupted"
        run["error"] = "Investigation interrupted; evidence preserved."
        await save(run)
        raise
    except Exception as exc:
        run["status"] = "failed"
        run["error"] = f"Investigation could not complete ({type(exc).__name__}). Evidence is preserved."
        await emit("commander", run["error"], "error")
        await save(run)


@app.post("/api/runs", status_code=202)
async def launch(body: Launch, request: Request, idempotency_key: str | None = Header(default=None),
                 x_admin_token: str | None = Header(default=None)):
    if not settings.groq_api_key.get_secret_value():
        raise HTTPException(503, "Live inference is unavailable: the server Groq credential is not configured.")
    if idempotency_key and (len(idempotency_key) > 100 or not idempotency_key.isascii()):
        raise HTTPException(400, "Invalid idempotency key.")
    identity = client_identity(request)
    key = f"{identity[:16]}:{idempotency_key}" if idempotency_key else None
    async with _launch_lock:
        if key and (previous := storage.find_idempotency(key)):
            return redact(previous)
        daily, session, active = storage.quota_counts(identity)
        if daily >= settings.daily_run_limit or (session >= settings.session_run_limit and not admin_authorized(x_admin_token)):
            raise HTTPException(429, "Demo capacity reached. Explore completed investigations or return tomorrow.", headers={"Retry-After": "3600"})
        if active >= settings.max_concurrent_runs:
            raise HTTPException(429, "An investigation is already running. Please inspect its live evidence and try again later.", headers={"Retry-After": "30"})
        now = datetime.now(UTC).isoformat()
        run: dict = {"id": str(uuid.uuid4()), "scenario_id": body.scenario_id, "status": "queued",
               "created_at": now, "updated_at": now, "model": settings.reasoning_model,
               "events": [], "evidence": [], "hypotheses": [], "tool_invocations": [], "patch_attempts": [],
               "patch": None, "verification": None, "review": None, "report": None,
               "usage": {"requests": 0, "tokens": 0}, "error": None, "controlled_scenario": True}
        storage.insert_run(run, identity, key)
        task = asyncio.create_task(investigate(run))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    return run


@app.get("/api/runs")
async def runs(q: str = ""):
    records = storage.list_runs()
    if q:
        needle = q[:100].lower()
        records = [r for r in records if needle in json.dumps([r["scenario_id"], r["id"], r.get("hypotheses"), r.get("report")]).lower()]
    return redact(records)


def require_run(run_id: str) -> dict:
    run = storage.get_run(run_id)
    if not run:
        raise HTTPException(404, "Investigation not found.")
    return redact(run)


@app.get("/api/runs/{run_id}")
async def run_detail(run_id: str):
    return require_run(run_id)


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str, request: Request, last_event_id: str | None = Header(default=None)):
    require_run(run_id)
    async def stream():
        seen: set[str] = set()
        initial = require_run(run_id).get("events", [])
        if last_event_id and any(e["id"] == last_event_id for e in initial):
            for event in initial:
                seen.add(event["id"])
                if event["id"] == last_event_id:
                    break
        last_snapshot = ""
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline and not await request.is_disconnected():
            run = require_run(run_id)
            for event in run.get("events", []):
                if event["id"] not in seen:
                    seen.add(event["id"])
                    yield f"id: {event['id']}\ndata: {json.dumps(event)}\n\n"
            snapshot = json.dumps(run)
            if snapshot != last_snapshot:
                yield f"event: snapshot\ndata: {snapshot}\n\n"
                last_snapshot = snapshot
            if run["status"] in TERMINAL:
                yield f"event: complete\ndata: {json.dumps({'status': run['status']})}\n\n"
                break
            yield ": keepalive\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


@app.get("/api/runs/{run_id}/report", response_class=PlainTextResponse)
async def report(run_id: str):
    run = require_run(run_id)
    if not run.get("report"):
        raise HTTPException(409, "The report is not yet available.")
    return PlainTextResponse(str(run["report"]), headers={"Content-Disposition": f'attachment; filename="traceforge-{run_id}.md"'})


@app.get("/api/runs/{run_id}/patch", response_class=PlainTextResponse)
async def patch(run_id: str):
    run = require_run(run_id)
    if not run.get("patch"):
        raise HTTPException(409, "A patch is not yet available.")
    return PlainTextResponse(run["patch"]["diff"], headers={"Content-Disposition": f'attachment; filename="traceforge-{run_id}.patch"'})


@app.get("/api/runs/{run_id}/similar")
async def similar(run_id: str):
    run = require_run(run_id)
    # Deterministic token Jaccard retrieval. Similarity is never verification proof.
    import re
    def terms(r):
        return set(re.findall(r"[a-z]{3,}", json.dumps([r["scenario_id"], r.get("hypotheses", [])]).lower()))
    target = terms(run)
    matches = []
    for other in storage.list_runs():
        if other["id"] != run_id and other["status"] == "verified":
            words = terms(other)
            score = len(target & words) / max(1, len(target | words))
            matches.append({"run_id": other["id"], "scenario_id": other["scenario_id"], "similarity": round(score, 3)})
    return sorted(matches, key=lambda item: item["similarity"], reverse=True)[:5]


@app.post("/api/runs/{run_id}/approve")
async def approve(run_id: str, x_admin_token: str | None = Header(default=None)):
    if not admin_authorized(x_admin_token):
        raise HTTPException(401, "Owner authentication is required.")
    run = require_run(run_id)
    from agent_engine.engine import objectively_verified
    if not (run["status"] == "verified" and objectively_verified(run.get("verification"))
            and (run.get("review") or {}).get("approved") is True):
        raise HTTPException(409, "Only a fully verified repair can be approved.")
    return storage.record_approval(run_id)


@app.get("/api/evaluations")
async def evaluations():
    path = ROOT / "evaluations" / "results.json"
    suite = json.loads(path.read_text()) if path.exists() else {"cases": [], "summary": {"executed": 0}}
    records = storage.list_runs(1000)
    completed = [r for r in records if r["status"] in TERMINAL]
    suite["live_runs"] = {"total": len(records), "completed": len(completed),
        "verified": sum(r["status"] == "verified" for r in completed),
        "failed": sum(r["status"] == "failed" for r in completed),
        "model_requests": sum(r.get("usage", {}).get("requests", 0) for r in records),
        "tokens": sum(r.get("usage", {}).get("tokens", 0) for r in records),
        "note": "Engineering evaluation cases and live agent outcomes are measured separately."}
    return redact(suite)


dist = ROOT / "frontend" / "dist"
if (dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")


@app.get("/{path:path}")
async def frontend(path: str):
    if path.startswith("api/") or path in {".env", ".git/config"}:
        raise HTTPException(404)
    index = dist / "index.html"
    if not index.exists():
        return JSONResponse({"service": "TraceForge", "frontend": "Build frontend with npm run build", "docs": "/api/docs"})
    # Only static assets and SPA entrypoint; never serve arbitrary filesystem paths.
    candidate = (dist / path).resolve()
    if candidate.is_relative_to(dist.resolve()) and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(index)
