# Handoff from Claude Code: release QA and presentation · 26 November 2026

Branch `feat/presentation-release-qa`, based on `origin/main` at `5607c10`. Documentation and tooling only: no backend, contract or product code was changed, and no Codex-owned branch was modified, merged or pushed. No paid inference was run.

## Read first
- [Independent QA report](../release/qa-report.md): results, review findings R1–R9, and what was not verified.
- [Submission checklist](../release/submission-checklist.md): organizer and event-site requirements, mapped to evidence.

## Instructions for Codex on resume

1. **Push the release work (R1).** If the release integration, Cloud runtime, Demo release, Dockerfile, Railway config or deployment notes still exist locally, push them to a branch. Nothing beyond `main`, `feat/core-engine`, `feat/frontend` and `polish` is on the remote. If the work is lost, record that in `docs/handoffs/codex.md`.
2. **Integrate the backend into main (R2).** `origin/main` + `origin/feat/core-engine` merges cleanly; a local check was done at `465a4d3`, not pushed. On that integration, 32/32 Playwright, 54/54 Vitest, the build and Ruff pass; pytest is 106/110 on Windows, with only the OS-dependent failures. Merge through a PR and tag the commit recorded as «Версия агента» in the official report.
3. **Deployment (R4–R6), if you deploy.**
   - Keep `SPECGUARD_LIVE=0` on any public URL; anonymous sessions plus consent could otherwise spend up to the default 1M/6M token ceilings.
   - Add per-client rate limiting or authentication: the 24-session cap is easy to exhaust.
   - Serve `frontend/dist` and proxy `/api` from one origin; the backend has no CORS and serves no static files.
   - Use `GET /health` as the health check.
   - Hosting needs owner approval.
4. **Small backend fixes (R7, R8).**
   - `tests/test_api.py::test_schemas_match_runtime`: add `encoding="utf-8"` to the read.
   - Contract export differs under Python 3.13 (413/422 reason phrases): pin 3.12, or normalise the phrases.
5. **Visibility (R3).** Before the 27 Nov 23:59 deadline, the owner must decide between making the repository public and granting jury access. Re-run the secret scan first, and confirm rights to `references/` or exclude it.
6. **Presentation figures.** The deck uses only the figures in your handoff: 54/54, 124/124, 12 (2/5/5), 176 = 167 + 9, 5/9, 45 clarifications, and the token totals. If you produce a new evaluation, update slide 8 and the speaker notes, and keep the old numbers labelled.

## Deliverables on this branch
| Path | Content |
| --- | --- |
| `docs/release/presentation/specguard-presentation.html` | 10-slide static Russian deck, no animations (self-contained; OFL fonts in `fonts/`, compressed screenshots in `img/`) |
| `docs/release/presentation/specguard-presentation.pdf` | PDF export |
| `docs/release/presentation/previews/` | PNG of each slide (git-ignored; regenerate with `node frontend/scripts/export-presentation.mjs`) |
| `docs/release/presentation/speaker-notes.md` | Notes and timing for each slide, with figure sources |
| `docs/release/demo-guide.md` | Jury demo script, honest fallback with the recorded official audit, troubleshooting |
| `docs/release/technical-defense.md` | Evidence-based answers to likely jury questions |
| `docs/release/submission-checklist.md` | Compliance checklist and blockers |
| `docs/release/qa-report.md` | Independent QA results and findings |
| `docs/release/qa/security_probe.py` | Reproducible black-box security and isolation probes (offline) |
| `docs/release/screenshots/` | Real application screenshots (offline mode, synthetic document) |
| `frontend/scripts/capture-screenshots.mjs`, `frontend/scripts/export-presentation.mjs` | Regenerate the screenshots and the deck exports |
