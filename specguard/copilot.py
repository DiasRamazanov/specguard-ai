"""Evidence navigation and separately approved, read-only semantic operations."""

import re

from fastapi import HTTPException

from .core import verify_evidence
from .http_models import CopilotResponse, RevisionDraft
from .intelligence import IntelligenceError
from .service import capacity, event, get_result, job_for, lock, provider_for


def select(items, key, value):
    if value is None:
        return None
    match = next((item for item in items if getattr(item, key) == value), None)
    if match is None:
        raise HTTPException(404, "Выбранный объект не найден.")
    return match


def selected_attachments(job, ids):
    with lock:
        if len(set(ids)) != len(ids):
            raise HTTPException(422, "Вложение указано несколько раз.")
        if any(i not in job.attachments for i in ids):
            raise HTTPException(404, "Вложение не найдено в этом аудите.")
        return [job.attachments[i] for i in ids]


def unique_documents(docs):
    return list({doc.document_id: doc for doc in docs}.values())


def resolve_evidence(refs, docs):
    index = {(doc.document_id, b.block_id): b for doc in docs for b in doc.blocks}
    verified = []
    for ref in refs:
        evidence = verify_evidence(ref, index)
        if evidence is None:
            raise HTTPException(502, "Ссылка на первоисточник не прошла проверку.")
        verified.append(evidence)
    return verified


def context(docs, requirements, findings):
    from .core import provider_block, provider_finding, provider_requirement

    return dict(
        blocks=[provider_block(b) for doc in docs for b in doc.blocks],
        requirements=[provider_requirement(r) for r in requirements],
        findings=[provider_finding(f) for f in findings],
    )


def invoke(engine, role, payload):
    try:
        return engine.run(role, payload)
    except IntelligenceError as exc:
        raise HTTPException(502, f"Семантическая операция не завершена ({exc.code}).") from None


def navigate(question, docs, requirement, finding):
    if finding:
        return CopilotResponse(
            answer=f"{finding.title}. {finding.explanation}\n{finding.impact}",
            evidence=finding.evidence,
            related_finding_ids=[finding.finding_id],
            clarification_questions=[finding.recommendation],
            proposed_actions=["open_evidence"],
            uncertainty=finding.uncertainty,
        )
    if requirement:
        return CopilotResponse(
            answer=requirement.summary,
            evidence=requirement.evidence,
            related_finding_ids=[],
            clarification_questions=[],
            proposed_actions=["open_evidence"],
            uncertainty=requirement.uncertainty,
        )
    terms = set(re.findall(r"\w{3,}", question.casefold()))
    matches = []
    for doc in docs:
        for block in doc.blocks:
            score = len(terms.intersection(re.findall(r"\w{3,}", block.text.casefold())))
            if score:
                matches.append((score, block))
    matches.sort(key=lambda pair: pair[0], reverse=True)
    evidence = resolve_evidence(
        [
            {"document_id": b.location.document_id, "block_id": b.block_id, "quote": b.text}
            for _, b in matches[:3]
        ],
        docs,
    )
    return CopilotResponse(
        answer=(
            "В источниках найдены фрагменты по словам запроса."
            if evidence
            else "Для ответа недостаточно сведений. Выберите требование или замечание."
        ),
        evidence=evidence,
        related_finding_ids=[],
        clarification_questions=[],
        proposed_actions=["open_evidence"] if evidence else [],
        uncertainty="В локальном режиме доступен поиск фрагментов по совпадению слов.",
    )


def ask(s, audit_id, req):
    job, audit = job_for(s, audit_id), get_result(s, audit_id)
    with capacity(job.conversation_lock):
        docs = unique_documents(job.docs + [doc for _, doc in selected_attachments(job, req.attachment_ids)])
        requirement = select(audit.requirements, "requirement_id", req.requirement_id)
        finding = select(audit.findings, "finding_id", req.finding_id)
        engine = provider_for(req.mode, req.allow_external_processing)
        if engine is None:
            return navigate(req.question, docs, requirement, finding)
        payload = context(docs, audit.requirements, audit.findings)
        # Keep history scoped to exactly the selected attachments and audit.
        selection = tuple(sorted(req.attachment_ids))
        history = [turn for key, turn in job.history if key == selection][-6:]
        payload.update(
            question=req.question,
            selected_requirement_id=req.requirement_id,
            selected_finding_id=req.finding_id,
            history=history,
            business_context=f"Вердикт аудита: {audit.readiness.verdict}. {audit.readiness.rationale}",
            complex=bool(finding or req.attachment_ids),
            supported_actions=["open_evidence", "request_revision", "compare_documents"],
        )
        event(job, "copilot_thinking")
        output = invoke(engine, "copilot", payload)
        answer = CopilotResponse(
            answer=output["answer"],
            evidence=resolve_evidence(output["evidence"], docs),
            related_finding_ids=output["related_finding_ids"],
            clarification_questions=output["questions"],
            proposed_actions=output["actions"],
            uncertainty=output["uncertainty"],
        )
        job.history.extend(
            [
                (selection, {"role": "user", "content": req.question}),
                (selection, {"role": "assistant", "content": answer.answer[:4000]}),
            ]
        )
        del job.history[:-12]
        event(job, "copilot_response_completed")
        return answer


def propose(s, audit_id, req):
    job, audit = job_for(s, audit_id), get_result(s, audit_id)
    requirement = select(audit.requirements, "requirement_id", req.requirement_id)
    finding = select(audit.findings, "finding_id", req.finding_id)
    if requirement.requirement_id not in finding.requirement_ids:
        raise HTTPException(422, "Замечание относится к другому требованию.")
    engine = provider_for("live", req.allow_external_processing)
    with capacity(job.conversation_lock):
        payload = context(job.docs, audit.requirements, [finding])
        payload.update(
            target_requirement_id=req.requirement_id, approved_assumptions=req.approved_assumptions
        )
        output = invoke(engine, "revision", payload)
        output["proposed_revision"] = output.pop("revision")
        output["evidence"] = resolve_evidence(output["evidence"], job.docs)
        return RevisionDraft(**output)


def compare_documents(s, audit_id, req):
    job, audit = job_for(s, audit_id), get_result(s, audit_id)
    primary = select(job.docs, "document_id", req.primary_document_id)
    with capacity(job.conversation_lock):
        entries = selected_attachments(job, req.attachment_ids)
        if any(meta.purpose not in {"comparison", "revision"} for meta, _ in entries):
            raise HTTPException(422, "Для сравнения укажите спецификации или новые редакции.")
        docs = unique_documents([primary, *(doc for _, doc in entries)])
        if len(docs) != len(entries) + 1:
            raise HTTPException(422, "Выбранные документы имеют одинаковое содержимое.")
        engine = provider_for("live", req.allow_external_processing)
        requirements = [r for r in audit.requirements if r.document_id == primary.document_id]
        findings = [f for f in audit.findings if set(f.document_ids) == {primary.document_id}]
        payload = context(docs, requirements, findings)
        payload.update(
            primary_document_id=primary.document_id,
            supplementary_document_ids=[d.document_id for d in docs[1:]],
            purpose=req.purpose,
        )
        event(job, "comparing_documents")
        output = invoke(engine, "compare", payload)
        for change in output["changes"]:
            change["evidence"] = resolve_evidence(change["evidence"], docs)
        return output
