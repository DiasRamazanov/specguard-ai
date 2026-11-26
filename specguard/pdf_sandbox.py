"""Parse PDFs in a short-lived child with an independent memory and time budget."""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MAX_RSS = 384 * 1024 * 1024
MAX_OUTPUT = 16 * 1024 * 1024
WALL_SECONDS = 15


def _worker(filename):
    import resource

    # The process-forking HTTP server can have multiple threads. Set limits here,
    # after exec, before loading the native document library.
    resource.setrlimit(resource.RLIMIT_CPU, (10, 11))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT, MAX_OUTPUT))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (MAX_RSS * 2, MAX_RSS * 2))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from specguard.ingest import MAX_UPLOAD_BYTES, DocumentError, _ingest_document_in_process

    try:
        document = _ingest_document_in_process(filename, sys.stdin.buffer.read(MAX_UPLOAD_BYTES + 1))
    except DocumentError as exc:
        sys.stdout.buffer.write(str(exc).encode("utf-8")[:2048])
        return 2
    sys.stdout.buffer.write(document.model_dump_json().encode("utf-8"))
    return 0


def ingest_pdf(filename, data):
    import psutil
    from pydantic import ValidationError

    from .ingest import DocumentError
    from .models import SourceDocument

    if sys.platform != "darwin" and not sys.platform.startswith("linux"):
        raise DocumentError("Для защищённого разбора PDF запустите SpecGuard в Linux или macOS.")
    with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as output:
        source.write(data)
        source.seek(0)
        # Supply no provider credentials or session identifiers to the parser.
        with subprocess.Popen(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()), filename],
            env={"PATH": os.defpath, "LC_ALL": "C"},
            stdin=source,
            stdout=output,
            stderr=subprocess.DEVNULL,
        ) as proc:
            deadline = time.monotonic() + WALL_SECONDS
            try:
                child = psutil.Process(proc.pid)
                while proc.poll() is None:
                    if time.monotonic() >= deadline or child.memory_info().rss > MAX_RSS:
                        raise DocumentError("Разбор PDF превысил лимит времени или памяти.")
                    try:
                        proc.wait(timeout=0.05)
                    except subprocess.TimeoutExpired:
                        continue
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                raise DocumentError("Контроль ресурсов PDF-процесса недоступен.") from None
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
        output.seek(0)
        if proc.returncode == 2:
            msg = output.read(2048).decode("utf-8", errors="replace")
            raise DocumentError(msg or "Ошибка чтения PDF.")
        if proc.returncode != 0:
            raise DocumentError("Изолированный процесс не смог обработать PDF.")
        payload = output.read(MAX_OUTPUT + 1)
        if len(payload) > MAX_OUTPUT:
            raise DocumentError("Извлечённый документ слишком велик.")
        try:
            return SourceDocument.model_validate_json(payload)
        except ValidationError:
            raise DocumentError("Некорректный результат чтения PDF.") from None


if __name__ == "__main__":
    raise SystemExit(_worker(sys.argv[1]))
