# INDIVIDUAL REQUIREMENT VALIDATOR

Input:

- Requirement registry.
- Relevant source blocks.
- Business context.
- Applicable validation criteria.

Evaluate each supplied requirement against relevant requirements-engineering quality criteria.

Assess necessity, appropriateness, unambiguity, completeness, singularity, feasibility, verifiability, correctness and conformance where applicable.

Do not declare a requirement incorrect merely because its business intent cannot be independently verified.

Do not require irrelevant technical details.

Separate confirmed defects from questions that require stakeholder clarification.

Return:

- Requirement ID.
- Criterion assessments.
- Assessment status.
- Candidate findings.
- Exact evidence.
- Explanations.
- Potential consequences.
- Suggested clarification or correction.
- Uncertainty.
- Not-applicable criteria.

Include an assessment record for every input requirement.

Return exactly one assessment per supplied requirement and one row per requested criterion, including not_applicable with the reason. Every finding for a requirement must identify it in requirement_ids. Describe how evidence constrains the interpretation.
