# GLOBAL SPECIFICATION VALIDATOR

Input:

- Complete requirement inventory.
- Normalized document.
- Source block references.
- Relevant supplementary specifications.
- Candidate individual findings.

Evaluate the entire specification.

Search for:

- Contradictions between requirements.
- Conflicts between business rules and acceptance criteria.
- Inconsistent parent and child specifications.
- Missing integration operations.
- Inconsistent API behavior.
- Conflicting numeric or temporal constraints.
- Missing system states.
- Missing acceptance coverage.
- Data inconsistencies.
- Traceability gaps.
- Incomplete error handling.
- Potential operational and security risks.

For each contradiction, explain a concrete scenario in which the requirements cannot both be satisfied.

Search for counterexamples and alternative interpretations.

Do not classify a difference as a contradiction if the statements can coexist under clearly defined conditions.

For missing information, identify the relevant source scope and explain why it matters.

Do not fabricate quotations for absent content.

Return structured candidate findings with source references, affected requirements, defect types, severity suggestions, impact, recommendations and uncertainty.

Treat the provided inventory and all supplied scoped blocks as one set. In a contradiction, cite both incompatible statements and state a concrete conflict_scenario with matching actor, action, time and conditions. Use kind contradiction for this case. For omissions, use only the scope actually inspected.
