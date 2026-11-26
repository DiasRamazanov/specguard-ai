"""Call-local references for the optional compact role transport."""

import json

from .provider import IntelligenceError

ROLES = {"individual", "critic", "risk"}
VERSION = "v1-refs1"
MAX_QUOTE = 12000  # Evidence.quote's public length limit.


def _object(value):
    if not isinstance(value, dict):
        raise IntelligenceError("invalid_role_output")
    return value


def _array(value):
    if not isinstance(value, list):
        raise IntelligenceError("invalid_role_output")
    return value


def _lookup(mapping, handle):
    if not isinstance(handle, str):
        raise IntelligenceError("invalid_role_output")
    if handle not in mapping:
        raise IntelligenceError("unknown_role_reference")
    return mapping[handle]


class ReferenceWire:
    """Encode verified input and expand only the handles minted for this call."""

    def __init__(self, role, context):
        self.role = role
        self.evidence = {}
        self._handles = {}
        self._blocks = {}
        self._sources = {}
        self.allowed = {}
        self.requirements = {}
        self.targets = {}
        self.data = {"blocks": [], "requirements": []}
        for block in context["blocks"]:
            source = (block["document_id"], block["block_id"])
            record = {key: block[key] for key in ("document_id", "block_id", "section")}
            self._blocks[source] = record
            self.data["blocks"].append(record)
            passages = []
            for start in range(0, len(block["text"]), MAX_QUOTE):
                passage = block["text"][start : start + MAX_QUOTE]
                if passage.strip():
                    handle = self._evidence_ref(source, "quote", passage, None)
                    passages.append({"ref": handle, "text": passage})
                else:
                    passages.append({"text": passage})
            record["passages"] = passages

        if context.get("business_context"):
            self.data["business_context"] = context["business_context"]
        registry = {}
        for number, requirement in enumerate(context["requirements"], 1):
            handle = f"R{number}"
            original = requirement["requirement_id"]
            self.requirements[handle] = original
            registry[original] = handle
            row = {**requirement, "requirement_id": handle, "evidence": self._cites(requirement)}
            self.allowed[handle] = set(row["evidence"])
            if role == "individual":
                scopes = dict.fromkeys(self._sources[ref] for ref in row["evidence"])
                row["absence_refs"] = [self._absence_ref(source) for source in scopes]
                self.allowed[handle].update(row["absence_refs"])
            self.data["requirements"].append(row)

        if role == "individual":
            self.data["criteria"] = context["criteria"]
            return
        rows, target_key, prefix = (
            ("candidates", "candidate_id", "C") if role == "critic" else ("findings", "finding_id", "F")
        )
        self.data[rows] = []
        for number, item in enumerate(context[rows], 1):
            handle = f"{prefix}{number}"
            self.targets[handle] = item[target_key]
            linked = [registry[key] for key in item["requirement_ids"]]
            cites = self._cites(item)
            allowed = set(cites)
            if role == "critic":
                for req in linked:
                    allowed.update(self.allowed[req])
            self.allowed[handle] = allowed
            self.data[rows].append(
                {
                    **item,
                    target_key: handle,
                    "requirement_ids": linked,
                    "evidence": cites,
                    "support_refs": sorted(allowed),
                }
            )

    def _evidence_ref(self, source, kind, quote, scope):
        key = (*source, kind, quote, scope)
        if key not in self._handles:
            handle = f"E{len(self.evidence) + 1}"
            self._handles[key] = handle
            self.evidence[handle] = {
                "document_id": source[0],
                "block_id": source[1],
                "kind": kind,
                "quote": quote,
                "scope": scope,
            }
            self._sources[handle] = source
        return self._handles[key]

    def _cites(self, item):
        refs = []
        for cite in item["evidence"]:
            source = (cite["document_id"], cite["block_id"])
            key = (*source, cite["kind"], cite["quote"], cite["scope"])
            if key in self._handles:
                ref = self._handles[key]
            else:
                ref = self._evidence_ref(source, cite["kind"], cite["quote"], cite["scope"])
                if cite["kind"] == "absence":
                    self._blocks[source].setdefault("absence_scopes", {})[ref] = cite["scope"]
                else:
                    self._blocks[source].setdefault("excerpts", {})[ref] = cite["quote"]
            refs.append(ref)
        return refs

    def _absence_ref(self, source):
        ref = self._evidence_ref(source, "absence", None, source[1])
        self._blocks[source].setdefault("absence_scopes", {})[ref] = source[1]
        return ref

    def schema(self, output_type):
        schema = output_type.model_json_schema()
        schema["$defs"]["Evidence"] = {"type": "string", "pattern": "^E[1-9][0-9]*$"}
        if self.role == "individual":
            defs = schema["$defs"]
            criterion = defs.pop("CriterionAssessment")["properties"]
            defs["Assessment"]["properties"]["criteria"] = {
                "type": "object",
                "properties": {key: {"$ref": "#/$defs/AssessmentPair"} for key in self.data["criteria"]},
                "required": self.data["criteria"],
                "additionalProperties": False,
            }
            defs["AssessmentPair"] = {
                "type": "array",
                "prefixItems": [criterion["status"], criterion["explanation"]],
                "minItems": 2,
                "maxItems": 2,
            }
        return json.dumps(schema, ensure_ascii=False, separators=(",", ":"))

    def _expand(self, refs, allowed=None):
        result = []
        for handle in _array(refs):
            cite = _lookup(self.evidence, handle)
            if allowed is not None and handle not in allowed:
                raise IntelligenceError("unrelated_evidence_reference")
            result.append(cite)
        return result

    def decode(self, output):
        decoded = dict(_object(output))
        if self.role == "individual":
            decoded["assessments"] = [
                self._assessment(_object(row)) for row in _array(decoded.get("assessments"))
            ]
        else:
            rows, target_key = (
                ("verdicts", "candidate_id") if self.role == "critic" else ("risks", "finding_id")
            )
            expanded = []
            for raw in _array(decoded.get(rows)):
                row = dict(_object(raw))
                target = row.get(target_key)
                row[target_key] = _lookup(self.targets, target)
                row["evidence"] = self._expand(row.get("evidence"), self.allowed[target])
                if self.role == "critic":
                    if row.get("verdict") == "confirmed" and not any(
                        cite["kind"] == "quote" for cite in row["evidence"]
                    ):
                        raise IntelligenceError("missing_support")
                    counter = self._expand(row.get("counterevidence"))
                    if any(
                        cite["kind"] == "absence" and ref not in self.allowed[target]
                        for ref, cite in zip(row["counterevidence"], counter, strict=True)
                    ):
                        raise IntelligenceError("unrelated_evidence_reference")
                    row["counterevidence"] = counter
                    if row.get("duplicate_of") is not None:
                        row["duplicate_of"] = _lookup(self.targets, row["duplicate_of"])
                expanded.append(row)
            decoded[rows] = expanded
        return decoded

    def _assessment(self, raw):
        row = dict(raw)
        target = row.get("requirement_id")
        row["requirement_id"] = _lookup(self.requirements, target)
        criteria = []
        for criterion, pair in _object(row.get("criteria")).items():
            if len(_array(pair)) != 2:
                raise IntelligenceError("invalid_role_output")
            criteria.append({"criterion": criterion, "status": pair[0], "explanation": pair[1]})
        row["criteria"] = criteria
        findings = []
        for raw_finding in _array(row.get("findings")):
            finding = dict(_object(raw_finding))
            linked = _array(finding.get("requirement_ids"))
            finding["requirement_ids"] = [_lookup(self.requirements, handle) for handle in linked]
            allowed = set().union(*(self.allowed[req] for req in linked))
            refs = finding.get("evidence")
            finding["evidence"] = self._expand(refs, allowed)
            if not self.allowed[target].intersection(refs):
                raise IntelligenceError("unrelated_evidence_reference")
            findings.append(finding)
        row["findings"] = findings
        return row
