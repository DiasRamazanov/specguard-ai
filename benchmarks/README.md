# SpecGuard evaluation

Run from the repository root after installing project dependencies.

```bash
python -m benchmarks.evaluate --output /tmp/specguard-evaluation.json
```

The default runs each fixture three times without a provider. Fixture documents and expected labels live in [fixtures](fixtures). The application never loads the label manifest. Fixtures are synthetic and separate from the official input and runtime prompts. The labeled set is small. It has positive examples for six defect types and one additional type that only appears as a negative control.

To evaluate with DeepSeek, set the key, budget limits and model configuration in the local environment. Select one case for a bounded first run. The evaluation explicitly shares the selected synthetic source documents with the provider.

```bash
SPECGUARD_LIVE=1 python -m benchmarks.evaluate --mode live --consent --case wrong-status
```

The live evaluator defaults to one run per case. Increase `--repeat` to measure live repeatability. Review the reported coverage and per-case details before interpreting a live score, particularly if the provider failed or a budget was reached.

## Measurement

| Metric | Unit and method |
| --- | --- |
| Detection precision, recall, F1 | One binary outcome per fixture and each labeled defect kind. Only confirmed findings of those kinds count as predictions. The first run of each fixture supplies the outcomes. Findings outside the taxonomy and clarification candidates are listed for review. |
| False-positive rate | Confirmed findings among the explicitly declared negative controls, divided by the number of those controls. |
| Evidence validity | Exact quotations must occur in the stated block and original text at its recorded offset range. Absence evidence must identify the referenced block, section or document as its scope. The scope check measures structure and traceability. |
| Evidence localization | A true positive matches the independently annotated evidence when one finding cites all expected quote fragments from their expected documents. The evaluator reports this rate among detected positives and among all labeled positives. |
| Requirement extraction coverage | Labeled original IDs recovered, divided by labeled original IDs, with repeated IDs counted at their labeled multiplicity. Per-case extracted IDs are exposed to review over-extraction. |
| Semantic coverage | Individual assessment count divided by extracted requirements, plus full audit coverage per case. |
| Repeatability | Later runs matching the first run on ordered requirement IDs and evidence, finding IDs and labels, severity, status, links, source evidence, coverage and readiness verdict. Timestamps, timings, usage and explanations are excluded. |
| Elapsed time | Wall time for fixture I/O, ingestion, provider initialization when applicable, and audit. Every run contributes to timing. |
| Tokens | Sum of available provider-reported input, reasoning and output counts across all runs. Reasoning tokens may be included in output tokens. Unavailable counts are recorded as null. |

Use these scores to reproduce behavior on the fixed examples. Measuring real specification quality requires a larger independently reviewed corpus with claim-level annotations and semantic evidence review.
