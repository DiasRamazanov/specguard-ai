---
name: secure-document-processing
description: Work on SpecGuard PDF parsing, upload limits and document isolation.
---

Treat filenames as metadata. Bound both uploaded bytes and extracted content, report unreadable pages, and keep raw text out of error logs. Test cross-session reads and deletes through the same API the frontend uses. Use synthetic documents.
