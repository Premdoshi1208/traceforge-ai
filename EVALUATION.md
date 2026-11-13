# Evaluation methodology

`uv run python -m evaluations.run` executes deterministic engineering cases and writes timestamped `evaluations/results.json`. Cases include three actual defects, bounded traffic, rejected unsafe patches, incorrect fixes, reproduction-only fixes rejected by regression, missing evidence, citation integrity, log prompt injection, timeout, and interrupted recovery. Each result records actual assertion/output/timing evidence.

These are engineering and security evaluations, not a measured LLM diagnosis benchmark. Unmeasured diagnosis/evidence accuracy is null. Do not relabel test suite pass rates as agent accuracy. Unit tests substitute model responses only inside test code; production makes real Groq requests.

Real Groq runs are stored independently in the application database with provider completion IDs, token usage, model IDs, original failures, patch attempts, actual test outcomes, reviewer judgments, and reports. Failed and unverified attempts remain visible. The Evaluation Arena reports actual counts from stored runs separately from engineering evaluation cases.

A verified curated fixture is not proof of safe behavior on arbitrary repositories or production systems. There are no customer reliability statistics, invented confidence percentages, or synthetic success counters.
