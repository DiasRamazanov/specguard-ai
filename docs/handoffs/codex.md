# SpecGuard engineering handoff

## Shared foundation · 26 November 2026

Local branch `feat/core-engine` in an isolated worktree. Starting commit `71c0ce4`. Claude Code can consume `contracts/openapi.json`, standalone schemas and the explicitly labeled mock fixture. Poll GET /audits/{audit_id} and render only returned events. Every private route takes the session bearer. Upload raw bytes with filename in the query string. The API provides separate fields for a draft revision and stakeholder decisions.

## Development routing

Installed ChatGPT desktop 26.1106.51428, Codex CLI 0.167.0-alpha.4.1 on macOS arm64. Native account/read returned ChatGPT Plus; model/list returned 10 visible models. The live desktop spawn tool offered six: gpt-6.2-astra, gpt-6.2-sol, gpt-6.1-terra, gpt-6.1-sol, gpt-6-astra and gpt-6-sol. The CLI also listed gpt-6-luna, gpt-5.6-sol, gpt-5.6-terra and gpt-5.6-luna. The dated catalog supported every selected effort. Plus plan identification establishes neither unlimited usage nor provider credits. No paid external inference was authorized, and the process environment lacked DEEPSEEK_API_KEY.

The desktop spawn tool in this existing chat exposes explicit model/effort overrides. Assignments below used that interface. Future trusted project sessions can use the six project TOML roles. The account and effective project layer were read through the installed app server. No change to user-wide config or active session model.

| Actual assignment | Model / effort | Result at foundation |
| --- | --- | --- |
| repository_explorer | gpt-6.1-terra / medium | Verified official tree, README, issued specification and event site. Video retrieval unavailable. |
| backend_engineer | gpt-6.2-sol / high | Canonical source and audit models implemented. Parser, pipeline, CLI and reports in progress. |
| ai_integration_engineer | gpt-6.2-astra / high | Provider interface agreed, role contracts and validation in progress. |
| test_engineer | gpt-6.2-sol / medium | Independent synthetic acceptance harness in progress. |
| Lead | Existing desktop session | Initialized Git and isolated worktree, installed dependencies, exported REST contract and schemas. |

Foundation checks: `python -m scripts.export_contracts` succeeded using the project venv. App-server configuration read confirmed the project layer and three-child limit. Role files, contracts and fixtures are local. Per-agent token consumption unavailable. Final results, checks and release gates follow below.
