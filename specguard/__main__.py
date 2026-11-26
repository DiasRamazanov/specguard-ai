"""SpecGuard command line."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from .core import AuditError, audit_documents
from .ingest import MAX_UPLOAD_BYTES, DocumentError, ingest_document
from .intelligence import Intelligence, IntelligenceError
from .report import render_json, render_markdown

EXIT_CONFIGURATION = 2
EXIT_INCOMPLETE = 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Статическая проверка требований SpecGuard AI.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "check-provider", help="Проверить доступ к обеим моделям через список моделей DeepSeek."
    )
    validator = commands.add_parser("validate", help="Выполнить аудит PDF, Markdown или TXT.")
    validator.add_argument(
        "--input", type=Path, required=True, action="append", help="Путь к спецификации. Можно повторить."
    )
    validator.add_argument("--output", type=Path, required=True, help="Путь к отчёту .md или .json.")
    validator.add_argument("--json-output", type=Path, help="Дополнительный путь к отчёту JSON.")
    validator.add_argument(
        "--reference-roles",
        action="store_true",
        help="Передавать проверяемые ссылки на источники для индивидуального, критического и риск-анализа.",
    )
    mode = validator.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="Локальные проверки без отправки данных.")
    mode.add_argument(
        "--consent", action="store_true", help="Разрешить передачу текстовых фрагментов в DeepSeek."
    )
    return parser


def _write(path: Path, content: str) -> None:
    temporary = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _output_paths(args: argparse.Namespace) -> list[tuple[Path, str]]:
    suffix = args.output.suffix.lower()
    if suffix not in {".md", ".markdown", ".json"}:
        raise ValueError("Укажите выходной файл .md или .json.")
    output = [(args.output, suffix)]
    if args.json_output is not None:
        if args.json_output.suffix.lower() != ".json":
            raise ValueError("Дополнительный отчёт должен иметь расширение .json.")
        output.append((args.json_output, ".json"))
    paths = {path.resolve() for path, _ in output}
    if len(paths) != len(output) or paths.intersection(path.resolve() for path in args.input):
        raise ValueError("Пути входных файлов и отчётов должны различаться.")
    if any(not path.parent.is_dir() or (path.exists() and not path.is_file()) for path, _ in output):
        raise ValueError("Укажите существующую папку и имя файла для записи отчёта.")
    return output


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "check-provider":
        try:
            Intelligence(live=True).provider.verify_audit_models()
        except IntelligenceError as error:
            print(f"Проверка доступа к DeepSeek не завершена ({error.code}).", file=sys.stderr)
            return EXIT_CONFIGURATION
        print("Обе модели доступны в каталоге DeepSeek. Запросов на генерацию: 0.")
        return 0
    if not args.offline and not args.consent:
        print(
            "Передача текста в DeepSeek требует --consent. Для локальных проверок используйте --offline.",
            file=sys.stderr,
        )
        return EXIT_CONFIGURATION
    try:
        paths = _output_paths(args)
        documents = []
        for path in args.input:
            with path.open("rb") as file:
                documents.append(ingest_document(path.name, file.read(MAX_UPLOAD_BYTES + 1)))
        provider = None if args.offline else Intelligence(live=True, reference_roles=args.reference_roles)
        if provider is not None:
            provider.provider.verify_audit_models()
        result = audit_documents(documents, provider)
        for path, suffix in paths:
            _write(path, render_json(result) if suffix == ".json" else render_markdown(result))
    except IntelligenceError as error:
        print(f"Не удалось настроить модель ({error.code}). Проверьте параметры DeepSeek.", file=sys.stderr)
        return EXIT_CONFIGURATION
    except (DocumentError, AuditError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return EXIT_CONFIGURATION
    except OSError:
        print("Не удалось прочитать входные файлы или записать отчёт.", file=sys.stderr)
        return EXIT_CONFIGURATION

    if result.mode == "live" and not result.coverage.complete:
        print("Отчёт записан. Семантическая проверка не завершена.", file=sys.stderr)
        return EXIT_INCOMPLETE
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
