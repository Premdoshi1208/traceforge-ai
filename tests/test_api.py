"""API integration and security tests with isolated durable state.

The investigation callback is explicitly replaced in these API tests. No test-only
callback or provider credential is used by production or counted as live inference.
"""
import asyncio
import copy
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine

from backend import main, security, storage

FAKE_KEY = "gsk_api_test_credential_never_a_real_key"
FAKE_ADMIN = "test-owner-token-with-sufficient-entropy"


def run_record(status="unverified", **changes):
    now = datetime.now(UTC).isoformat()
    value = {"id": str(uuid.uuid4()), "scenario_id": "discount", "status": status,
             "created_at": now, "updated_at": now, "model": "test-only-model",
             "events": [], "evidence": [], "hypotheses": [], "tool_invocations": [],
             "patch_attempts": [], "patch": None, "verification": None, "review": None,
             "report": None, "usage": {"requests": 0, "tokens": 0}, "error": None}
    value.update(changes)
    return value


def verified_record():
    test = {"exit_code": 0, "command": "test-only fixture command", "output": "test fixture result"}
    return run_record("verified", verification={"verified": True, "before": {**test, "exit_code": 1},
                                               "after": copy.deepcopy(test), "regression": copy.deepcopy(test)},
                      review={"approved": True, "summary": "Test-only stored fixture"})


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/api-test.db", connect_args={"check_same_thread": False})
    monkeypatch.setattr(storage, "engine", engine)
    monkeypatch.setattr(main.settings, "app_env", "test")
    monkeypatch.setattr(main.settings, "groq_api_key", SecretStr(FAKE_KEY))
    monkeypatch.setattr(main.settings, "admin_token", SecretStr(FAKE_ADMIN))
    monkeypatch.setattr(main.settings, "database_url", SecretStr(f"sqlite:///{tmp_path}/api-test.db"))
    monkeypatch.setattr(main.settings, "verification_mode", "unavailable")
    monkeypatch.setattr(main.settings, "daily_run_limit", 12)
    monkeypatch.setattr(main.settings, "session_run_limit", 2)
    monkeypatch.setattr(main.settings, "max_concurrent_runs", 1)
    monkeypatch.setattr(main, "_launch_lock", asyncio.Lock())
    monkeypatch.setattr(main, "_tasks", set())
    monkeypatch.setattr(security, "_sensitive_values", [FAKE_KEY, FAKE_ADMIN])
    async def test_only_investigation(run):
        run["status"] = "unverified"
        run["error"] = "Test-only callback: no model request or verification executed."
        storage.save_run(run)
    monkeypatch.setattr(main, "investigate", test_only_investigation)
    with TestClient(main.app) as client:
        yield client
    engine.dispose()


def test_health_readiness_and_secret_free_configuration(api):
    assert api.get("/healthz").json()["status"] == "ok"
    assert api.get("/readyz").json()["database"] is True
    response = api.get("/api/config")
    assert response.status_code == 200
    assert response.json()["groq_configured"] is True
    assert FAKE_KEY not in response.text and FAKE_ADMIN not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_readiness_fails_when_database_is_unreachable(api):
    with patch.object(storage.engine, "connect", side_effect=ConnectionError("test-only database failure")):
        response = api.get("/readyz")
    assert response.status_code == 503
    assert response.json()["database"] is False


def test_launch_requires_provider_configuration(api, monkeypatch):
    monkeypatch.setattr(main.settings, "groq_api_key", SecretStr(""))
    response = api.post("/api/runs", json={"scenario_id": "discount"})
    assert response.status_code == 503
    assert storage.list_runs() == []


def test_launch_is_idempotent_and_preserves_real_run_identity(api):
    headers = {"Idempotency-Key": "api-integration-once"}
    one = api.post("/api/runs", json={"scenario_id": "discount"}, headers=headers)
    two = api.post("/api/runs", json={"scenario_id": "discount"}, headers=headers)
    assert one.status_code == two.status_code == 202
    assert one.json()["id"] == two.json()["id"]
    assert len(storage.list_runs()) == 1
    assert api.get(f"/api/runs/{one.json()['id']}").json()["usage"]["requests"] == 0


@pytest.mark.parametrize("body", [
    {"scenario_id": "../../.env"}, {"scenario_id": "external-repo"},
    {"scenario_id": "discount", "command": "echo secret"}, {},
])
def test_launch_rejects_unallowlisted_input(api, body):
    assert api.post("/api/runs", json=body).status_code == 422
    assert storage.list_runs() == []


def test_oversized_body_and_idempotency_key_are_rejected(api):
    assert api.post("/api/runs", content="x" * (main.settings.max_body_bytes + 1)).status_code == 413
    assert api.post("/api/runs", json={"scenario_id": "discount"}, headers={"Idempotency-Key": "x" * 101}).status_code == 400


def test_cross_origin_and_cross_site_writes_are_rejected(api):
    payload = {"scenario_id": "discount"}
    assert api.post("/api/runs", json=payload, headers={"Origin": "https://attacker.example"}).status_code == 403
    assert api.post("/api/runs", json=payload, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert api.post("/api/runs", json=payload, headers={"Origin": "http://testserver"}).status_code == 202


def test_session_and_global_quotas(api, monkeypatch):
    monkeypatch.setattr(main.settings, "session_run_limit", 1)
    assert api.post("/api/runs", json={"scenario_id": "discount"}).status_code == 202
    limited = api.post("/api/runs", json={"scenario_id": "retry"})
    assert limited.status_code == 429
    assert "capacity" in limited.json()["detail"].lower()
    assert "Retry-After" in limited.headers
    monkeypatch.setattr(main.settings, "daily_run_limit", 1)
    assert api.post("/api/runs", json={"scenario_id": "retry"}, headers={"X-Admin-Token": FAKE_ADMIN}).status_code == 429


def test_concurrency_limit_is_enforced(api):
    storage.insert_run(run_record("investigating"), "another-visitor", None)
    response = api.post("/api/runs", json={"scenario_id": "discount"})
    assert response.status_code == 429
    assert "already running" in response.json()["detail"]


def test_owner_approval_requires_authentication_and_verified_status(api):
    run = run_record()
    storage.insert_run(run, "test", None)
    url = f"/api/runs/{run['id']}/approve"
    assert api.post(url).status_code == 401
    assert api.post(url, headers={"X-Admin-Token": "wrong"}).status_code == 401
    assert api.post(url, headers={"X-Admin-Token": FAKE_ADMIN}).status_code == 409


def test_owner_approval_is_idempotent(api):
    run = verified_record()
    storage.insert_run(run, "test", None)
    url = f"/api/runs/{run['id']}/approve"
    first = api.post(url, headers={"X-Admin-Token": FAKE_ADMIN})
    second = api.post(url, headers={"X-Admin-Token": FAKE_ADMIN})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert "Production was not modified" in first.json()["note"]


def test_owner_approval_rechecks_stored_execution_proof(api):
    # Simulates an inconsistent/corrupt historical record; status text is not proof.
    run = run_record("verified")
    storage.insert_run(run, "test", None)
    response = api.post(f"/api/runs/{run['id']}/approve", headers={"X-Admin-Token": FAKE_ADMIN})
    assert response.status_code == 409


def test_reports_patches_and_public_records_are_redacted(api):
    run = run_record(report=f"# Test report\nprovider={FAKE_KEY}\nowner={FAKE_ADMIN}",
                     patch={"diff": f"--- a/fixture.py\n+++ b/fixture.py\n+{FAKE_KEY}\n"},
                     evidence=[{"id": "test-evidence", "data": {"api_key": FAKE_KEY, "message": FAKE_ADMIN}}])
    storage.insert_run(run, "test", None)
    for path in ("/api/runs", f"/api/runs/{run['id']}", f"/api/runs/{run['id']}/report", f"/api/runs/{run['id']}/patch"):
        response = api.get(path)
        assert response.status_code == 200
        assert FAKE_KEY not in response.text and FAKE_ADMIN not in response.text
    assert "attachment" in api.get(f"/api/runs/{run['id']}/report").headers["content-disposition"]


def test_missing_artifacts_and_unknown_runs_have_explicit_errors(api):
    run = run_record()
    storage.insert_run(run, "test", None)
    assert api.get(f"/api/runs/{run['id']}/report").status_code == 409
    assert api.get(f"/api/runs/{run['id']}/patch").status_code == 409
    assert api.get("/api/runs/does-not-exist").status_code == 404


def test_event_stream_reconnect_respects_last_event_id(api):
    run = run_record(events=[{"id": "event-1", "message": "first"}, {"id": "event-2", "message": "second"}])
    storage.insert_run(run, "test", None)
    response = api.get(f"/api/runs/{run['id']}/events", headers={"Last-Event-ID": "event-1"})
    assert response.status_code == 200
    event_ids = [line for line in response.text.splitlines() if line.startswith("id: ")]
    assert event_ids == ["id: event-2"]
    assert "event: complete" in response.text


def test_recovery_preserves_records_and_does_not_replay_work(api):
    run = run_record("verifying", checkpoint={"next": "verifier"}, events=[{"id": "proof", "message": "Recorded before restart"}])
    storage.insert_run(run, "test", "restart-idempotency")
    assert storage.recover_interrupted() == 1
    recovered = api.get(f"/api/runs/{run['id']}").json()
    assert recovered["status"] == "interrupted"
    assert recovered["events"] == run["events"]
    assert storage.recover_interrupted() == 0
    assert storage.find_idempotency("restart-idempotency")["id"] == run["id"]


def test_source_secret_files_are_not_public(api):
    for path in ("/.env", "/.git/config", "/api/unknown"):
        response = api.get(path)
        assert response.status_code == 404
        assert FAKE_KEY not in response.text


def test_evaluation_response_separates_engineering_and_live_metrics(api):
    response = api.get("/api/evaluations")
    assert response.status_code == 200
    data = response.json()
    assert data["live_runs"]["model_requests"] == 0
    if data.get("kind") == "deterministic_engineering_evaluation":
        assert data["summary"]["diagnosis_accuracy"] is None


def test_signed_sessions_do_not_share_a_proxy_quota(api, monkeypatch):
    monkeypatch.setattr(main.settings, "session_run_limit", 1)
    first = api.post("/api/runs", json={"scenario_id": "discount"})
    assert first.status_code == 202
    assert "httponly" in first.headers["set-cookie"].lower()
    assert api.post("/api/runs", json={"scenario_id": "discount"}).status_code == 429
    with TestClient(main.app) as second_browser:
        second = second_browser.post("/api/runs", json={"scenario_id": "discount"})
        assert second.status_code == 202
        assert second_browser.cookies.get("tf_session") != api.cookies.get("tf_session")
    tampered_hash, replacement = security.session_identity("forged-session.invalid-signature")
    valid_hash, same_cookie = security.session_identity(replacement)
    assert tampered_hash == valid_hash and same_cookie == replacement
