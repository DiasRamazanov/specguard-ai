# Engineering decisions

- Use one canonical Pydantic audit result for CLI output, report generation, REST responses and exported schemas. Stable source blocks carry page or line coordinates.
- Isolate document parsing, deterministic rules, semantic inference, citation checks and readiness. A live audit requires explicit consent. Local-only analysis carries an incomplete verdict.
- Bound the local demo service by session, time, bytes and concurrent work. Frontend integration uses a bearer session, raw document uploads and polling. Use one worker for in-memory state.
- Keep the native Codex development roles separate from DeepSeek runtime prompts. Only the development lead delegates. The user authorized automatic routing within the existing Codex account.
- Preserve the organizer input and final submission report outside Git. Hold live verification and external release until authorized.
