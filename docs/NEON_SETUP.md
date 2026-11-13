# Neon tooling setup changes

Requested source: https://neon.com/.well-known/agent-skills/neon/SKILL.md . Fetched the official skill and followed its manual setup path to preserve existing project configuration.

Initial inspection found no Neon skills or project MCP configuration. Existing global Codex MCP entries were node_repl and computer-use; neither was changed.

Changes:
- Installed project skills neon and neon-postgres under .agents/skills/ with their official reference files.
- Created skills-lock.json recording the official GitHub source and installed content hashes.
- Added only mcp_servers.Neon to ~/.codex/config.toml, using the HTTPS MCP endpoint and OAuth, without an API key in source.
- Verified the entire previous global configuration was semantically preserved. A private ignored pre-change backup is in .local/.
- Removed a redundant project MCP entry created during setup after confirming Codex's global server registration.
- Completed Neon MCP OAuth login and verified the server is enabled through the Codex CLI. The running conversation may need a new session to discover newly registered MCP tools; the authenticated Neon CLI is already usable.
- Reused the authenticated Neon CLI account; no unrelated Neon project or global skill was replaced.
- For the already authorized TraceForge deployment, created a separate Free-plan traceforge-ai database project, linked .neon with --no-env-pull, and added .neon to .gitignore. Local .env remained unchanged; private deployment values are in ignored .env.production.

The Neon CLI freshness checker reported freshly installed skills as outdated, while its updater reported all skills current. Skills were re-fetched from the official repository; do not interpret this inconsistent CLI status as proof of an outdated install. No skill hashes were falsified to suppress the warning.
