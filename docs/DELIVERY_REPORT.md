# TraceForge delivery and change summary

Public app: https://traceforge-ai-3pb0.onrender.com

Source: https://github.com/Premdoshi1208/traceforge-ai

## Neon setup requested by the owner

Followed the official skill at https://neon.com/.well-known/agent-skills/neon/SKILL.md . Initial inspection found no installed Neon project skills or Neon MCP registration. Installed `neon` and `neon-postgres` under `.agents/skills/`, added their official references and `skills-lock.json`, and verified every file against upstream GitHub blob hashes. Removed two byte-identical duplicate skill files after privately backing them up, then reconciled the lock hashes. `neon skills status` reports both skills up to date.

Added the Neon HTTPS MCP entry to the existing global Codex configuration. Verified the prior configuration was semantically preserved; `node_repl` and `computer-use` entries were unchanged. Completed OAuth authentication without putting an API key in project source. Removed the redundant project MCP entry created during setup. Exercised the authenticated MCP connection with read-only project and database queries. Detailed tooling changes are in [NEON_SETUP.md](NEON_SETUP.md).

For the original authorized product deployment, created a separate Neon Free project `traceforge-ai` (`wild-term-61414840`) in AWS Oregon with fixed 0.25 CU compute and the Free plan's default scale-to-zero behavior. The existing `firstsignal-staging` project was not modified. Linked `.neon` with `--no-env-pull` to preserve the development `.env`, and ignored the context file. Used pooled application and direct migration connection strings in private deployment settings.

## Product and repository changes

Built a responsive React/TypeScript application with landing page, mission control, streamed investigations, evidence and tool inspectors, trace waterfall, repair/code comparison, test output, postmortems, searchable history, evaluation cases, and interactive architecture. Its metrics are derived from stored executions.

Implemented FastAPI typed APIs, PostgreSQL persistence, Alembic migration, normalized audit entities, startup interruption recovery, signed HttpOnly visitor sessions, per-session/global quotas, concurrency limits, owner authentication boundaries, same-origin mutation protection, security headers, secret redaction, health/readiness checks, and SSE delivery.

Built three executable controlled faults: string discount arithmetic, payment retry budget regression, and inventory response contract drift. Actual ASGI HTTP requests generate logs, latency/error metrics, and OpenTelemetry SDK span IDs. The modules are honestly documented as service boundaries in one process.

Implemented a typed LangGraph investigation with seven responsibilities, real Groq model discovery, tool selection, separate structured diagnosis/patch/review calls, cited evidence, bounded retries/budgets, reproduction, patch scope/AST validation, real unified diffs, local isolated subprocess tests, and technical reports. Added a restricted GitHub Actions verification workflow and artifact reconciliation integration, CI configuration, container/Compose/Render configuration, developer commands, license, and operational/security/evaluation documentation.

Environment files, local artifacts, databases, and credentials are ignored by Git and Docker. The Groq key is loaded only by backend settings and configured as a secure Render environment variable. Scans of the full Git history and built frontend found no configured credential values.

## Deployment changes

Created Render Free service `srv-dbrmm98u01pc73dvsup0` with the provider-assigned public URL above, one unprivileged container process, database-backed readiness, secure backend environment settings, and Git-backed automatic deployment. Documentation-only changes are excluded from deployment triggers. Durable records live in Neon rather than the host filesystem. No paid plan, disk, worker, or subscription was started.

An optional GitHub App registration completed during the owner's consent flow before installation was declined. Installation was not confirmed; setup was stopped and generated app credentials were removed. The registration was not deleted. The temporary broader GitHub account credential was also removed from Render. The deployed runtime now holds no GitHub credential.

GitHub refused CI jobs before execution because the account was locked due to a billing issue. The owner explicitly chose to leave remote verification unavailable. The interface states that limitation. Public live investigations reach an honest awaiting-verification verdict, with a real failing reproduction and reviewable patch/report. No remote CI success, remote test result, PR, or automatic patch deployment is claimed.

## Executed verification

- 51 backend tests and 17 scenario subtests passed.
- 11 frontend tests, TypeScript production build, Python lint, and static type checks passed.
- 15/15 deterministic engineering evaluation cases passed; these are separate from unmeasured model-quality benchmarks.
- Public desktop/mobile routes and responsive navigation passed checks without page errors or horizontal page overflow. An expanded console audit caught an external font request blocked by CSP; the fonts were moved to same-origin WOFF2 assets with OFL license notices. The final rerun passed all 12 desktop/mobile route checks with no page or console errors, no horizontal page overflow, and working mobile navigation. Results are recorded in [browser-verification.json](browser-verification.json).
- Public health, database readiness, scenario/history/evaluation APIs, patch/report downloads, owner-approval denial (401), cross-origin write denial (403), secure cookie flags, and secret absence were checked.

The browser launched public run `6762c3c1-2890-4250-ae77-cd9b4e0043d5`. The deployed backend recorded 3 actual Groq responses, 5,393 reported tokens, 14 evidence records, 33 events, 11 real SDK spans, reproduction exit code 1, and downloadable patch/report responses (200). Verdict: awaiting_verification, exactly as required by the owner's disabled remote-execution choice. Machine-readable evidence: [verification-evidence.json](verification-evidence.json).

Three completed Groq-generated local repairs are available publicly as clearly labeled recordings, each with original test exit 1, patched exit 0, regression exit 0, and accepted model review:

- [Broken Orders Deployment](https://traceforge-ai-3pb0.onrender.com/runs/7c894bb8-2c49-41d6-96f2-4abd6fdfc067/repair)
- [Inventory Contract Drift](https://traceforge-ai-3pb0.onrender.com/runs/20ba5936-d57d-4bea-b5ad-7d68c72aeddb/repair)
- [Payment Retry Storm](https://traceforge-ai-3pb0.onrender.com/runs/402be054-b8b5-4c4e-b384-b66e12ef6dd1/repair)

Failed, rejected, and interrupted attempts remain in history. Fixture verification is not a guarantee for an arbitrary production application. Free hosting may sleep, and live inference remains quota-limited.
