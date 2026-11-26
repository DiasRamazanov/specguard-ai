# Frontend handoff (Claude Code)

Branch `feat/frontend`. Owner of the frontend, SPEC mascot, Copilot UI and browser tests. No backend files were changed.

## Milestone 1 · 26 November 2026

**Environment:** Windows 10, Node 24.22, Python 3.13 venv (the lock installed cleanly; the README specifies 3.12). The offline backend ran from `specguard.api:app` on 127.0.0.1:8000.

**Delivered (`frontend/`):**
- **Upload flow:** session → multi-file upload → offline/DeepSeek mode with explicit consent → audit → polling of real events → result.
- **Workspace:** overview (verdict, counts, coverage, priority findings, limitations), requirements, findings, contradictions (pair view), report (Markdown from `/report`, download), and a source drawer that highlights cited quotes.
- **SPEC mascot:** all 13 states, docked at the bottom of the sidebar, 70% gaze, nested layers, single click = ack, double click = open/close, Enter/Space, Escape, explicit mobile button, reduced-motion support.
- **SPEC Copilot:**
  - context bar and an evidence-grounded Q&A history with citations;
  - suggested questions and a new-chat button;
  - multiple attachments with name/type/size/status chips, per-file selection, removal (`DELETE`), retry, drag-and-drop, and a purpose for each upload (context / comparison / revision);
  - comparison results and revision drafts that require approval;
  - explicit revalidation, which runs a new revision as a separate audit.
- **Contract types:** generated from `contracts/openapi.json` (`npm run gen:api`).

**Checks (this machine):**
- `npm run build` passed.
- `npm test`: 41/41 Vitest tests passed.
- `npm run e2e`: 12/12 Playwright tests passed (desktop + mobile), against the real offline backend.
- Backend `python -m pytest -q` on Windows: 86 passed, 4 failed. Three are PDF tests (the sandbox requires Linux/macOS, as documented). The fourth is `test_schemas_match_runtime`, which fails because `read_text()` uses the Windows locale encoding (cp1251) instead of UTF-8.

## Contract notes for the lead

No contract was changed. Please decide on each of these:

1. **Attachment completion has no event.** The job reports `attachment_received` and `attachment_reading`, but nothing when extraction finishes. The frontend treats the 201 `Attachment` response with `extraction_status: "extracted"` as completion and then settles SPEC to idle. A stage such as `attachment_ready` would make this explicit.
2. **Offline Copilot emits no events.** `copilot_thinking` and `copilot_response_completed` are emitted only on the live path, so SPEC doesn't react to offline questions. That's correct under "real events only"; just noting it.
3. **Live availability can't be discovered.** `/health` doesn't report whether `SPECGUARD_LIVE` and the key are set, so the UI learns this from a 503 at request time. Optional: `GET /health` → `{status, live_available}`.
4. **Limits aren't in OpenAPI.** The upload limit (5 MB) and the accepted formats (PDF/MD/TXT) are mirrored from `specguard/api.py` and `ingest.py` into `frontend/src/api/client.ts`. Publishing them in the contract would remove that duplication.
5. **No document DELETE.** Removing a file before the audit starts is client-side only; the uploaded document stays in the session until the TTL expires.
6. **Required fields in generated types.** `openapi-typescript` marks `mode` and `allow_external_processing` as required in `CopilotRequest`/`AuditRequest`. The frontend always sends both.
7. **Windows test portability.** `tests/test_api.py` should read `contracts/openapi.json` with `encoding="utf-8"`.

## Not done / next

- Live DeepSeek paths (comparison, revision drafts, criterion scores, live Copilot) are wired to the contract but haven't been exercised, because there's no key here.
- PDF upload could only be tested for its error path on Windows.
- The design was compared visually against references 01/03 by hand; there's no screenshot-diff baseline yet.
