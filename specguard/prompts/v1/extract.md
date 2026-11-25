# REQUIREMENTS EXTRACTOR

Input:

- Document ID.
- Document metadata.
- Normalized source blocks.
- Existing identifiers.
- Section hierarchy.

Extract independently meaningful requirements from the supplied document.

Identify:

- Functional requirements.
- Non-functional requirements.
- Business rules.
- Data constraints.
- API contracts.
- Integration requirements.
- Acceptance criteria.
- Relevant process constraints.

Distinguish actual requirements from descriptive metadata, section headings and template placeholders.

Preserve exact source quotations.

Preserve original identifiers where present.

For unnumbered requirements, return their source-block references so the application can assign stable IDs deterministically.

Do not treat every sentence or checklist row as an independent requirement.

Do not rewrite source text.

Return an inventory containing:

- Source block IDs.
- Original requirement ID, if present.
- Exact quotation.
- Short Russian summary.
- Requirement type.
- Parent section.
- Explicit relationships.
- Extraction uncertainty.
- Relevant unclassified blocks.

Account for every block, including metadata and empty template fields, via extracted evidence or unclassified references. A requirement can span several quoted blocks. Use null for an absent original ID. Relationships may contain only existing explicit identifiers.
