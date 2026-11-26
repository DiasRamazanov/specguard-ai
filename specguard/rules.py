"""General-purpose deterministic rules and requirement seed extraction."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal

from .models import Requirement, SourceBlock, SourceDocument

_ID_TEXT = r"[A-ZА-ЯЁ][A-ZА-ЯЁ0-9_]{0,14}[-–]\d+(?:[.-]\d+)*"
_ID_START = re.compile(
    rf"^\s*(?:\|\s*|[-+*]\s+|\d+[.)]\s+)?(?:\*\*|`)?(?P<id>{_ID_TEXT})(?=[\s.:)\]|`*—]|$)",
    re.IGNORECASE,
)
_REFERENCE = re.compile(
    rf"(?:\b(?:see|refer(?:s)? to|согласно|см\.?|по требованию|ссылк\w* на)\s+"
    rf"(?:requirement\s+|требовани\w+\s+)?)[`*\[(]*(?P<id>{_ID_TEXT})",
    re.IGNORECASE,
)
_NORMATIVE = re.compile(
    r"\b(?:must\b|shall\b|required\b|"
    r"долж[еён]\w*|должн\w*|необходим\w*|обяз\w*|запрещ\w*|допускается|"
    r"хранить|возвращать|проверить|использовать)\b",
    re.IGNORECASE,
)
_METADATA = re.compile(
    r"(?:^| › )(?:общие сведения|ревью требований|блок согласующих|чек[- ]?лист|"
    r"шаблон|метаданные|checklist|template|metadata|approvals?|overview)(?:$| › )",
    re.IGNORECASE,
)
_REQUIREMENT_SECTION = re.compile(
    r"при[её]мк|acceptance\b|functional requirements?|business rules?|"
    r"non.functional|data requirements?|integration|функциональн|"
    r"требовани[яй] к данн|требовани[яй] к интеграции|особые правила|"
    r"логика работы|business requirements?|требовани[яй] к изменениям",
    re.IGNORECASE,
)
_PLACEHOLDER = re.compile(
    r"\b(?:TBD|TBC|TODO|FIXME|XXX|заполня(?:ется|ются)\b[^.\n|]*|"
    r"вставить значение|уточнить позже)\b|\{\{[\w .-]{1,60}\}\}",
    re.IGNORECASE,
)
_FILL_EMPTY = {"", "—", "–", "-", "tbd", "n/a", "none", "null"}
_HTTP = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+[`']?(/[A-Za-z0-9_/{}/.-]+)\b")
_GET_FIELD = re.compile(r"(?:\bREST type\b|\bHTTP method\b|\bметод\b)[^\n]{0,12}\bGET\b", re.I)
_MUTATION = re.compile(
    r"\b(?:creat(?:e|es|ing)|updat(?:e|es|ing)|delet(?:e|es|ing)|sav(?:e|es|ing)|"
    r"modif(?:y|ies|ying)|"
    r"сохран(?:яет|ить|ять)|обнов(?:ить|лять|ляет)|удал(?:ить|ять|яет)|"
    r"созда(?:ть|вать|ёт|ет)|замен(?:ить|ять|яет))\b",
    re.IGNORECASE,
)
_MUTATION_EXCLUSION = re.compile(
    r"\b(?:not|never|doesn't|cannot|without|no|не|без|запрещено|history|information|"
    r"информаци\w*|сведения|истори\w*|журнал\w*|статус)\b[^.;\n]{0,32}$",
    re.I,
)
_STATUS_NAME = {
    200: "ok",
    201: "created",
    202: "accepted",
    204: "no content",
    400: "bad request",
    401: "unauthorized",
    403: "forbidden",
    404: "not found",
    409: "conflict",
    422: "unprocessable content",
    429: "too many requests",
    500: "internal server error",
    502: "bad gateway",
    503: "service unavailable",
}
_STATUS_DECLARATION = re.compile(
    r"(?<![\w/])(?P<code>[245]\d\d)\.?[\s:|—–-]+(?:un)?successful\s+[—–-]\s+"
    r"|(?<![\w/])(?P<direct>[245]\d\d)\.?[\s:|—–-]+(?=[A-Za-z])",
    re.I,
)
_TYPE = re.compile(
    r"^\s*`?(?P<field>[a-zA-Z_][a-zA-Z0-9_.]*)`?\s*\|\s*"
    r"(?P<type>integer|string|number|boolean|array|object)\b",
    re.I,
)
_ACCEPTANCE = re.compile(r"acceptance|при[её]мк", re.I)
_REQUEST = re.compile(r"request|запрос|query-параметры|path-параметры", re.I)
_RESPONSE = re.compile(r"response|ответ", re.I)
_REQUIRED_ACCEPTANCE = re.compile(
    r"(?:every|each|all)\s+(?:functional\s+)?requirements?[^.\n]{0,75}\bacceptance\b"
    r"|кажд\w+\s+(?:функциональн\w+\s+)?требовани\w+[^.\n]{0,90}при[её]мк",
    re.I,
)
_REQUIRED_ID = re.compile(
    r"(?:every|each|all)\s+(?:functional\s+)?requirements?[^.\n]{0,55}\b(?:id|identifier)\b"
    r"|кажд\w+\s+(?:функциональн\w+\s+)?требовани\w+[^.\n]{0,55}идентификатор",
    re.I,
)
_OPERATION_REFERENCE = re.compile(
    r"(?:\b(?:calls?|uses?|via|вызывает|через)\s+)(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)"
    r"\s+[`']?(/[A-Za-z0-9_/{}/.-]+)",
    re.I,
)
_BOUND_WORD = (
    r"minimum|maximum|min|max|at least|at most|no less than|no more than|минимум|максимум|не менее|не более"
)
_UNIT_WORD = r"milliseconds?|seconds?|minutes?|hours?|days?|bytes?|seconds?|s|ms|min|h|[км]б|мс|секунд\w*|минут\w*|час\w*|₸|\$|€|[A-Z]{3}"
_NUMBER = r"-?(?:\d{1,3}(?:[ \u00a0\u202f]\d{3})+|\d+)(?:[.,]\d+)?"
_BOUND_HEAD = re.compile(
    rf"^\s*(?:[-*+]\s*)?(?P<bound>{_BOUND_WORD})\s+(?P<subject>[^:;.!\n]{{2,60}}?)"
    rf"\s*[:=]?\s+(?P<number>{_NUMBER})(?:\s*(?P<unit>{_UNIT_WORD})(?!\w))?",
    re.I | re.M,
)
_BOUND_INLINE = re.compile(
    rf"(?:^|[.!?\n])\s*(?:[-*+]\s+)?(?P<subject>[\w][\w \t-]{{1,55}}?)"
    rf"\s+(?:(?:must|shall)\s+be\s+|(?:долж[еннаы]+)\s+быть\s+)?"
    rf"(?P<bound>{_BOUND_WORD})\s+(?P<number>{_NUMBER})(?:\s*(?P<unit>{_UNIT_WORD})(?!\w))?",
    re.I,
)
_ROLE_SECTION = (
    (_ACCEPTANCE, "acceptance"),
    (re.compile(r"нефункциональн|non.functional", re.I), "non_functional"),
    (re.compile(r"интеграц|integration", re.I), "integration"),
    (re.compile(r"требовани[яй] к данн|data requirements?", re.I), "data"),
    (re.compile(r"api\b|request|response|запрос|ответ|логика работы", re.I), "api"),
    (re.compile(r"особые правила|business rules?", re.I), "business_rule"),
)
_UNITS = {
    "ms": ("time", Decimal("0.001")),
    "мс": ("time", Decimal("0.001")),
    "s": ("time", Decimal(1)),
    "second": ("time", Decimal(1)),
    "min": ("time", Decimal(60)),
    "minute": ("time", Decimal(60)),
    "h": ("time", Decimal(3600)),
    "hour": ("time", Decimal(3600)),
    "day": ("time", Decimal(86400)),
    "₸": ("kzt", Decimal(1)),
    "$": ("usd", Decimal(1)),
    "€": ("eur", Decimal(1)),
}
_LOWER_BOUNDS = {"minimum", "min", "at least", "no less than", "минимум", "не менее"}


def original_ids(block: SourceBlock) -> list[tuple[str, str]]:
    if block.kind in {"code", "table_header"} or _METADATA.search(block.section or ""):
        return []
    declarations = []
    for line in block.text.splitlines():
        match = _ID_START.match(line)
        if match:
            declarations.append((match["id"], line))
    return declarations


def _content(block: SourceBlock) -> bool:
    return (
        block.kind not in {"heading", "table_header", "code"}
        and not _METADATA.search(block.section or "")
        and not _PLACEHOLDER.fullmatch(block.text.strip())
    )


def seed_requirements(blocks: Sequence[SourceBlock]) -> list[dict]:
    seeds = []
    for block in blocks:
        if not _content(block):
            continue
        section = block.section or ""
        declarations = original_ids(block)
        if declarations:
            pairs = declarations if len(declarations) > 1 else [(declarations[0][0], block.text)]
        elif (
            _NORMATIVE.search(block.text) or _REQUIREMENT_SECTION.search(section) or _HTTP.search(block.text)
        ):
            pairs = [(None, block.text)]
        else:
            continue
        kind = next((kind for pattern, kind in _ROLE_SECTION if pattern.search(section)), "functional")
        for original_id, quote in pairs:
            summary = re.sub(r"\s+", " ", quote).strip()
            seeds.append(
                {
                    "original_id": original_id,
                    "summary": summary[:237] + "…" if len(summary) > 240 else summary,
                    "kind": kind,
                    "evidence": [_quote(block, quote)],
                    "relationships": list(dict.fromkeys(match["id"] for match in _REFERENCE.finditer(quote))),
                    "uncertainty": "Извлечение по структуре и формальным признакам.",
                }
            )
    return seeds


def _quote(block: SourceBlock, text: str | None = None) -> dict:
    return {
        "document_id": block.location.document_id,
        "block_id": block.block_id,
        "kind": "quote",
        "quote": text if text is not None else block.text,
    }


def _absence(block: SourceBlock, scope: str | None = None) -> dict:
    return {
        "document_id": block.location.document_id,
        "block_id": block.block_id,
        "kind": "absence",
        "scope": scope or block.section or block.block_id,
        "quote": None,
    }


def _candidate(
    kind: str,
    title: str,
    explanation: str,
    severity: str,
    evidence: list[dict],
    impact: str,
    correction: str,
    *,
    status: str = "confirmed",
    scope: str = "individual",
    criterion: str = "completeness",
    scenario: str | None = None,
) -> dict:
    return {
        "kind": kind,
        "title": title,
        "description": explanation,
        "severity": severity,
        "status": status,
        "evidence": evidence,
        "impact": impact,
        "recommendation": correction,
        "uncertainty": "Требуется уточнение контекста." if status != "confirmed" else "Формальная проверка.",
        "criterion": criterion,
        "requirement_ids": [],
        "scope": scope,
        "conflict_scenario": scenario,
    }


def _id_rules(document: SourceDocument, requirements: Sequence[Requirement]) -> list[dict]:
    output = []
    by_id: dict[str, list[tuple[SourceBlock, str]]] = defaultdict(list)
    for block in document.blocks:
        for original_id, quote in original_ids(block):
            by_id[original_id.upper().replace("–", "-")].append((block, quote))
    for original_id, declarations in by_id.items():
        if len(declarations) > 1:
            output.append(
                _candidate(
                    "duplicate_id",
                    f"Повторяется идентификатор {original_id}",
                    f"Идентификатор {original_id} присвоен нескольким формулировкам в одном документе.",
                    "minor",
                    [_quote(block, quote) for block, quote in declarations],
                    "Ссылки и тесты невозможно однозначно сопоставить с требованием.",
                    "Присвоить формулировкам разные идентификаторы и обновить ссылки.",
                    scope="global",
                    criterion="traceability",
                )
            )
    id_policy = next((b for b in document.blocks if _REQUIRED_ID.search(b.text)), None)
    acceptance_policy = next((b for b in document.blocks if _REQUIRED_ACCEPTANCE.search(b.text)), None)
    acceptances = [b for b in document.blocks if _ACCEPTANCE.search(b.section or "")]
    blocks = {block.block_id: block for block in document.blocks}
    for req in requirements:
        if req.document_id != document.document_id or req.kind == "acceptance":
            continue
        if req.kind not in {"functional", "business_rule"}:
            continue
        anchor = blocks[req.evidence[0].location.block_id]
        if id_policy and not req.original_id and anchor != id_policy:
            output.append(
                _candidate(
                    "missing_id",
                    "У требования отсутствует идентификатор",
                    "Спецификация требует идентификатор у каждого требования. У этой формулировки он не распознан.",
                    "minor",
                    [_quote(id_policy), _absence(anchor, anchor.block_id)],
                    "Труднее поддерживать связь с тестами и связанными требованиями.",
                    "Присвоить формулировке уникальный идентификатор.",
                    status="requires_clarification",
                    criterion="traceability",
                )
            )
        if (
            acceptance_policy
            and req.original_id
            and anchor != acceptance_policy
            and not any(
                re.search(rf"(?<!\w){re.escape(req.original_id)}(?![\w-])", item.text, re.I)
                for item in acceptances
            )
        ):
            output.append(
                _candidate(
                    "missing_acceptance_coverage",
                    f"Не видна связь с критериями приёмки для {req.original_id}",
                    "Документ требует критериев приёмки для каждого требования. В разделах приёмки не найден явный идентификатор этой формулировки.",
                    "minor",
                    [
                        _quote(acceptance_policy),
                        _quote(anchor),
                        _absence(acceptances[0] if acceptances else anchor, document.document_id),
                    ],
                    "Может отсутствовать проверяемое условие сдачи.",
                    "Добавить критерий приёмки и связать его с идентификатором требования.",
                    status="requires_clarification",
                    scope="global",
                    criterion="verifiability",
                )
            )
    return output


def _table_fields(text: str) -> list[str]:
    return [re.sub(r"[\x60*]", "", part.strip()) for part in re.split(r"(?<!\\)\|", text.strip().strip("|"))]


def _field_rules(blocks: Sequence[SourceBlock]) -> list[dict]:
    output = []
    header: list[str] = []
    for block in blocks:
        if block.kind == "table_header":
            header = [part.casefold() for part in _table_fields(block.text.splitlines()[0])]
            continue
        if block.kind == "table_row" and len(header) >= 3:
            fields = _table_fields(block.text)
            if len(fields) != len(header) or not fields[0]:
                continue
            mandatory = [
                index
                for index, field in enumerate(header)
                if field in {"mandatory", "required", "обязательность", "обязательно"}
            ]
            columns = {"format", "type", "description", "logic", "формат", "тип", "описание"}
            empty = [
                label
                for label, value in zip(header, fields)
                if label in columns and value.casefold() in _FILL_EMPTY
            ]
            if empty and mandatory and fields[mandatory[0]].casefold() in {"да", "yes", "true", "required"}:
                output.append(
                    _candidate(
                        "missing_mandatory_field",
                        f"Неполное описание обязательного поля {fields[0]}",
                        f"Для обязательного поля не заполнено: {', '.join(empty)}.",
                        "minor",
                        [_quote(block), _absence(block, block.block_id)],
                        "Разработчики и тестировщики могут по-разному понять контракт.",
                        "Заполнить пропуски в таблице или явно определить неприменимые столбцы.",
                        status="requires_clarification",
                    )
                )
        if block.kind not in {"heading", "table_header", "code"} and not _METADATA.search(
            block.section or ""
        ):
            if match := _PLACEHOLDER.search(block.text):
                output.append(
                    _candidate(
                        "unfilled_placeholder",
                        "В спецификации остался заполнитель",
                        "В указанном фрагменте значение или часть требований отложены на будущее.",
                        "minor",
                        [_quote(block, match[0])],
                        "Команда не получает исходных данных для реализации или проверки этого условия.",
                        "Уточнить значение либо явно исключить пункт из текущего объёма работ.",
                        status="confirmed"
                        if _REQUIREMENT_SECTION.search(block.section or "") or _NORMATIVE.search(block.text)
                        else "requires_clarification",
                    )
                )
    return output


def _api_rules(blocks: Sequence[SourceBlock]) -> list[dict]:
    output = []
    field_types: dict[tuple[str, str], dict[str, tuple[str, SourceBlock]]] = defaultdict(dict)
    for index, block in enumerate(blocks):
        section = block.section or ""
        text = block.text
        http = _HTTP.search(text)
        if (
            http and http[1] == "GET" and block.kind != "code" and not _OPERATION_REFERENCE.search(text)
        ) or _GET_FIELD.search(text):
            named = http[0] if http else "GET"
            neighbors = [block]
            if _GET_FIELD.search(text):
                operation_root = section.rpartition(" › ")[0] or section
                if operation_root:
                    for neighbor in blocks[index + 1 : index + 35]:
                        if not (neighbor.section or "").startswith(f"{operation_root} › "):
                            break
                        method = _HTTP.search(neighbor.text)
                        if (method and method[1] != "GET") or (
                            neighbor.kind == "table_row" and re.search(r"\bREST type\b", neighbor.text, re.I)
                        ):
                            break
                        neighbors.append(neighbor)
                    neighbors.extend(
                        neighbor
                        for neighbor in blocks[max(0, index - 4) : index]
                        if neighbor.section == section
                        and re.search(r"\bDescription\b|описание", neighbor.text, re.I)
                    )
            for service in neighbors:
                mutation = next(
                    (
                        verb
                        for verb in _MUTATION.finditer(service.text)
                        if not _MUTATION_EXCLUSION.search(
                            service.text[max(0, verb.start() - 40) : verb.start()]
                        )
                        and not re.search(r"[?/_]", service.text[max(0, verb.start() - 1) : verb.start()])
                    ),
                    None,
                )
                if mutation:
                    method_quote = _quote(block, named) if service != block else _quote(block)
                    output.append(
                        _candidate(
                            "state_changing_get",
                            "GET описан как операция изменения состояния",
                            "Метод GET и описание действия указывают, что запрос меняет состояние.",
                            "major",
                            [method_quote, _quote(service)] if service != block else [method_quote],
                            "Повторные запросы и механизмы предварительной загрузки могут применить изменение неожиданно.",
                            "Выделить чтение в GET, а изменение состояния описать подходящим несчитывающим методом.",
                            scope="global" if service != block else "individual",
                            criterion="conformance",
                        )
                    )
                    break

        for status in _STATUS_DECLARATION.finditer(text) if block.kind != "code" else ():
            code = int(status["code"] or status["direct"])
            next_text = text[status.end() :].casefold()
            declared = next(
                (
                    name
                    for name in _STATUS_NAME.values()
                    if next_text.startswith(name)
                    and (len(next_text) == len(name) or not next_text[len(name)].isalpha())
                ),
                None,
            )
            expected = _STATUS_NAME.get(code)
            if not declared or not expected or declared == expected:
                continue
            output.append(
                _candidate(
                    "http_status_mismatch",
                    f"Описание не соответствует HTTP {code}",
                    f"Для кода {code} указано «{declared}». Стандартное название этого кода — «{expected}».",
                    "minor",
                    [_quote(block, text[status.start() : status.end() + len(declared)])],
                    "Клиенты API могут трактовать исход операции по-разному.",
                    "Согласовать числовой код, описание и примеры ответа.",
                    criterion="conformance",
                )
            )

        if block.kind == "table_row" and (match := _TYPE.match(text.strip().lstrip("|"))):
            method_root = re.split(
                r"\s+›\s+(?=[^›]*(?:request|response|параметры запроса|ответ))",
                section,
                flags=re.I,
            )[0]
            direction = (
                "response" if _RESPONSE.search(section) else "request" if _REQUEST.search(section) else None
            )
            if direction:
                field_types[(method_root, match["field"])][direction] = (match["type"].lower(), block)

    for (_, field), directions in field_types.items():
        if len(directions) != 2:
            continue
        request_type, request = directions["request"]
        response_type, response = directions["response"]
        if request_type != response_type:
            output.append(
                _candidate(
                    "request_response_mismatch",
                    f"Тип поля {field} различается в запросе и ответе",
                    f"Поле `{field}` описано как `{request_type}` в запросе и как `{response_type}` в ответе.",
                    "minor",
                    [_quote(request), _quote(response)],
                    "Клиенты могут ошибаться при повторном использовании схемы или преобразовании данных.",
                    "Подтвердить и описать преобразование либо унифицировать типы.",
                    status="requires_clarification",
                    scope="global",
                    criterion="consistency",
                )
            )
    return output


def _relation_rules(documents: Sequence[SourceDocument]) -> list[dict]:
    output = []
    declared = {
        identifier.upper().replace("–", "-")
        for document in documents
        for block in document.blocks
        for identifier, _ in original_ids(block)
    }
    endpoints = {
        (match[1].upper(), match[2].rstrip("."))
        for document in documents
        for block in document.blocks
        if block.kind != "code"
        for match in _HTTP.finditer(block.text)
        if not re.search(r"(?:calls?|uses?|via|вызывает|через)\s*$", block.text[: match.start()], re.I)
    }
    for document in documents:
        for block in document.blocks:
            if block.kind in {"heading", "code"} or _METADATA.search(block.section or ""):
                continue
            for match in _REFERENCE.finditer(block.text):
                identifier = match["id"]
                if identifier.upper().replace("–", "-") not in declared:
                    output.append(
                        _candidate(
                            "undefined_reference",
                            f"Не найдено требование {identifier}",
                            f"Ссылка указывает на {identifier}, но такого идентификатора нет в проверенных документах.",
                            "minor",
                            [_quote(block, match[0]), _absence(block, document.document_id)],
                            "Связь между формулировками невозможно проследить по представленному набору.",
                            "Добавить целевую формулировку, предоставить связанный документ или исправить ссылку.",
                            scope="global",
                            criterion="traceability",
                        )
                    )
            for match in _OPERATION_REFERENCE.finditer(block.text):
                method, path = match[1].upper(), match[2].rstrip(".")
                if (method, path) not in endpoints:
                    output.append(
                        _candidate(
                            "missing_api_operation",
                            f"Не найден контракт операции {method} {path}",
                            "В документе есть ссылка на операцию, но в проверенных спецификациях не найдено её отдельное описание.",
                            "major",
                            [_quote(block, match[0]), _absence(block, document.document_id)],
                            "Команды могут по-разному реализовать взаимодействие или обработку отказов.",
                            "Добавить контракт операции либо приложить документ с её действующим описанием.",
                            status="requires_clarification",
                            scope="global",
                        )
                    )
    return output


def _unit(raw: str | None) -> tuple[str, Decimal]:
    value = (raw or "").casefold()
    for prefix, key in (("секунд", "second"), ("минут", "minute"), ("час", "hour")):
        if value.startswith(prefix):
            value = key
    return _UNITS.get(value, _UNITS.get(value.rstrip("s"), (value, Decimal(1))))


def _matching_bound_context(
    lower: SourceBlock,
    upper: SourceBlock,
    documents: dict[str, list[SourceBlock]],
) -> bool:
    """Confirm bounds across sources only if the rest of both specifications agrees."""
    if lower.section != upper.section:
        return False
    if lower.location.document_id == upper.location.document_id:
        return True
    if not lower.section:
        return False

    def declaration(block: SourceBlock) -> str | None:
        line = _ID_START.sub("", block.text, count=1).lstrip(" .:*—–)")
        match = _BOUND_INLINE.match(line) or _BOUND_HEAD.match(line)
        if not match:
            return None
        # Preserve each unit, trailing condition and any other text outside the bound.
        start = match.start("bound")
        end = match.end("number")
        # Prefix-form bounds put the subject between the operator and the number.
        return (line[:start] + line[match.end("bound") : match.start("number")] + line[end:]).strip()

    left = declaration(lower)
    if left is None or left != declaration(upper):
        return False
    lower_doc = documents[lower.location.document_id]
    upper_doc = documents[upper.location.document_id]
    return len(lower_doc) == len(upper_doc) and all(
        (a is lower and b is upper) or (a.kind == b.kind and a.text == b.text)
        for a, b in zip(lower_doc, upper_doc, strict=True)
    )


def _bound_rules(blocks: Sequence[SourceBlock]) -> list[dict]:
    bounds: dict[str, dict[str, list[tuple[Decimal, str, SourceBlock, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    output = []
    documents: dict[str, list[SourceBlock]] = defaultdict(list)
    for block in blocks:
        documents[block.location.document_id].append(block)
        if not _content(block):
            continue
        clauses = []
        for line in block.text.splitlines():
            declaration = _ID_START.match(line)
            if declaration:
                line = line[declaration.end() :].lstrip(" .:*—–)")
            clauses.append(line)
        for pattern in (_BOUND_HEAD, _BOUND_INLINE):
            for line in clauses:
                for match in pattern.finditer(line):
                    subject = re.sub(r"\s+", " ", match["subject"].strip().casefold())
                    if subject.startswith(("the ", "a ")):
                        subject = subject.split(" ", 1)[1]
                    number = Decimal(re.sub(r"\s", "", match["number"]).replace(",", "."))
                    unit, ratio = _unit(match["unit"])
                    side = "lower" if match["bound"].casefold() in _LOWER_BOUNDS else "upper"
                    bounds[subject][side].append((number * ratio, unit, block, match[0].strip()))
    for subject, sides in bounds.items():
        if "lower" not in sides or "upper" not in sides:
            continue
        by_unit: dict[str, dict[str, tuple[Decimal, str, SourceBlock, str]]] = defaultdict(dict)
        for side, entries in sides.items():
            for item in entries:
                value, unit, _, _ = item
                previous = by_unit[unit].get(side)
                if not previous or (value > previous[0] if side == "lower" else value < previous[0]):
                    by_unit[unit][side] = item
        for by_side in by_unit.values():
            if len(by_side) != 2 or by_side["lower"][0] <= by_side["upper"][0]:
                continue
            _, _, lower, lower_quote = by_side["lower"]
            _, _, upper, upper_quote = by_side["upper"]
            explanation = f"У показателя «{subject}» минимальное значение больше максимального."
            same_scope = _matching_bound_context(lower, upper, documents)
            output.append(
                _candidate(
                    "contradiction",
                    "Несовместимые нижняя и верхняя границы",
                    explanation,
                    "major",
                    [_quote(lower, lower_quote), _quote(upper, upper_quote)],
                    "Входные данные не могут одновременно удовлетворить обеим границам.",
                    "Уточнить применимость и привести границы к одному допустимому диапазону.",
                    status="confirmed" if same_scope else "requires_clarification",
                    scope="global",
                    criterion="consistency",
                    scenario=explanation,
                )
            )
        lower_bound = sides["lower"][0]
        upper_bound = sides["upper"][0]
        if len(by_unit) > 1 and lower_bound[1] != upper_bound[1]:
            _, _, lower, lower_quote = lower_bound
            _, _, upper, upper_quote = upper_bound
            output.append(
                _candidate(
                    "inconsistent_unit",
                    "Границы указаны в несопоставимых единицах",
                    f"Для показателя «{subject}» нижняя и верхняя границы используют разные единицы или масштаб не указан.",
                    "minor",
                    [_quote(lower, lower_quote), _quote(upper, upper_quote)],
                    "Границы нельзя однозначно сравнить при проверке входных данных.",
                    "Уточнить единицы и добавить правило преобразования, если оно предусмотрено.",
                    status="requires_clarification",
                    scope="global",
                    criterion="consistency",
                )
            )
    return output


def deterministic_candidates(
    documents: Sequence[SourceDocument],
    requirements: Sequence[Requirement],
) -> list[dict]:
    output = []
    for document in documents:
        output.extend(_id_rules(document, requirements))
        output.extend(_field_rules(document.blocks))
        output.extend(_api_rules(document.blocks))
    output.extend(_relation_rules(documents))
    output.extend(_bound_rules([block for document in documents for block in document.blocks]))
    return output
