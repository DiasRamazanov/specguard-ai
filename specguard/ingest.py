"""Bounded parsing of uploaded document bytes into verifiable source blocks."""

import re
from bisect import bisect_right
from hashlib import sha256
from pathlib import PurePath
from statistics import median
from typing import List, Optional, Tuple

from .models import SourceBlock, SourceDocument, SourceLocation

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 500_000
MAX_TEXT_LINES = 50_000
MAX_SECTION_CHARS = 560
MAX_PDF_PAGES = 100
MAX_PDF_OBJECTS = 100_000
MAX_BLOCK_CHARS = 2_400
MAX_BLOCKS = 3_000
SUPPORTED_EXTENSIONS = {".md": "markdown", ".markdown": "markdown", ".pdf": "pdf", ".txt": "text"}

ATX = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)\s*$")
SETEXT = re.compile(r"^ {0,3}(=+|-+)\s*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
LIST_ITEM = re.compile(r"^\s{0,8}(?:[-+*]|\d{1,4}[.)])\s+\S")
TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{2,}:?(?:\s*\|\s*:?-{2,}:?)+\s*\|?\s*$")
THEMATIC_BREAK = re.compile(r"^\s{0,3}(?:(?:-[ \t]*){3,}|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,})$")
PDF_NUMBERED_HEADING = re.compile(r"^(?P<number>\d+(?:\.\d+)*)(?:[.)])?\s+[A-ZА-ЯЁ]")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class DocumentError(ValueError):
    """The source cannot be safely parsed within the supported limits."""


def _filename(name: str) -> str:
    clean = PurePath(name.replace("\\", "/")).name
    clean = "".join(char for char in clean if char.isprintable()).strip()
    suffix = PurePath(clean).suffix
    if suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise DocumentError("Поддерживаются файлы PDF, Markdown и TXT.")
    return clean[: 180 - len(suffix)] + suffix if len(clean) > 180 else clean


def _ranges(start: int, end: int, text: str):
    while end - start > MAX_BLOCK_CHARS:
        boundary = text.rfind("\n", start + 1, start + MAX_BLOCK_CHARS + 1)
        if boundary <= start:
            boundary = text.rfind(" ", start + 1, start + MAX_BLOCK_CHARS + 1)
        stop = boundary + 1 if boundary > start else start + MAX_BLOCK_CHARS
        yield start, stop
        start = stop
    if start < end:
        yield start, end


def _set_heading(headings: List[str], level: int, title: str) -> None:
    headings[level - 1 :] = (
        [title] if level <= len(headings) + 1 else ([""] * (level - len(headings) - 1) + [title])
    )


def _section(headings: List[str], warnings: List[str]) -> Optional[str]:
    section = " › ".join(heading for heading in headings if heading)
    if len(section) > MAX_SECTION_CHARS:
        warning = "Сокращены слишком длинные пути разделов. Полные заголовки сохранены в источнике."
        if warning not in warnings:
            warnings.append(warning)
        section = section[: MAX_SECTION_CHARS - 1] + "…"
    return section or None


def _markdown(
    text: str,
    document_id: str,
    markdown: bool,
    warnings: List[str],
) -> List[SourceBlock]:
    line_count = sum(text.count(marker) for marker in ("\n", "\r", "\x85", "\u2028", "\u2029"))
    if line_count - text.count("\r\n") >= MAX_TEXT_LINES:
        raise DocumentError("Текстовый документ содержит слишком много строк.")
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    blocks: List[SourceBlock] = []
    headings: List[str] = []
    pending: Optional[int] = None
    pending_kind = "paragraph"
    fence: Optional[str] = None
    in_table = False

    def add(first: int, last: int, kind: str) -> None:
        start, end = offsets[first], offsets[last]
        end = start + len(text[start:end].rstrip("\r\n"))
        for left, right in _ranges(start, end, text):
            if not text[left:right].strip():
                continue
            line_start = bisect_right(offsets, left)
            line_end = bisect_right(offsets, right - 1)
            block_id = f"l{line_start}-{line_end}-{left}"
            location = SourceLocation(
                document_id=document_id,
                block_id=block_id,
                section=_section(headings, warnings),
                line_start=line_start,
                line_end=line_end,
                char_start=left,
                char_end=right,
            )
            if len(blocks) >= MAX_BLOCKS:
                raise DocumentError("Документ содержит слишком много текстовых блоков.")
            blocks.append(SourceBlock(block_id=block_id, text=text[left:right], kind=kind, location=location))

    def flush(last: int) -> None:
        nonlocal pending
        if pending is not None:
            add(pending, last, pending_kind)
            pending = None

    index = 0
    while index < len(lines):
        line = lines[index].rstrip("\r\n")
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        fence_match = FENCE.match(line) if markdown else None
        if fence:
            if (
                fence_match
                and fence_match[1][0] == fence[0]
                and len(fence_match[1]) >= len(fence)
                and not line[fence_match.end() :].strip()
            ):
                flush(index + 1)
                fence = None
            index += 1
            continue
        if fence_match:
            flush(index)
            in_table = False
            fence = fence_match[1]
            pending, pending_kind = index, "code"
            index += 1
            continue

        heading = ATX.match(line) if markdown else None
        setext = SETEXT.match(next_line) if markdown and line.strip() and pending is None else None
        if setext and (LIST_ITEM.match(line) or "|" in line or THEMATIC_BREAK.match(line)):
            setext = None
        if heading or setext:
            flush(index)
            in_table = False
            if heading:
                title = re.sub(r"\s+#+\s*$", "", heading[2]).strip()
                _set_heading(headings, len(heading[1]), title)
                add(index, index + 1, "heading")
                index += 1
            else:
                _set_heading(headings, 1 if setext[1].startswith("=") else 2, line.strip())
                add(index, index + 2, "heading")
                index += 2
            continue

        if markdown and "|" in line and TABLE_SEPARATOR.match(next_line):
            flush(index)
            in_table = True
            add(index, index + 2, "table_header")
            index += 2
            continue
        if in_table and "|" in line:
            add(index, index + 1, "table_row")
            index += 1
            continue
        in_table = False

        if not line.strip() or (markdown and THEMATIC_BREAK.match(line)):
            flush(index)
        elif LIST_ITEM.match(line):
            flush(index)
            pending, pending_kind = index, "list_item"
        elif pending is None:
            pending, pending_kind = index, "paragraph"
        elif pending_kind == "list_item" and not line.startswith((" ", "\t")):
            flush(index)
            pending, pending_kind = index, "paragraph"
        index += 1
    flush(len(lines))
    return blocks


def _pdf(data: bytes, document_id: str) -> Tuple[str, List[SourceBlock], int, List[str]]:
    import pymupdf

    blocks: List[SourceBlock] = []
    chunks: List[str] = []
    warnings: List[str] = []
    headings: List[str] = []
    offset = 0
    unreadable: List[int] = []
    replacement_pages: List[int] = []
    image_pages: List[int] = []
    try:
        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.needs_pass:
                raise DocumentError("PDF защищён паролем.")
            if not 0 < document.page_count <= MAX_PDF_PAGES:
                raise DocumentError(f"В PDF должно быть от 1 до {MAX_PDF_PAGES} страниц.")
            if document.xref_length() > MAX_PDF_OBJECTS:
                raise DocumentError("Структура PDF превышает допустимый размер.")
            if document.is_repaired:
                warnings.append("Внутренняя структура PDF была повреждена и восстановлена при чтении.")
            if document.embfile_count():
                warnings.append("Файлы, вложенные внутрь PDF, не анализировались.")
            page_count = document.page_count
            outline = {
                (page, title.casefold()): level for level, title, page in document.get_toc() if page > 0
            }
            for page_number, page in enumerate(document, 1):
                page_data = page.get_text(
                    "dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES, sort=True
                )
                native_blocks = page_data.get("blocks", [])
                sizes = [
                    (span["size"], len(span["text"].strip()))
                    for native in native_blocks
                    for line in native.get("lines", [])
                    for span in line["spans"]
                    if span["text"].strip()
                ]
                body_size = (
                    median(size for size, length in sizes if length >= 24)
                    if any(length >= 24 for _, length in sizes)
                    else median(size for size, _ in sizes)
                    if sizes
                    else 0
                )
                page_has_text = False
                for index, native in enumerate(native_blocks, 1):
                    lines = [
                        "".join(span["text"] for span in line["spans"]) for line in native.get("lines", [])
                    ]
                    value = "\n".join(lines).strip("\n")
                    if not value.strip():
                        continue
                    page_has_text |= bool(value.strip().replace("\ufffd", "").strip())
                    if "\ufffd" in value and page_number not in replacement_pages:
                        replacement_pages.append(page_number)
                    if offset + len(value) > MAX_TEXT_CHARS:
                        raise DocumentError("Извлечённый текст PDF превышает допустимый размер.")
                    kind = "paragraph"
                    if len(lines) == 1 and len(value) <= 140:
                        named_level = outline.get((page_number, value.strip().casefold()))
                        font_size = max(span["size"] for span in native["lines"][0]["spans"])
                        if named_level or (body_size and font_size >= body_size * 1.25):
                            numbered = PDF_NUMBERED_HEADING.match(value.strip())
                            inferred_level = 1 + numbered["number"].count(".") if numbered else 1
                            _set_heading(headings, min(named_level or inferred_level, 6), value.strip())
                            kind = "heading"
                    for left, right in _ranges(0, len(value), value):
                        if not value[left:right].strip():
                            continue
                        block_id = f"p{page_number}-b{index}-{left}"
                        location = SourceLocation(
                            document_id=document_id,
                            block_id=block_id,
                            section=_section(headings, warnings),
                            page=page_number,
                            char_start=offset + left,
                            char_end=offset + right,
                            bbox=tuple(native["bbox"]),
                        )
                        blocks.append(
                            SourceBlock(
                                block_id=block_id, text=value[left:right], kind=kind, location=location
                            )
                        )
                    if len(blocks) > MAX_BLOCKS:
                        raise DocumentError("PDF содержит слишком много текстовых блоков.")
                    chunks.append(value)
                    offset += len(value) + 2
                if not page_has_text:
                    unreadable.append(page_number)
                elif any(
                    pymupdf.Rect(info["bbox"]).get_area() > page.rect.get_area() * 0.45
                    for info in page.get_image_info()
                ):
                    image_pages.append(page_number)
    except (RuntimeError, ValueError, OSError) as error:
        if isinstance(error, DocumentError):
            raise
        raise DocumentError("Не удалось прочитать структуру PDF.") from error

    if len(unreadable) == page_count:
        raise DocumentError("PDF не содержит читаемого текстового слоя. Требуется текстовый PDF.")
    for pages, explanation in (
        (unreadable, "нет читаемого текстового слоя"),
        (replacement_pages, "некоторые символы не распознаны"),
        (image_pages, "крупные изображения не распознавались"),
    ):
        if pages:
            page_list = ", ".join(map(str, pages))
            warnings.append(f"Страницы {page_list}: {explanation}.")
    return "\n\n".join(chunks), blocks, page_count, warnings


def _validate_input(filename: str, data: bytes) -> str:
    name = _filename(filename)
    if not data:
        raise DocumentError("Файл пуст.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise DocumentError(f"Файл превышает ограничение {MAX_UPLOAD_BYTES // 1024**2} МБ.")
    if name.casefold().endswith(".pdf") and b"%PDF-" not in data[:1024]:
        raise DocumentError("Содержимое файла не соответствует формату PDF.")
    return name


def ingest_document(filename: str, data: bytes) -> SourceDocument:
    """Read a PDF or UTF-8 specification without following links or executing content."""
    name = _validate_input(filename, data)
    if name.casefold().endswith(".pdf"):
        from .pdf_sandbox import ingest_pdf

        return ingest_pdf(name, data)
    return _ingest_document_in_process(name, data)


def _ingest_document_in_process(filename: str, data: bytes) -> SourceDocument:
    """Parse validated bytes directly, inside the bounded worker for PDF."""
    name = _validate_input(filename, data)
    digest = sha256(data).hexdigest()
    document_id = f"doc-{digest[:24]}"
    format_name = SUPPORTED_EXTENSIONS[PurePath(name).suffix.lower()]
    page_count: Optional[int] = None
    warnings: List[str] = []

    if format_name == "pdf":
        original, blocks, page_count, warnings = _pdf(data, document_id)
    else:
        try:
            original = data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise DocumentError("Текстовый файл должен быть в кодировке UTF-8.") from error
        if CONTROL_CHARS.search(original):
            raise DocumentError("Файл содержит двоичные или неподдерживаемые управляющие символы.")
        if len(original) > MAX_TEXT_CHARS:
            raise DocumentError("Текст документа превышает допустимый размер.")
        blocks = _markdown(original, document_id, format_name == "markdown", warnings)
    if not blocks:
        raise DocumentError("В документе нет читаемого текста.")
    if len(blocks) > MAX_BLOCKS:
        raise DocumentError("Документ содержит слишком много текстовых блоков.")
    return SourceDocument(
        document_id=document_id,
        filename=name,
        format=format_name,
        sha256=digest,
        size_bytes=len(data),
        page_count=page_count,
        warnings=warnings,
        original_text=original,
        blocks=blocks,
    )
