"""Export frontend contracts from the same models used by the API."""
import json
from pathlib import Path

from specguard.api import app
from specguard.http_models import Attachment, CopilotRequest, CopilotResponse, ErrorResponse, Event
from specguard.models import AuditResult, Evidence, Finding, Requirement

ROOT = Path(__file__).resolve().parents[1] / "contracts"


def write(name, content):
    (ROOT / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    ROOT.mkdir(exist_ok=True)
    write("openapi.json", app.openapi())
    for cls in (AuditResult, Evidence, Finding, Requirement, Attachment, CopilotRequest,
                CopilotResponse, ErrorResponse, Event):
        write(cls.__name__ + ".schema.json", cls.model_json_schema())


if __name__ == "__main__":
    main()
