# SpecGuard AI — approved frontend references

Use alongside Claude Code master prompt No. 2 and autonomous routing prompt. Reference 01 is the primary approved light visual direction. Reference 02 is the original hackathon mascot reference, not an asset to reproduce directly. Reference 03 illustrates mascot integration, not the final Copilot attachment UI. All visible mockup metrics are illustrative; use actual backend values.

## Visual design
Light lavender/off-white #F7F6FC, white surfaces, violet #7828EE, deep purple #5521CA, soft lavender #EAE3FC, charcoal #111322. Manrope/Inter, JetBrains Mono for IDs, Russian interface. Original yellow-white pixel-art robot, navy face, cyan neutral eyes, document/checkmark antenna instead of copied chart antenna. No dark or green redesign.

## SPEC 4.2
Permanently dock at bottom of workspace sidebar; no autonomous page travel or full-body cursor following. Eye tracking fixed at 70% (bounded SVG displacement roughly 10.5 horizontal and 6.3 vertical units in 160-unit viewBox, smooth interpolation), neutral on pointer leave. Separate nested layers for body animation, expression/blink, gaze and dynamic LED/effects. Keep gold shell permanent. States:
- Idle: yellow, gentle float and blink.
- Greeting: yellow, happy bounce.
- Document received: blue, bounce and document icon.
- Extracting: blue, nod and scan.
- Thinking: violet, head tilt and dots.
- Contradiction: orange, recoil and warning icon.
- Verification: cyan, scan and magnifier.
- Report generation: indigo, nod and document.
- Success: green, celebration and particles.
- Error: red LED and face, pronounced side-to-side head shake (roughly +/-9 degrees), concerned face.
- Attachment received: yellow, nod and document.
- Reading attachment: blue, scan.
- Comparing documents: violet, two documents and alternating gaze.
Real backend events only; dramatic motions briefly play and settle. Single click acknowledgment; double click activation bounce and right-side panel slides open; double click again closes. Escape, visible close, keyboard Enter/Space, explicit mobile opening control. Restore underlying emotional state after gesture. Reduced motion support.

## Copilot panel
Right-side panel with current audit/document/requirement/finding context, history, free-text composer, suggested questions, source citations, new chat and close. Paperclip and drag/drop, multiple files, file chips with name/type/size/status/removal and retry; PDF/MD mandatory for planned attachment functionality, other formats only if supported by backend. Attachment purpose: supplementary context, comparison, or explicit revalidation. Never silently change original audit. Evidence-grounded Q&A, corrections as drafts with approval, stakeholder questions, readiness explanation. No fake production responses or progress. Use actual API contracts and backend events.

The interactive ChatGPT prototypes were not available as standalone image files; this written specification preserves their approved behavior. These are design references, not production assets or working React components.
