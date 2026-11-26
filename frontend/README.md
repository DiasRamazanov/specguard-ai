# SpecGuard AI — frontend

React 19 + TypeScript + Vite. Russian UI in the approved light direction (`references/frontend/01`), with the SPEC mascot (SPEC 4.1/4.2) and the SPEC Copilot panel.

## Run

The backend must be on `127.0.0.1:8000` (see the root README). The dev server proxies `/api/*` to it on the same origin.

```bash
cd frontend
npm ci
npm run dev          # http://127.0.0.1:5173
```

Set `SPECGUARD_API` to point the proxy at another backend origin.

## Checks

```bash
npm run typecheck
npm test             # Vitest unit/component tests
npx playwright install chromium   # once
npm run e2e          # Playwright: starts the offline backend + Vite if they are not running
npm run build
```

For e2e, `SPECGUARD_PYTHON` overrides the backend interpreter (default, relative to the repo root: `.venv/bin/python`, or `.venv\Scripts\python.exe` on Windows).

## Contract

`src/api/schema.d.ts` is generated from `contracts/openapi.json` with `npm run gen:api`. Don't edit it by hand. `src/api/types.ts` only aliases the generated types. After Codex changes a contract, regenerate it and run `npm run typecheck`.

## Offline vs DeepSeek

- The default mode is **offline**: deterministic local checks, no model. Every result screen shows an «Офлайн · без модели» badge and a notice that coverage is incomplete.
- **DeepSeek** is used only when the user picks it and ticks explicit consent. If the server isn't configured, the real 503 message is shown.
- Copilot comparison and revision drafts are live-only on the backend. In offline mode the panel explains this instead of sending a request.
- `contracts/fixtures/mock-audit.json` is used **only in unit tests**. It is never rendered as product data.

## SPEC mascot

| Source | Implementation |
| --- | --- |
| `spec-mascot.svg` geometry | `src/mascot/SpecMascot.tsx` (same paths; gold shell permanent; unique clip IDs) |
| `spec-animations.css` | `src/mascot/mascot.css` (13 states + gestures; finite dramatic motions that settle) |
| `spec-gaze.ts` (70%) | `src/mascot/gaze.ts` (bounded to 10.5 × 6.3 units; pointer data never leaves the browser) |
| `spec-interactions.ts` | `src/mascot/SpecDock.tsx` (single click = ack, double click = open/close, Enter/Space, Escape, mobile button) |

The layers are nested and independent: `.spec-gesture` → `.spec-body` → LED/`.spec-fx` effects, `.gaze` → `.gaze-auto` → `.blink` (expression).

Only real backend `Event.stage` values drive the state (`STAGE_TO_STATE` in `src/mascot/states.ts`). Events are replayed in order, each shown for at least 650 ms. API errors switch SPEC to the red error state.

Reduced motion (the OS setting or the «Анимация SPEC» toggle) stops all motion and gaze but keeps the state colours and faces.
