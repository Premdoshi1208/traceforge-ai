"""Fixed-argv subprocess verification of allowlisted scenario fixtures."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from incident_lab.scenarios import get_scenario, scenario_directory, scenario_source
from verification.policy import validate_patch

HARNESS = Path(__file__).with_name("_subprocess.py").resolve()


def _run(scenario_id: str, source: str, suite: str) -> dict:
    directory = scenario_directory(scenario_id)
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix=f"traceforge-{scenario_id}-") as temp:
        working_copy = Path(temp)
        (working_copy / "service.py").write_text(source)
        for filename in ["test_reproduction.py", "test_regression.py"]:
            shutil.copyfile(directory / filename, working_copy / filename)
        argv = [sys.executable, "-I", "-B", str(HARNESS), str(working_copy), suite]
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": temp, "TMPDIR": temp}
        try:
            result = subprocess.run(argv, cwd=temp, capture_output=True, text=True, timeout=10, env=env)
            exit_code = result.returncode
            output = (result.stdout + result.stderr)[-16_000:]
        except subprocess.TimeoutExpired:
            exit_code, output = 124, "Verification exceeded the 10-second execution deadline."
    return {"exit_code": exit_code, "output": output, "command": " ".join(argv),
            "duration_ms": round((time.perf_counter() - start) * 1000, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(), "suite": suite,
            "mode": "local_subprocess", "source_sha256": __import__("hashlib").sha256(source.encode()).hexdigest()}


def run_reproduction(scenario_id: str) -> dict:
    """Execute only the trusted, checked-in buggy fixture and its reproduction."""
    get_scenario(scenario_id)
    return _run(scenario_id, scenario_source(scenario_id), "test_reproduction")


def verify_patch(scenario_id: str, after_source: str) -> dict:
    """Execute proposed source only with explicit local/ephemeral-runner opt-in.

    Production must dispatch to GitHub Actions and must not enable this option.
    """
    patch = validate_patch(scenario_id, after_source)
    if os.environ.get("TRACEFORGE_ALLOW_LOCAL_EXECUTION") != "1":
        raise PermissionError("Local candidate execution is disabled. Use the GitHub verification runner.")
    before = run_reproduction(scenario_id)
    after = _run(scenario_id, patch["after"], "test_reproduction")
    regression = _run(scenario_id, patch["after"], "test_regression")
    expected = get_scenario(scenario_id)["expected_failure"]
    expected_failure_reproduced = before["exit_code"] == 1 and expected in before["output"]
    return {"before": before, "after": after, "regression": regression,
            "verified": expected_failure_reproduced and after["exit_code"] == 0 and regression["exit_code"] == 0,
            "expected_failure_reproduced": expected_failure_reproduced,
            "mode": "local_subprocess", "patch_path": patch["path"],
            "source_sha256": after["source_sha256"]}


def main() -> None:
    """GitHub Actions entrypoint. Candidate input is data, never interpolated in shell."""
    import base64
    scenario = os.environ.get("SCENARIO_ID", "")
    run_id = os.environ.get("INCIDENT_RUN_ID", "")
    encoded = os.environ.get("PATCH_SOURCE_B64", "")
    if len(encoded) > 12_000 or not run_id or len(run_id) > 100:
        raise SystemExit("Invalid verification input")
    output_path = Path("verification-result.json")
    try:
        source = base64.b64decode(encoded, validate=True).decode("utf-8")
        result = verify_patch(scenario, source)
        result.update({"mode": "github_actions", "run_id": run_id, "scenario_id": scenario,
                       "github_run_id": os.environ.get("GITHUB_RUN_ID"),
                       "commit_sha": os.environ.get("GITHUB_SHA"),
                       "repository": os.environ.get("GITHUB_REPOSITORY")})
        for key in ("before", "after", "regression"):
            result[key]["mode"] = "github_actions"
        output_path.write_text(json.dumps(result, indent=2))
    except (ValueError, PermissionError, UnicodeError) as exc:
        output_path.write_text(json.dumps({"verified": False, "mode": "github_actions", "run_id": run_id, "error": str(exc), "commit_sha": os.environ.get("GITHUB_SHA")}, indent=2))
        raise SystemExit(1)
    raise SystemExit(0 if result["verified"] else 1)


if __name__ == "__main__":
    main()
