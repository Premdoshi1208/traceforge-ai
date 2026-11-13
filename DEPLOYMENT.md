# Free deployment

Deploy one Docker web service on Render Free and durable PostgreSQL on Neon Free. `render.yaml` declares the free plan. The Docker build compiles React, installs the locked Python environment, and runs one unprivileged Uvicorn worker on PORT. Startup runs Alembic first. Health checks use `/readyz` and execute a database query.

## Secure runtime configuration

- APP_ENV=production
- GROQ_API_KEY: server secret
- DATABASE_URL: pooled Neon PostgreSQL URL with TLS
- MIGRATION_DATABASE_URL: direct Neon URL with TLS
- SESSION_SECRET and ADMIN_TOKEN: independent high-entropy secrets
- VERIFICATION_MODE=unavailable (owner-selected current deployment; use github only after scoped access and runner availability are verified)
- GITHUB_REPOSITORY: fixed curated repository
- GITHUB_TOKEN: server secret permitted to dispatch/read the verification workflow
- DAILY_RUN_LIMIT=12, SESSION_RUN_LIMIT=2, MAX_CONCURRENT_RUNS=1

Do not commit any real environment file. `scripts/deploy_render.py` reads the private production environment and authenticated Render CLI configuration, submits settings over HTTPS, and prints only resource identities/status. It refuses non-free service plans and does not subscribe to paid services.

Neon organization plan was checked as Free before a dedicated traceforge-ai project was created, with fixed 0.25 CU compute. The existing firstsignal-staging project was preserved. Project linking used --no-env-pull to preserve local .env. Pooled/direct connection values were captured privately in ignored .env.production.

Render's free web service may sleep after inactivity and its filesystem is ephemeral. All durable runs and evidence live in Neon. No expiring Render Postgres, paid workers, or disks are used. Provider free allowances can change; verify account and plan before re-provisioning.

## Verification

Check public landing, `/healthz`, `/readyz`, config, scenarios, history, evaluations, and a full live incident through public HTTPS. Inspect the actual GitHub job and artifacts, before/after/regression test output, evidence references, review, report downloads, mobile layout, and browser console. A 200 landing response alone is insufficient.

## Current verification limitation

GitHub rejected jobs before execution because account Premdoshi1208 was locked due to a billing issue. The owner selected leaving live remote verification unavailable. The deployed runtime retains no GitHub credential. Three actual Groq-generated repairs have recorded local subprocess before/after/regression results and accepted model reviews; these are explicitly labeled local recordings. Public live runs collect failures, infer diagnoses, reproduce trusted fixtures, generate constrained patches, and produce reports with an awaiting-verification verdict. They never receive a VERIFIED badge without test proof.

A GitHub App registration completed during the optional consent flow, but installation was not confirmed before the owner declined remote verification. Setup was stopped and all generated app credentials were removed from the deployment environment. No remote pull request was created.
