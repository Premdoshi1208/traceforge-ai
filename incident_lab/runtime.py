"""Controlled incident execution over real in-process HTTP service boundaries.

These are ASGI modules in a single process, not separately deployed services.
Each observation uses a fresh app, fixture module and telemetry collector.
"""
from __future__ import annotations

import asyncio
import importlib.util
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode

from incident_lab.scenarios import get_scenario, scenario_directory


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_trusted_fixture(scenario_id: str, healthy: bool = False):
    path = scenario_directory(scenario_id) / ("healthy.py" if healthy else "service.py")
    spec = importlib.util.spec_from_file_location(f"fixture_{scenario_id}_{uuid.uuid4().hex}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Trusted fixture could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def observe(scenario_id: str) -> dict[str, Any]:
    """Execute a healthy baseline and three real faulty checkout requests."""
    scenario = get_scenario(scenario_id)
    started = time.perf_counter()
    logs: list[dict] = []
    spans: list[dict] = []
    responses: list[dict] = []
    otel_provider = TracerProvider(resource=Resource.create({"service.name": "traceforge-incident-lab"}))
    tracer = otel_provider.get_tracer("traceforge.incident_lab")
    modules = {
        (name, healthy): load_trusted_fixture(name, healthy)
        for name in ("discount", "retry", "inventory") for healthy in (False, True)
    }
    app = FastAPI(title="TraceForge controlled incident lab", docs_url=None, openapi_url=None)

    @contextmanager
    def span(service: str, operation: str, trace_id: str, parent_id: str | None, phase: str):
        sid = uuid.uuid4().hex[:16]
        begin = time.perf_counter()
        record = {"id": sid, "span_id": sid, "trace_id": trace_id, "parent_id": parent_id,
                  "service": service, "name": operation, "phase": phase,
                  "started_at": now(), "start_ms": round((begin - started) * 1000, 3), "status": "ok"}
        with tracer.start_as_current_span(f"{service}.{operation}") as otel_span:
            context = otel_span.get_span_context()
            record["otel_trace_id"] = format(context.trace_id, "032x")
            record["otel_span_id"] = format(context.span_id, "016x")
            otel_span.set_attribute("traceforge.scenario", scenario_id)
            otel_span.set_attribute("traceforge.trace_id", trace_id)
            try:
                yield record
            except Exception as exc:
                record["status"] = "error"
                record["error"] = f"{type(exc).__name__}: {exc}"
                otel_span.record_exception(exc)
                raise
            finally:
                if record["status"] == "error":
                    otel_span.set_status(Status(StatusCode.ERROR))
                record["duration_ms"] = round((time.perf_counter() - begin) * 1000, 3)
                spans.append(record)

    def log(service: str, message: str, trace_id: str, level: str = "INFO", **fields):
        logs.append({"id": f"log-{len(logs) + 1}", "timestamp": now(), "service": service,
                     "level": level, "message": message, "trace_id": trace_id, **fields})

    def context(request: Request):
        return (request.headers["x-trace-id"], request.headers.get("x-parent-span"), request.headers.get("x-phase", "fault"))

    @app.get("/inventory/stock")
    async def inventory(request: Request):
        tid, parent, phase = context(request)
        with span("inventory", "GET /stock", tid, parent, phase):
            body = {"stock": {"available": 12}} if scenario_id == "inventory" and phase == "fault" else {"available": 12}
            log("inventory", "Stock response emitted", tid, contract="v2" if "stock" in body else "v1", phase=phase)
            return body

    @app.post("/provider/charge")
    async def provider(request: Request):
        tid, parent, phase = context(request)
        with span("payment-provider", "POST /charge", tid, parent, phase) as rec:
            if scenario_id == "retry" and phase == "fault":
                await asyncio.sleep(0.004)
                rec["status"] = "error"
                log("payment-provider", "Payment provider deadline exceeded", tid, "ERROR", phase=phase)
                return JSONResponse({"error": "payment provider deadline exceeded"}, status_code=504)
            return {"status": "paid"}

    @app.post("/payments/charge")
    async def payments(request: Request):
        tid, parent, phase = context(request)
        with span("payments", "POST /charge", tid, parent, phase) as rec:
            attempts = 0
            async def send():
                nonlocal attempts
                attempts += 1
                response = await client.post("/provider/charge", headers={"x-trace-id": tid, "x-parent-span": rec["id"], "x-phase": phase})
                if response.status_code == 504:
                    raise TimeoutError("payment provider deadline exceeded")
                return response.json()
            try:
                result = await modules[("retry", not (scenario_id == "retry" and phase == "fault"))].charge(send, 3)
                log("payments", "Payment authorized", tid, attempts=attempts, phase=phase)
                return result
            except TimeoutError as exc:
                rec["status"] = "error"
                log("payments", str(exc), tid, "ERROR", attempts=attempts, configured_max_attempts=3, phase=phase)
                return JSONResponse({"error": str(exc), "attempts": attempts}, status_code=504)

    @app.post("/orders")
    async def orders(request: Request):
        tid, parent, phase = context(request)
        with span("orders", "POST /orders", tid, parent, phase) as rec:
            headers = {"x-trace-id": tid, "x-parent-span": rec["id"], "x-phase": phase}
            payload = await request.json()
            try:
                total = modules[("discount", not (scenario_id == "discount" and phase == "fault"))].calculate_total(payload["subtotal"], payload["discount_percent"])
                inventory_response = await client.get("/inventory/stock", headers=headers)
                # Order validation retains the old contract in the faulty deployment.
                modules[("inventory", phase == "baseline")].validate_inventory(inventory_response.json(), payload["quantity"])
                payment_response = await client.post("/payments/charge", headers=headers)
                if payment_response.status_code != 200:
                    rec["status"] = "error"
                    return JSONResponse(payment_response.json(), status_code=504)
                log("orders", "Order created", tid, total=total, phase=phase)
                return {"order_id": uuid.uuid4().hex[:12], "total": total, "status": "confirmed"}
            except (TypeError, KeyError, ValueError) as exc:
                rec["status"] = "error"
                message = f"{type(exc).__name__}: {exc}"
                log("orders", message, tid, "ERROR", phase=phase, source=scenario["path"])
                return JSONResponse({"error": message}, status_code=500)

    @app.post("/gateway/checkout")
    async def gateway(request: Request):
        tid, parent, phase = context(request)
        with span("api-gateway", "POST /checkout", tid, parent, phase) as rec:
            response = await client.post("/orders", json=await request.json(), headers={"x-trace-id": tid, "x-parent-span": rec["id"], "x-phase": phase})
            rec["status"] = "error" if response.status_code >= 400 else "ok"
            log("api-gateway", "Checkout completed", tid, "ERROR" if response.status_code >= 400 else "INFO", status_code=response.status_code, phase=phase)
            return JSONResponse(response.json(), status_code=response.status_code)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://controlled-lab", timeout=5) as client:
        for phase in ["baseline", "fault", "fault", "fault"]:
            tid = uuid.uuid4().hex
            begin = time.perf_counter()
            response = await client.post("/gateway/checkout", json={"subtotal": 100, "discount_percent": "10", "quantity": 2}, headers={"x-trace-id": tid, "x-phase": phase})
            responses.append({"trace_id": tid, "phase": phase, "status_code": response.status_code, "duration_ms": round((time.perf_counter() - begin) * 1000, 3), "body": response.json()})
    otel_provider.shutdown()
    faulty = [r for r in responses if r["phase"] == "fault"]
    baseline = [r for r in responses if r["phase"] == "baseline"]
    return {
        "scenario_id": scenario_id, "controlled_scenario": True,
        "execution_boundary": "Real ASGI HTTP requests between instrumented modules in one process",
        "logs": logs, "traces": sorted(spans, key=lambda s: s["start_ms"]), "responses": responses,
        "metrics": {"requests": len(faulty), "errors": sum(r["status_code"] >= 400 for r in faulty),
                    "error_rate": sum(r["status_code"] >= 400 for r in faulty) / len(faulty),
                    "mean_latency_ms": round(sum(r["duration_ms"] for r in faulty) / len(faulty), 3),
                    "baseline_requests": len(baseline), "baseline_errors": sum(r["status_code"] >= 400 for r in baseline),
                    "downstream_requests": sum(s["service"] == "payment-provider" and s["phase"] == "fault" for s in spans)},
        "recent_changes": [{"id": f"controlled-{scenario_id}-deployment", "kind": "controlled_scenario_activation", "service": scenario["service"], "path": scenario["path"], "timestamp": logs[0]["timestamp"], "description": "Curated faulty fixture activated for this isolated run; not a real production deployment."}],
        "dependencies": [{"source": "api-gateway", "target": "orders"}, {"source": "orders", "target": "inventory"}, {"source": "orders", "target": "payments"}, {"source": "payments", "target": "payment-provider"}],
    }
