# MULTI-DOCUMENT COMPARISON

Input:

- Primary document.
- Supplementary documents.
- Document-specific requirement registries.
- Source references.
- User-selected comparison purpose.

Determine whether the documents are complementary specifications, conflicting specifications or different versions.

Identify:

- Newly introduced requirements.
- Removed requirements.
- Changed requirements.
- Cross-document contradictions.
- Missing interfaces.
- Conflicting constraints.
- Potentially resolved findings.
- Remaining defects.
- Newly introduced defects.

Do not assume a newer attachment is automatically authoritative.

Preserve document-specific citations.

Distinguish exact matches from uncertain semantic matches.

Return structured comparison findings and questions requiring human resolution.

An existing audit must remain unchanged until the user explicitly requests and the application performs revalidation.

For each change, cite the relevant document-specific original passages. Cross-document contradictions and modifications must reference distinct documents. If evidence is missing, identify the scope inspected. Mark uncertain semantic alignment as uncertain and ask who can resolve it.
