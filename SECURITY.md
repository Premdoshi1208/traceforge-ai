# Security and execution boundaries

Provider credentials are backend-only Pydantic SecretStr settings. `.env`, `.env.*`, runtime databases, local artifacts, and private tooling backups are excluded from Git and Docker. Production values are configured in hosting environment settings. Response/audit redaction removes configured secrets and token patterns. Never prefix credentials with VITE_ or send them to the browser.

Public visitors may launch only three curated scenarios and inspect stored runs. Unknown fields, arbitrary paths, arbitrary commands, and arbitrary repositories are rejected. Cross-origin and cross-site mutations are rejected. Responses set CSP, frame denial, nosniff, and production HSTS. Live runs have an IP-derived private actor identity, per-actor/day admission, global daily limits, and single-run concurrency. IP grouping is a demo constraint: shared networks can share a quota. Configure trusted reverse-proxy handling at the host boundary.

Generated source cannot modify tests, CI, secrets, or arbitrary files. AST validation is a restrictive fixture policy, not a claim of general-purpose Python sandboxing. Candidate execution is prohibited inside the production server. Subprocesses have fixed argv, stripped environment, temporary working copies, resource limits, and deadlines. GitHub workflow inputs are never interpolated into shell commands.

Owner actions require a high-entropy X-Admin-Token and verified execution evidence. Anonymous callers cannot approve patches. Owner approval never deploys code. External side effects use run/branch identities and reconciliation before replay.

Use a dedicated repository-scoped GitHub credential with Actions read/write and Contents read for verification. PR creation, if enabled, additionally needs Contents and Pull requests write. Keep credentials in secure host settings. No GitHub credential is retained in the deployed runtime while remote verification is disabled. The temporary broader CLI credential was removed from host settings; repository-scoped App consent was not completed. Workflow test jobs receive no application secrets.

Free model access is quota-limited. No fabricated fallback is used when inference or verification is unavailable. Rotate any key pasted into chat or another exposed channel. Security findings should be reported privately to the repository owner.
