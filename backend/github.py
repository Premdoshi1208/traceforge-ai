"""Dispatch trusted verification workflow and retrieve its actual signed-in API artifact."""
import asyncio
import base64
import hashlib
import io
import json
import re
import time
import zipfile

import httpx

from backend.config import settings


class VerificationUnavailable(RuntimeError):
    pass


async def verify_on_github(scenario_id: str, after_source: str, run_id: str) -> dict:
    repository = settings.github_repository
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise VerificationUnavailable("A curated GitHub repository is not configured.")
    headers = {"Authorization": f"Bearer {settings.github_token.get_secret_value()}",
               "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    api = f"https://api.github.com/repos/{repository}"
    expected_title = f"verify-{run_id}"
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        # A run ID is an idempotency identity: discover before dispatching.
        async def lookup():
            response = await client.get(f"{api}/actions/workflows/verify-patch.yml/runs", params={"per_page": 50, "event": "workflow_dispatch"})
            response.raise_for_status()
            return next((r for r in response.json()["workflow_runs"] if r["display_title"] == expected_title), None)

        remote = await lookup()
        if remote is None:
            response = await client.post(f"{api}/actions/workflows/verify-patch.yml/dispatches", json={
                "ref": settings.github_ref, "inputs": {"scenario": scenario_id,
                "source_b64": base64.b64encode(after_source.encode()).decode(), "run_id": run_id}})
            if response.status_code != 204:
                raise VerificationUnavailable(f"GitHub verification dispatch returned HTTP {response.status_code}.")
        deadline = time.monotonic() + 480
        while time.monotonic() < deadline:
            await asyncio.sleep(5)
            remote = await lookup()
            if remote is None:
                continue
            from backend.storage import get_run, save_run
            persisted = get_run(run_id)
            if persisted and persisted.get("remote_job", {}).get("id") != remote["id"]:
                persisted["remote_job"] = {"id": remote["id"], "url": remote["html_url"],
                                           "commit_sha": remote["head_sha"]}
                save_run(persisted)
            if remote["status"] != "completed":
                continue
            artifacts_response = await client.get(f"{api}/actions/runs/{remote['id']}/artifacts")
            artifacts_response.raise_for_status()
            artifact = next((a for a in artifacts_response.json()["artifacts"]
                             if a["name"] == f"verification-{run_id}"), None)
            if not artifact:
                raise VerificationUnavailable(f"Verification job completed {remote['conclusion']} without its result artifact.")
            archive = await client.get(artifact["archive_download_url"])
            if archive.status_code == 302:
                # Do not forward the GitHub credential to the signed blob-storage URL.
                async with httpx.AsyncClient(timeout=30) as download:
                    archive = await download.get(archive.headers["location"])
            archive.raise_for_status()
            if len(archive.content) > 2_000_000:
                raise VerificationUnavailable("Verification artifact exceeds the size limit.")
            with zipfile.ZipFile(io.BytesIO(archive.content)) as zf:
                info = next((i for i in zf.infolist() if i.filename == "verification-result.json"), None)
                if info is None or info.file_size > 1_000_000:
                    raise VerificationUnavailable("Verification artifact is missing or too large.")
                result = json.loads(zf.read(info))
            if result.get("run_id") != run_id or result.get("scenario_id") != scenario_id:
                raise VerificationUnavailable("Verification artifact identity does not match this run.")
            if result.get("source_sha256") != hashlib.sha256(after_source.encode()).hexdigest():
                raise VerificationUnavailable("Verification artifact does not match the proposed patch.")
            result["verified"] = bool(result.get("verified") and remote["conclusion"] == "success"
                                      and result.get("before", {}).get("exit_code") not in (None, 0)
                                      and result.get("after", {}).get("exit_code") == 0
                                      and result.get("regression", {}).get("exit_code") == 0)
            result.update(mode="github_actions", job_url=remote["html_url"], job_id=remote["id"],
                          commit_sha=remote["head_sha"], artifact_id=artifact["id"])
            return result
        raise VerificationUnavailable("GitHub verification is still pending after the bounded polling window.")
