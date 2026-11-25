# BENCHMARK CANDIDATE GENERATOR

Generate synthetic FinTech requirement specifications for independent evaluation.

Include both clean examples and controlled defective examples.

Cover:

- Ambiguity.
- Contradictions.
- Missing information.
- Inconsistent units.
- Unverifiable requirements.
- Non-atomic requirements.
- API contract problems.
- Cross-document conflicts.
- False-positive traps.
- Benign prompt injection attempts.

Return candidate expected defects and source references separately.

These labels are candidates, not authoritative ground truth.

They require independent human or Claude Code review before benchmark use.

Never include held-out benchmark answers in production prompts.

Generate uniquely identified synthetic documents with uniquely identified blocks. Keep case classifications in case_labels and proposed expected defects in candidate_labels, separate from the documents and their block text. Include at least one clean and one intentionally defective case. Do not present labels as independently reviewed; set requires_review true. Do not use any real customer or confidential data.
