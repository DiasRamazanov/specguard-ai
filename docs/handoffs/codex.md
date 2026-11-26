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

## Live DeepSeek verification · 26 November 2026

The worktree .env furnished the server credential for bounded calls to the authenticated DeepSeek endpoint. Both configured model IDs were returned. A synthetic Flash extraction passed its schema and source checks. The first Pro probe reported 3,169 reasoning tokens and its unknown requirement reference was rejected. A subsequent live Pro Copilot answer cited the correct “17 дней” passage in the chosen attachment. The API preserved the original audit, denied a foreign session and removed the attachment. This live HTTP test took 11.576 seconds with 1,581 input and 876 output tokens, including 683 reasoning tokens. A separate two-attachment test verified PDF page-one coordinates and Markdown navigation together.

The official source is organizer revision `928c1aa364265426105b69ba7a3444eac11b22db` with SHA-256 `e7dae55e5453a250d93e335f5ff9c7f775f4457ccddd333f4a67e47b20d74381`. The initial audit `544ded8c5c294ad9b38342755c71832c` covered 124/124 source blocks, 46/54 individual assessments and a completed global pass. Incomplete critic batches and the spending ceiling prevented a readiness determination. All 125 stored evidence records were independently verified against the original. This is an intermediate result.

| Assignment | Actual model / effort | Result |
| --- | --- | --- |
| Evaluation test engineer | gpt-6.2-sol / medium | Froze nine independent source checks and two false-positive controls before seeing the report. |
| Semantic scoring test engineer | gpt-6.2-sol / medium | Matched four of nine source checks in the initial report. Two of those four met every localization anchor. Neither control triggered. |
| AI integration engineer | gpt-6.2-astra / high | Implemented opt-in call-local evidence references for individual, critic and risk stages. Returned handles are resolved against the input and verified against the public output contract. |
| Lead | Existing Codex session | Integrated the CLI flag, bounded reasoning effort, conservative durable budget, saved validated role results, ran the actual pipeline and checked source coordinates. |

Commit `4f1c875` added reasoning effort and timeout controls and full-document global context when serialized input fits. Commit `623ec25` exposed `validate --reference-roles` for review recovery. The local suite passed 110 tests. Ruff, pip dependency and contract regeneration checks passed. The two-case live benchmark found one labeled defect and triggered none of three designated negative controls. Both labeled requirement IDs were extracted and individually assessed; one of the two audits completed all semantic stages. Time was 143.360 seconds with 14,674 input and 11,153 output tokens, including 7,593 reasoning tokens. The small development fixture sample cannot estimate general production accuracy.

The initial aggregate ledger reached 476,902 tokens, including conservative charges for a timeout and an interrupted request whose provider token counts were unavailable. The user authorized economical recovery using the available balance. The lead retained a cumulative ceiling of 790,000 tokens, below the proposed 850,000. No new credits were purchased. The release reports and the organizer input are stored outside Git. Final measurements follow once the recovery completes.

## Completed official run and frontend PR review

Audit `fd9bf1615ce04dc09e5f889bd2613f4b` assessed 54/54 requirements and reviewed 124/124 blocks. Global and critic passes completed. The production renderer generated the six-section Russian report with verdict `requires_revision`. It contains 12 confirmed findings (2 critical, 5 major, 5 minor), 45 requests for clarification and one context-dependent finding. The independent source checker validated 167 quotations and nine scoped absence records. The Markdown matched a fresh render byte for byte. Its SHA-256 is `3fa9cef9aef328bc6a6277b280e13c7c8ef1c3185c2a4ea173d02a9e70f93d97`. Separate organizer source, report, structured audit, verification and usage files are in Downloads/SpecGuard AI Review and Release/official on the owner's Mac. External submission is pending.

The lead recovered four assessments with individual calls restricted to their source blocks and verified the combined output against the original parent payload. Prior results retained their order for the global and critic stages, allowing identical verified requests to reuse checkpoints. A backend-engineer dispatch (gpt-6.2-sol/high) hit the Codex usage limit before delivery. The lead used a release-local ordering wrapper and the production service. No new public resume option was shipped. The final recovery took 415 seconds. Across official attempts the provider recorded 288,860 input and 336,317 output tokens, including 205,578 reasoning tokens, over 3,970.853 seconds of recorded requests. Across all live tests and runs, known usage was 660,550 tokens, including reasoning. Two unmetered requests account for the remaining 65,401 conservatively reserved tokens. Ledger total 725,951 of 790,000, final balance USD 0.96. No top-up. The backend regression suite passed 110 tests, Ruff passed and contract export left no diff.

On a strict lead review of the frozen nine-item rubric, the final findings explicitly identified the repeat push, mutating GET, invalid-amount 200/400 conflict, missing production route and 403/404 mismatch (5/9). Two more findings discussed the month boundary and read/save ambiguity without identifying the full cross-document conflict or missing read contract. The unclear error envelope and 201 selection rule were missed. This is a non-exhaustive single-document evaluation. The earlier 4/9 score was for the original partial report.

The lead reviewed private PR #2 at eec96f7c6aa1292bd779fcaaa7d9ef7585073cee in a detached checkout. GitHub reported a clean merge into main. Eleven frontend files, no dependency or API changes. PR backend pytest 90 passed, frontend Vitest 41 passed, TypeScript and production build passed. All 12 Playwright tests passed against both the PR backend and feat/core-engine. A browser PDF upload produced a 2,967-byte Markdown download identical to the server report. Gitleaks scanned eight reachable commits with zero findings. The PR checkout has a pre-existing Ruff I001 and no frontend lint script. Verdict approved with minor issues. An inline comment documents an ID-prefix truncation in shared.ts:26. PR remains open for the owner's decision. Review and four screenshots are in Downloads/SpecGuard AI Review and Release/pr2.
