"""Measure case-level defect detection and source grounding on labeled fixtures."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from specguard.core import audit_documents
from specguard.ingest import ingest_document

FIXTURES = Path(__file__).parent / "fixtures"


def load_manifest():
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    cases = manifest["cases"]
    taxonomy = {kind for case in cases for kind in case["positives"] + case["negative_controls"]}
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Fixture case IDs must be unique and the manifest must contain a case.")
    for case in cases:
        positives, controls = set(case["positives"]), set(case["negative_controls"])
        source = {name: (FIXTURES / name).read_text(encoding="utf-8") for name in case["documents"]}
        if positives & controls or set(case["anchors"]) != positives:
            raise ValueError(f"Inconsistent labels in case {case['id']}.")
        for anchors in case["anchors"].values():
            if not anchors or any(
                not anchor["quote_fragment"]
                or anchor["quote_fragment"] not in source.get(anchor["document"], "")
                for anchor in anchors
            ):
                raise ValueError(f"Invalid evidence anchor in case {case['id']}.")
    return manifest, taxonomy


def fraction(numerator, denominator):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(numerator / denominator, 6) if denominator else None,
    }


def source_valid(evidence, documents):
    location = evidence.location
    document = documents.get(location.document_id)
    if document is None:
        return False
    block = next((row for row in document.blocks if row.block_id == location.block_id), None)
    if block is None:
        return False
    block_location = block.location
    if evidence.kind == "absence":
        return (
            block_location == location
            and bool(evidence.scope)
            and evidence.scope in {document.document_id, block.block_id, location.section}
            and evidence.quote is None
        )
    if not evidence.quote or evidence.quote not in block.text:
        return False
    if (location.section, location.page, location.bbox) != (
        block_location.section,
        block_location.page,
        block_location.bbox,
    ):
        return False
    start, end = location.char_start, location.char_end
    if None in (start, end, block_location.char_start, block_location.char_end):
        return False
    if not block_location.char_start <= start < end <= block_location.char_end:
        return False
    if document.original_text[start:end] != evidence.quote:
        return False
    if block_location.line_start is None:
        return location.line_start is None and location.line_end is None
    prefix = document.original_text[block_location.char_start : start]
    first = block_location.line_start + len(re.findall(r"\r\n|[\r\n]", prefix))
    final = first + len(re.findall(r"\r\n|[\r\n]", evidence.quote.rstrip("\r\n")))
    return (location.line_start, location.line_end) == (first, final)


def anchors_match(finding, anchors, documents):
    verified_quotes = [
        (documents[evidence.location.document_id].filename, evidence.quote)
        for evidence in finding.evidence
        if evidence.kind == "quote" and source_valid(evidence, documents)
    ]
    return all(
        any(
            filename == anchor["document"] and anchor["quote_fragment"] in quote
            for filename, quote in verified_quotes
        )
        for anchor in anchors
    )


def signature(result):
    source_rows = [
        (
            requirement.requirement_id,
            requirement.original_id,
            [evidence.model_dump(mode="json") for evidence in requirement.evidence],
        )
        for requirement in result.requirements
    ]
    finding_rows = [
        (
            finding.finding_id,
            finding.kind,
            finding.status,
            finding.severity,
            finding.document_ids,
            finding.requirement_ids,
            [evidence.model_dump(mode="json") for evidence in finding.evidence],
        )
        for finding in result.findings
    ]
    data = (
        source_rows,
        finding_rows,
        result.coverage.model_dump(),
        result.readiness.verdict,
    )
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def score_cases(cases, taxonomy, repetitions, provider_factory=None):
    counts = Counter()
    times_ms = []
    details = []
    token_totals = {field: [] for field in ("input_tokens", "reasoning_tokens", "output_tokens")}

    for case in cases:
        signatures = []
        for run in range(repetitions):
            started = perf_counter()
            documents = [ingest_document(name, (FIXTURES / name).read_bytes()) for name in case["documents"]]
            provider = provider_factory() if provider_factory is not None else None
            result = audit_documents(documents, provider=provider)
            times_ms.append((perf_counter() - started) * 1000)
            signatures.append(signature(result))
            counts["usage_records"] += len(result.usage)
            for record in result.usage:
                for field, amounts in token_totals.items():
                    amount = getattr(record, field)
                    if amount is not None:
                        amounts.append(amount)

            if run != 0:
                continue
            expected = set(case["positives"])
            negative_controls = set(case["negative_controls"])
            confirmed = {row.kind for row in result.findings if row.status == "confirmed"}
            confirmed_in_scope = confirmed & taxonomy
            true_positives = expected & confirmed_in_scope
            false_positives = confirmed_in_scope - expected
            false_negatives = expected - confirmed_in_scope
            clarifications = {row.kind for row in result.findings if row.status != "confirmed"}
            surfaced_unconfirmed = false_negatives & clarifications
            counts.update(
                tp=len(true_positives),
                fp=len(false_positives),
                fn=len(false_negatives),
                surfaced_unconfirmed=len(surfaced_unconfirmed),
                negative_controls=len(negative_controls),
                negative_controls_triggered=len(negative_controls & confirmed),
                complete_audits=int(result.coverage.complete),
                individually_assessed=result.coverage.individually_assessed,
                reported_requirements=len(result.requirements),
            )
            extracted = Counter(row.original_id for row in result.requirements)
            expected_requirements = Counter(case["requirements"])
            counts["expected_requirements"] += expected_requirements.total()
            counts["matched_requirements"] += (expected_requirements & extracted).total()

            documents_by_id = {document.document_id: document for document in documents}
            localized = {
                finding.kind
                for finding in result.findings
                if finding.status == "confirmed"
                and finding.kind in true_positives
                and anchors_match(finding, case["anchors"][finding.kind], documents_by_id)
            }
            counts["localized"] += len(localized)
            invalid_evidence = []
            for requirement in result.requirements:
                for evidence in requirement.evidence:
                    counts["requirement_evidence_checks"] += 1
                    if evidence.location.document_id == requirement.document_id and source_valid(
                        evidence, documents_by_id
                    ):
                        counts["requirement_evidence_valid"] += 1
                    else:
                        invalid_evidence.append(evidence.evidence_id)
            for finding in result.findings:
                for evidence in finding.evidence:
                    counts[f"{evidence.kind}_checks"] += 1
                    if evidence.location.document_id in finding.document_ids and source_valid(
                        evidence, documents_by_id
                    ):
                        counts[f"{evidence.kind}_valid"] += 1
                    else:
                        invalid_evidence.append(evidence.evidence_id)
            details.append(
                {
                    "id": case["id"],
                    "true_positives": sorted(true_positives),
                    "true_positives_at_expected_source": sorted(localized),
                    "false_positives": sorted(false_positives),
                    "false_negatives": sorted(false_negatives),
                    "other_confirmed_kinds": sorted(confirmed - taxonomy),
                    "clarification_kinds": sorted(clarifications),
                    "unconfirmed_labeled_pairs": sorted(surfaced_unconfirmed),
                    "expected_requirement_ids": case["requirements"],
                    "extracted_requirement_ids": [row.original_id for row in result.requirements],
                    "invalid_evidence_ids": invalid_evidence,
                    "analysis_complete": result.coverage.complete,
                }
            )

        counts["repeat_comparisons"] += len(signatures) - 1
        repeat_matches = sum(item == signatures[0] for item in signatures[1:])
        counts["repeat_matches"] += repeat_matches
        details[-1]["repeats_match"] = repeat_matches == len(signatures) - 1

    true_positives = counts["tp"]
    return {
        "cases": len(cases),
        "repeat_count": repetitions,
        "taxonomy": sorted(taxonomy),
        "detection": {
            "true_positives": true_positives,
            "false_positives": counts["fp"],
            "false_negatives": counts["fn"],
            "unconfirmed_labeled_pairs": counts["surfaced_unconfirmed"],
            "precision": fraction(true_positives, true_positives + counts["fp"]),
            "recall": fraction(true_positives, true_positives + counts["fn"]),
            "f1": fraction(2 * true_positives, 2 * true_positives + counts["fn"] + counts["fp"]),
            "false_positive_rate": fraction(
                counts["negative_controls_triggered"], counts["negative_controls"]
            ),
        },
        "evidence": {
            "requirement_evidence_validity": fraction(
                counts["requirement_evidence_valid"], counts["requirement_evidence_checks"]
            ),
            "quote_validity": fraction(counts["quote_valid"], counts["quote_checks"]),
            "localization_among_true_positives": fraction(counts["localized"], true_positives),
            "localized_detection_recall": fraction(counts["localized"], true_positives + counts["fn"]),
            "absence_scope_validity": fraction(counts["absence_valid"], counts["absence_checks"]),
        },
        "coverage": {
            "requirements_extracted": fraction(
                counts["matched_requirements"], counts["expected_requirements"]
            ),
            "individually_assessed": fraction(
                counts["individually_assessed"], counts["reported_requirements"]
            ),
            "complete_audits": fraction(counts["complete_audits"], len(cases)),
        },
        "repeatability": fraction(counts["repeat_matches"], counts["repeat_comparisons"]),
        "time_ms": {
            "executions": len(times_ms),
            "total": round(sum(times_ms), 3),
            "mean": round(mean(times_ms), 3),
            "median": round(median(times_ms), 3),
            "max": round(max(times_ms), 3),
        },
        "provider_usage": {
            "records": counts["usage_records"],
            **{field: sum(amounts) if amounts else None for field, amounts in token_totals.items()},
        },
        "case_results": details,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    parser.add_argument("--consent", action="store_true", help="permit external DeepSeek requests")
    parser.add_argument("--repeat", type=int, help="runs per case, defaults to 3 offline and 1 live")
    parser.add_argument("--case", action="append", help="selected case ID, repeatable")
    parser.add_argument("--output", type=Path, help="write JSON to this path")
    args = parser.parse_args()
    repetitions = args.repeat if args.repeat is not None else (1 if args.mode == "live" else 3)
    if not 1 <= repetitions <= 20:
        parser.error("--repeat must be between 1 and 20")
    provider_factory = None
    if args.mode == "live":
        if not args.consent:
            parser.error("--mode live requires --consent to send fixture text to DeepSeek")
        from specguard.intelligence import Intelligence
        from specguard.provider import IntelligenceError

        def provider_factory():
            try:
                return Intelligence(live=True)
            except IntelligenceError as error:
                parser.error(f"live provider configuration failed ({error.code})")

    manifest, taxonomy = load_manifest()
    cases = manifest["cases"]
    if args.case:
        unknown = set(args.case) - {case["id"] for case in cases}
        if unknown:
            parser.error(f"unknown case IDs: {', '.join(sorted(unknown))}")
        cases = [case for case in cases if case["id"] in args.case]

    results = {
        "mode": args.mode,
        "fixture_version": manifest["version"],
        **score_cases(cases, taxonomy, repetitions, provider_factory),
    }
    serialized = json.dumps(results, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
