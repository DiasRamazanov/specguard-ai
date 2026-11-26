---
name: api-contract-management
description: Change the shared REST interface consumed by Claude Code’s frontend.
---

Edit Pydantic models and route declarations first. Regenerate contracts using python -m scripts.export_contracts and inspect the diff. Verify the returned examples against schemas, the bearer ownership boundary and the session polling flow.
