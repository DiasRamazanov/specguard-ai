# SPEC 4.1 / 4.2 implementation reference

Open `prototype.html` directly in a browser; no installation or network required. The source preserves the SVG geometry, colors and keyframes of SPEC 4.1, adapts the SPEC 4.2 composer to standalone HTML, and adds the three previously specified attachment states. It is a reconstruction from the chat source, not an exported ChatGPT runtime. All audit counts and answers are illustrative. Local file selection is real; no file content is parsed or uploaded. The additional compare state uses head tilts and two document icons; alternating document gaze is a production TODO.

## Files
- prototype.html: self-contained visual and interaction reference
- spec-mascot.svg: inline SVG artwork (use unique clip IDs for multiple instances)
- spec-animations.css: 13 states and activation gestures
- spec-gaze.ts: reusable 70% gaze hook logic with cleanup
- spec-interactions.ts: reusable activation logic
- spec-copilot.html: composer and panel markup
- prototype.css / prototype.js: standalone demonstration styling and behavior
- design-tokens.json: approved palette and typography

## Claude Code instructions
Use this pack alongside the earlier visual reference archive and frontend master prompt. Preserve geometry, golden shell, navy face, 70% gaze, bottom-sidebar docking, independent transforms, red error shake, green completion, double-click activation and right panel. Adapt to React and TypeScript; do not embed the demonstration as the production app. Replace hardcoded data and demo messages with real API results. Implement source citations, actual upload/extraction statuses, multiple attachments, session isolation, file removal, correction drafts and explicit revalidation. Never send cursor data to the backend. Preserve reduced motion, keyboard activation and an explicit mobile control. For real events, make dramatic animations short rather than continuously looping as in the test controls. Add backend event mapping and explicit tests for all states. The prototype uses system font fallback; use approved licensed Cyrillic-supporting fonts in production.

## Verification
Run Playwright against the reference and production interface; compare screenshots and exercise double-click, Escape, keyboard, error shaking, eye movement, upload/removal and reduced motion. Do not claim real inference or uploads based on this prototype.
