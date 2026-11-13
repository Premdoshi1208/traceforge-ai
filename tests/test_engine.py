"""Deterministic engine policy tests. Model mocks are test-only, never production."""

import copy
import json

import httpx
import pytest

from agent_engine.engine import EngineConfig, execute, objectively_verified
from agent_engine.groq_client import EngineError, GroqClient, redact, retry_delay
from agent_engine.schemas import Diagnosis, validate_citations


def passing_evidence():
    return {
        "verified": True,
        "before": {"exit_code": 1, "command": "python -m unittest", "output": "FAIL TypeError"},
        "after": {"exit_code": 0, "command": "python -m unittest", "output": "OK"},
        "regression": {"exit_code": 0, "command": "python -m unittest", "output": "OK"},
    }


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(verified=False),
    lambda x: x["before"].update(exit_code=0),
    lambda x: x["after"].update(exit_code=1),
    lambda x: x["regression"].update(exit_code=1),
    lambda x: x["after"].update(output=""),
    lambda x: x.pop("regression"),
])
def test_cannot_claim_verified_without_full_execution_evidence(mutation):
    result = passing_evidence()
    assert objectively_verified(result)
    mutation(result)
    assert not objectively_verified(result)


def test_rejects_invented_and_ungrounded_evidence():
    with pytest.raises(ValueError):
        validate_citations({"evidence_ids": ["invented"]}, {"ev-001"})
    with pytest.raises(ValueError):
        validate_citations({"evidence_ids": ["ev-001"], "hypotheses": [{"supporting_evidence": [], "contradicting_evidence": [], "assessment": "supported"}]}, {"ev-001"})


def test_redaction_and_config_repr_hide_credentials():
    secret = "gsk_private_test_value"
    assert secret not in repr(EngineConfig(groq_api_key=secret))
    result = redact({"error": f"key={secret} db=postgresql://user:password@host/db token=gho_example"}, (secret,))
    assert secret not in json.dumps(result)
    assert "password" not in json.dumps(result)
    assert "gho_example" not in json.dumps(result)


def test_retry_after_and_provider_reset_headers():
    assert retry_delay(httpx.Headers({"Retry-After": "7"})) == 7
    assert retry_delay(httpx.Headers({"x-ratelimit-reset-tokens": "1m2.5s"})) == 62.5


async def test_request_budget_blocks_network_request():
    async def noop(*args, **kwargs):
        pass
    client = GroqClient(EngineConfig(max_model_requests=1), {"usage": {"requests": 1, "tokens": 0}}, noop, noop)
    try:
        with pytest.raises(EngineError, match="request budget"):
            await client.request("reasoner", {})
    finally:
        await client.close()


async def test_missing_key_is_honest_failure():
    run = {"id": "test-missing-key", "scenario_id": "discount", "status": "queued", "events": [], "usage": {"requests": 0, "tokens": 0}}
    async def emit(agent, message, type="step", data=None):
        run["events"].append({"agent": agent, "message": message, "type": type, "data": data})
    async def save(value):
        pass
    result = await execute(run, emit, save, EngineConfig())
    assert result["status"] == "failed"
    assert "not configured" in result["error"]
    assert result["usage"]["requests"] == 0
    assert not result.get("verification")


async def test_real_fixture_graph_with_test_only_mocked_model(monkeypatch):
    from incident_lab.scenarios import healthy_source
    monkeypatch.setenv("TRACEFORGE_ALLOW_LOCAL_EXECUTION", "1")
    async def discover(self):
        pass
    async def request(self, agent, payload):
        self.run["usage"]["requests"] += 1
        return {"tool_calls": [{"id": "test-call", "function": {"name": "query_logs", "arguments": "{}"}}]}
    async def structured(self, agent, system, data, schema, efficient=False):
        self.run["usage"]["requests"] += 1
        refs = [self.run["evidence"][0]["id"]]
        if agent == "reasoner":
            return {"root_cause": "Test model: string discount arithmetic", "hypotheses": [{"title": "Type mismatch", "explanation": "Controlled test response", "supporting_evidence": refs, "contradicting_evidence": [], "assessment": "supported"}], "evidence_ids": refs, "safe_to_patch": True, "missing_evidence": ""}
        if agent == "patcher":
            return {"source": healthy_source("discount"), "explanation": "Test-only model oracle", "evidence_ids": refs}
        return {"approved": True, "summary": "Test-only model review", "risks": ["Fixture scope"], "evidence_ids": refs}
    monkeypatch.setattr(GroqClient, "discover", discover)
    monkeypatch.setattr(GroqClient, "request", request)
    monkeypatch.setattr(GroqClient, "structured", structured)
    run = {"id": "unit-graph", "scenario_id": "discount", "status": "queued", "events": [], "usage": {"requests": 0, "tokens": 0}}
    snapshots = []
    async def emit(agent, message, type="step", data=None):
        run["events"].append({"agent": agent, "message": message, "type": type, "data": data})
    async def save(value):
        snapshots.append(copy.deepcopy(value))
    result = await execute(run, emit, save, EngineConfig(verification_mode="local"))
    assert result["status"] == "verified", result.get("error")
    assert objectively_verified(result["verification"])
    assert result["verification"]["mode"] == "local_subprocess"
    assert result["checkpoint"]["next"] == "end"
    assert result["pull_request_artifact"]["remote_created"] is False
    assert {"commander", "telemetry", "reasoner", "reproducer", "patcher", "reviewer", "reporter"} == set(result["agents"])
    assert any(s.get("checkpoint", {}).get("next") == "verifier" for s in snapshots)
    assert all(call["status"] == "succeeded" for call in result["tool_invocations"])


def test_structured_schema_forbids_unexpected_properties():
    schema = Diagnosis.model_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
