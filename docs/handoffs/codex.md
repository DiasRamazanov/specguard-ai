# SpecGuard engineering handoff

## Current cross-computer handoff

Clone the private GitHub repository on the teammate’s computer and select `feat/frontend`. The current contract and mock responses are in `contracts/`, backend startup instructions are in `README.md`, and the approved frontend and SPEC source references are in `references/`. Use [the collaboration guide](../collaboration.md) for invitation, clone and synchronization commands. Local Mac worktree paths in the earlier milestone notes describe the original setup.

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

## Initial local frontend start point (historical)

The shared local repository is `/Users/diasramazanov/Downloads/MNU HACK`. Its primary checkout is `main`. Core development uses `.worktrees/core-engine` on `feat/core-engine`. There is no configured Git remote. Claude Code on this Mac can open the frontend worktree; a separate machine needs an explicitly shared copy or team-owned remote. The organizer repository is a source of requirements.

The shared foundation commit is `b8bc02d28b73672f6919a1d94a0463f09f46bf96`. The provider commit is `93d1cbf51ecd00ecb64159db5dc7351783f8580b`. The integration commit that contains this section adds the runnable backend, refreshed OpenAPI and schemas, and both mock fixtures. Read `docs/architecture.md` and `contracts/openapi.json`. Source design PNGs are untracked at the shared repository root and can be read there from either worktree. Create UI files on the frontend branch only.

```bash
cd '/Users/diasramazanov/Downloads/MNU HACK'
git worktree add -b feat/frontend .worktrees/frontend main
cd .worktrees/frontend
git status --short --branch
```

The creation command is one-time. For an existing frontend checkout, use only the second cd from the repository root.

## Integration and review

| Actual assignment | Model / effort | Result |
| --- | --- | --- |
| AI integration engineer | gpt-6.2-astra / high | Committed nine versioned prompts, paired schemas, bounded transport, durable quota ledger and offline tests. 55 provider tests passed. |
| Backend engineer | gpt-6.2-sol / high | Implemented Markdown/PDF ingestion, individual/global/critic orchestration, deterministic checks, reporting and CLI. Session reached its usage limit before final review. |
| Test engineer | gpt-6.2-sol / medium | Built a 12-case synthetic benchmark and CLI/PDF regression suite. Submitted measurements before the account limit interrupted its final turn. |
| Security reviewer | gpt-6.2-astra / high | Reviewed source, ran 55 tests and pip check. Raised parser allocation, strict consent, primary comparison sources and deterministic finding suppression for lead review. |
| Principal architect | gpt-6.2-astra / xhigh | Dispatch accepted; account usage limit prevented execution. No architectural review or conclusions can be attributed to this agent. Lead retained the review. |
| Lead | Existing session | Integrated session-owned API, scoped Copilot, comparison and approval-only revision drafts. Added isolated PDF parsing, strict consent and primary-document comparison citations. Verified the six role descriptions in native Codex prompt metadata. All eight project skills passed quick_validate. |

At frontend handoff, `python -m pytest -q` passed 90 tests with six dependency deprecation warnings. `python -m scripts.export_contracts` completed; the suite matches the generated OpenAPI to the live routes. No external model calls or purchases occurred. Per-worker Codex token totals are unavailable. The account reported a usage ceiling during the architect dispatch. The lead continued offline integration without switching the active model.

DeepSeek account model access, live semantic benchmark, the final official report and frontend integration remain release gates. The backend serves real offline audits now. Scope the demo to trusted local users. Session creation is anonymous, with bounded ephemeral state. Cross-origin UI development should use a same-origin dev proxy. OCR, final approval/application of revisions, mascot animation and automatic revalidation are outside the shipped backend functionality.

## Verified local handoff and backend follow-up

The shared integration commit is `0d62d1f5b72e88e8bc4c2fbd1e1135b82a8ed019`. The lead created `/Users/diasramazanov/Downloads/MNU HACK/.worktrees/frontend` on `feat/frontend` and verified that its working tree was clean. Open Claude Code in that directory. The original main checkout remains available at the absolute path above. A GitHub remote has not been set.

The lead completed the interrupted backend review. Follow-up changes preserve deterministic findings when the critic supplies an unsupported rejection, validate overlap before accepting duplicate verdicts, include prior individual candidates during global review and invoke the risk role on verified findings. Checkout-based reports record the Git revision. These changes preserve the frontend wire contract.

Final local checks on the backend branch: 91 tests passed with six dependency deprecation warnings, Ruff passed, regenerated contracts produced no diff and pip check found no dependency conflicts. A fresh Python 3.12 venv installed the lockfile and built the foundation package. Its installed CLI processed the organizer Markdown from outside the repository. The offline diagnostic contained 124 source blocks, 20 extracted requirements and five findings, with incomplete coverage and undetermined readiness. The wheel included all nine prompts and their schemas. An offline CI workflow is committed; no hosted run or external submission was performed.

Offline development benchmark, 12 synthetic cases × 3 runs: precision 5/5, recall 5/6, F1 10/11, false-positive rate 0/18. All 17 expected requirement instances were extracted; all eight finding quotations and the one scoped absence resolved. Five detected positives matched the expected source locations. The cross-document bounds case was flagged for clarification and counts as a miss against its confirmed label. Repeatability was 24/24 comparisons. Validator timing for 36 executions was 17.086 ms total in this run. These fixtures were used during development. Independent held-out semantic accuracy and provider token breakdowns are unmeasured. No live requests were made.

The core branch is ready for a bounded, separately authorized live evaluation when credentials are available. The next reasoning assignment for independent architecture review is principal_architect (gpt-6.2-astra, xhigh) after included usage becomes available. The local frontend worktree can proceed independently.

## Private GitHub synchronization and live preflight

The lead created the private DiasRamazanov/specguard-ai repository, configured origin and pushed main, feat/core-engine and feat/frontend in one atomic ordinary push. Main and the initial remote frontend tip are `2275807ad0d37ac6c1a48668d5ff69eb06b52a8a`. The coordination changes were merged into the backend branch. All earlier commits are reachable.

Gitleaks 8.30.1 scanned reachable patch history and the extracted reference pack before publication. A separate check examined all 120 distinct reachable blobs at the initial push, including binaries, for credential signatures and inspected every tree for sensitive filenames or worktree and environment directories. Neither check found a credential. The only tracked dotenv file is the empty-key example. The design references are approved for internal team use; their archives included no separate redistribution license.

An independent single-branch HTTPS clone from GitHub installed the lockfile in an empty Python 3.12 environment, passed 90 offline tests, regenerated unchanged API contracts and generated a Russian CLI smoke report. Send the teammate the clone instructions in docs/collaboration.md. The owner still needs to invite their GitHub account.

The lead added a catalog-only `python -m specguard check-provider` command and an early check of both configured models in the official CLI path. This prevents spending tokens on extraction before discovering the reasoning model is unavailable. The backend suite passed 93 offline tests and Ruff passed. Running the live preflight here returned `missing_api_key` before any network request. The official Russian submission report is pending access to an authorized server-side DeepSeek key. No provider tokens were consumed during this synchronization. Codex token accounting was unavailable.
