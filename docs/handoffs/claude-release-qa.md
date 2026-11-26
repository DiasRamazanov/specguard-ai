# Final frontend and QA handoff from Claude Code · 26 November 2026

Written while Codex was unavailable (its allowance resets 27 Nov, 01:42 Astana). Claude Code has **stopped active development** and is available for integration corrections only.

Throughout: no backend, contract or deployment files were modified. No branch was merged into `main` by Claude after PR #2. No paid inference was run, no API key was requested or used, and nothing was deployed.

---

## 1. Branches and latest commits (all pushed, verified against `origin` on 26.11.2026)

| Branch | Latest commit | Owner | State |
| --- | --- | --- | --- |
| `main` | `5607c10` | lead | Frontend PR #1 and PR #2 merged. **Does not include the 7 newest `feat/core-engine` commits.** |
| `feat/core-engine` | `afe3831` | Codex | Backend with the official-run fixes; CI "Offline verification" green |
| `feat/frontend` | `4338640` | Claude | Merged via PR #1; no further work |
| `polish` | `3aed951` | Claude | Merged via PR #2; no further work |
| `frontend-enhance` | `6705609` | Claude (forked session) | **Pushed, no PR, not reviewed by Codex.** Accessibility, navigation and responsive improvements; frontend only. |
| `feat/presentation-release-qa` | this commit | Claude | QA report, presentation, jury materials, this handoff |

**Local-only state (deliberately not pushed):** branch `qa/integration-local` (`465a4d3`), a test merge of `origin/main` + `origin/feat/core-engine` used for QA. It contains no unique work: Codex should do the real integration through a PR. Everything else is on GitHub. Untracked slide previews in local checkouts are regenerable and git-ignored.

## 2. Completed tasks
1. **Frontend** (React 19 + TypeScript + Vite; merged via PR #1 and #2):
   - upload, audit progress driven by backend events, overview, requirements, findings, contradictions, report and source evidence;
   - SPEC mascot: 13 states, 70% gaze, sidebar dock, double-click activation, reduced-motion support;
   - SPEC Copilot: grounded Q&A, multiple attachments, comparison, approval-only drafts, explicit revalidation.
2. **Visual polish** against approved references 01/03 (PR #2), plus your review fix: requirement-ID prefix stripping, with regression tests.
3. **Frontend enhancements** on `frontend-enhance`: dialog focus handling, confirm dialog, navigation and responsive layout, plus 4 new unit and 7 new browser tests.
4. **Independent release QA** of the integrated code: [qa-report.md](../release/qa-report.md).
5. **Presentation and jury materials** (Russian), listed in section 7.

## 3. Actual test results

| Code tested | Checks | Result |
| --- | --- | --- |
| Integration (`main` + `feat/core-engine`, local `465a4d3`) | Fresh install (venv from the lockfile, `npm ci`), `pip check` | ✅ |
| | Backend pytest | **106/110**: 4 OS-dependent failures (3 PDF sandbox tests need Linux/macOS; 1 locale-encoding test passes with `PYTHONUTF8=1`) |
| | Ruff | ✅ |
| | Contract regeneration | ✅ no real diff (Python 3.13 renames the 413/422 reason phrases only) |
| | CLI reproducibility (2 offline runs) | ✅ identical apart from run ID and time |
| | TypeScript / Vitest / build | ✅ / **54/54** / ✅ (dev harness absent from `dist`) |
| | Playwright, desktop + mobile, cold start | ✅ **32/32** |
| | Security and isolation probes ([script](../release/qa/security_probe.py)) | ✅ **20/20** |
| `frontend-enhance` (`6705609`, against the `main` backend) | TypeScript / Vitest / build | ✅ / **58/58** / ✅ |
| | Playwright, desktop + mobile | ✅ **39/39** |

Environment: Windows 10, Python 3.13.11 (3.12 was unavailable), Node 24.22, Chromium. No Linux, WSL distribution or Docker.

## 4. Verified vs. unverified

**Verified independently (Windows, offline):**
- Markdown processing.
- Report generation, retrieval and download.
- Requirement and finding navigation; source evidence with highlighted quotes.
- All 13 SPEC states, with motion measured: error shake within ±9°, success bounce, thinking tilt, compare gaze.
- 70% gaze bound.
- Double-click, keyboard and Escape activation.
- Multiple attachments, including removal.
- Mobile layout.
- Session isolation, auth, input limits, the paid-inference gate (off by default) and offline injection resistance.
- CLI reproducibility.
- API contract compatibility (frontend types are generated from `contracts/openapi.json`).

**Not verified by Claude:**
- PDF parsing: it fails closed on Windows; Codex reports a passing macOS browser upload.
- Every live DeepSeek path: audit, Copilot, revision drafts, comparison.
- Any hosted deployment, health checks in hosting, production startup: no configuration exists on the remote.
- The official report's contents: they are outside Git, and the figures come from your handoff.
- Python 3.12.
- `frontend-enhance` against the integrated `feat/core-engine` backend: it was tested against `main` only.

## 5. Unresolved issues

| # | Severity | Issue |
| --- | --- | --- |
| R1 | **Critical** | Release integration, Cloud runtime, Dockerfile and Railway work are **not on the remote**. Only the branches in section 1 exist. |
| R2 | **Critical** | `main` lacks the backend that produced the official report (`feat/core-engine` is 7 commits ahead; it merges cleanly). |
| R3 | **Critical** | The repository is private, but the organizer requires that someone else can run it from the link. Rights to `references/` images are unconfirmed. |
| R4 | Major | Enabling live mode publicly would let anonymous users spend up to 1M tokens per run / 6M global (defaults). |
| R5 | Major | 24-session anonymous cap with no per-client limit, so a public demo is easy to lock out. |
| R6 | Major | No same-origin serving: the backend serves no static files and sets no CORS. A deployment needs a proxy. |
| R7 | Minor | `test_schemas_match_runtime` reads JSON with the locale codec. |
| R8 | Minor | Contract export differs under Python 3.13. |
| R9 | Minor | No CI on `main` or on PRs; frontend checks run only locally. |
| R10 | Major (process) | `frontend-enhance` has no PR and no independent review. |

## 6. Deployment observations
- Live mode is gated twice: user consent, and `SPECGUARD_LIVE=1` on the server. The default `.env.example` has `SPECGUARD_LIVE=0`. Verified: without server enablement the API returns 503; without consent, 400.
- Health check: `GET /health` → `{"status":"ok"}`.
- State is in memory with a 1-hour TTL, so run **one worker** only (documented). A restart clears all sessions.
- Public hosting needs the same-origin proxy (`frontend/dist` + `/api`), rate limiting or authentication, and `SPECGUARD_LIVE=0` unless access is controlled.
- The PDF sandbox needs Linux or macOS; a Windows host rejects PDFs.

## 7. Presentation, speaker notes, demo and submission materials (all on `feat/presentation-release-qa`)

| File | Content |
| --- | --- |
| `docs/release/presentation/specguard-presentation.pdf` | **10 static slides, no animations, 1.25 MB** |
| `docs/release/presentation/specguard-presentation.html` | Same deck, self-contained (fonts in `fonts/`, images in `img/`) |
| `docs/release/presentation/speaker-notes.md` | Notes and timing per slide (about 5 min), with figure sources |
| `docs/release/demo-guide.md` | 12-step jury demo, an honestly labelled fallback with the saved official run, troubleshooting |
| `docs/release/technical-defense.md` | Evidence-based answers on all 13 requested topics |
| `docs/release/submission-checklist.md` | Organizer README + event-site requirements mapped to evidence and gaps |
| `docs/release/qa-report.md` | Detailed QA results and findings |
| `docs/release/screenshots/` | Real application screenshots (offline, synthetic document) |
| `frontend/scripts/capture-screenshots.mjs`, `export-presentation.mjs` | Regenerate the screenshots and the PDF |

Figures used (all from your handoff; nothing extrapolated):
- 54/54 requirements, 124/124 blocks;
- 12 confirmed findings (2/5/5);
- 176 = 167 quotes + 9 absences;
- 45 clarification requests;
- 5/9 strict semantic score;
- 288,860 input / 336,317 output tokens.

**Submission facts** (event site, rechecked): deadline 27 Nov 23:59 with no timezone stated; submit «демонстрацию работы агента и репозиторий» online, but no channel is named. Judging: Уточнение, Архитектура, Ценность, Презентация и защита, 25% each. Finals on 4 December.

## 8. Exact actions for Codex on resume (in order)

1. `git fetch --prune origin` and read this file, then [qa-report.md](../release/qa-report.md).
2. **R1:** if local release, Cloud runtime, Demo release or deployment work still exists on the Mac, push it to a branch now. If it is lost, record that in `docs/handoffs/codex.md`.
3. **R2:** open a PR `feat/core-engine` → `main` (it merges cleanly), run the suites, merge, and tag the commit shown as «Версия агента» in the official report.
4. **R10:** review `frontend-enhance` (`6705609`; 11 frontend files, no API or dependency changes). Run its checks against the merged backend from step 3, then PR it into `main` or reject it. On `main` it passed TypeScript, 58/58 Vitest, the build and 39/39 Playwright.
5. **R7/R8:** add `encoding="utf-8"` in `tests/test_api.py::test_schemas_match_runtime`; pin Python 3.12 for contract export.
6. **R3:** with the owner, before the deadline: run a final secret scan, decide on the `references/` images, then make the repository public or grant jury access.
7. **Submission bundle:** place the official report (audit `fd9bf1615ce04dc09e5f889bd2613f4b`, SHA-256 `3fa9cef9…f93d97`) and the issued input (SHA-256 `e7dae55e…d74381`) next to the repository link. Both are currently only on the owner's Mac. Confirm the submission channel and deadline timezone with the organizers.
8. **Deployment (only with owner approval):** follow section 6, keep `SPECGUARD_LIVE=0` on any public URL, add a same-origin proxy and rate limiting. Do not build a deployment that competes with any recovered R1 work.
9. If any figure changes after a new evaluation, update slide 8, the speaker notes and the technical-defense answers, and keep the old figures labelled.

Claude Code is available for integration corrections, for example frontend fixes after merging `feat/core-engine` or adjustments from the `frontend-enhance` review.
