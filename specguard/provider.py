"""Bounded DeepSeek HTTP transport and process-shared, durable quota reservations."""

import json
import os
import socket
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class IntelligenceError(ValueError):
    """Fixed safe error code. Never contains payloads, HTTP bodies or credentials."""

    def __init__(self, code, retryable=False, retry_after=0):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.retry_after = retry_after


def setting(name, default, minimum, maximum):
    try:
        value = int(os.environ.get(name, default))
    except ValueError:
        raise IntelligenceError("invalid_provider_settings") from None
    if not minimum <= value <= maximum:
        raise IntelligenceError("invalid_provider_settings")
    return value


class Budget:
    """Reserve pessimistically before sending. Unknown usage stays fully charged.

    One ledger covers all CLI processes and API workers sharing the same DB path.
    Active leases bound concurrency; expired leases release capacity, never cost.
    """

    def __init__(self, path, run_limit, global_limit, concurrency):
        self.path = Path(path).expanduser()
        self.run_limit = run_limit
        self.global_limit = global_limit
        self.concurrency = concurrency
        self.used = 0
        self.lock = threading.Lock()

    def reserve(self, tokens):
        with self.lock:
            if self.used + tokens > self.run_limit:
                raise IntelligenceError("run_token_budget_exceeded")
            lease = uuid.uuid4().hex
            try:
                self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with closing(sqlite3.connect(str(self.path), timeout=3)) as db, db:
                    db.execute("BEGIN IMMEDIATE")
                    db.execute(
                        "CREATE TABLE IF NOT EXISTS quota (id INTEGER PRIMARY KEY, used INTEGER NOT NULL)"
                    )
                    db.execute(
                        "CREATE TABLE IF NOT EXISTS leases (id TEXT PRIMARY KEY, expires REAL NOT NULL)"
                    )
                    db.execute("INSERT OR IGNORE INTO quota VALUES (1, 0)")
                    now = time.time()
                    db.execute("DELETE FROM leases WHERE expires <= ?", (now,))
                    used = db.execute("SELECT used FROM quota WHERE id=1").fetchone()[0]
                    if used + tokens > self.global_limit:
                        raise IntelligenceError("global_token_budget_exceeded")
                    if db.execute("SELECT COUNT(*) FROM leases").fetchone()[0] >= self.concurrency:
                        raise IntelligenceError("provider_busy")
                    db.execute("UPDATE quota SET used=used+? WHERE id=1", (tokens,))
                    db.execute("INSERT INTO leases VALUES (?,?)", (lease, now + 600))
            except (OSError, sqlite3.Error):
                raise IntelligenceError("budget_storage_unavailable") from None
            self.used += tokens
            return lease

    def settle(self, lease, reserved, actual):
        # On unreadable responses, even a timeout, the provider may have billed the request.
        delta = 0 if actual is None else actual - reserved
        with self.lock:
            try:
                with closing(sqlite3.connect(str(self.path), timeout=3)) as db, db:
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("DELETE FROM leases WHERE id=?", (lease,))
                    db.execute("UPDATE quota SET used=used+? WHERE id=1", (delta,))
            except sqlite3.Error:
                raise IntelligenceError("budget_storage_unavailable") from None
            self.used += delta


def rate_limit_delay(header):
    """Honor numeric and HTTP-date Retry-After. Long waits end the current operation."""
    if header is None:
        return 0
    try:
        if header.isdecimal():
            return int(header)
        return max(0, parsedate_to_datetime(header).timestamp() - time.time())
    except (ValueError, TypeError, OverflowError):
        return 0


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def json_object(raw):
    def unique_keys(pairs):
        parsed = dict(pairs)
        if len(parsed) != len(pairs):
            raise ValueError("duplicate_key")
        return parsed

    def invalid_constant(_value):
        raise ValueError("invalid_number")

    try:
        parsed = json.loads(raw, object_pairs_hook=unique_keys, parse_constant=invalid_constant)
        if not isinstance(parsed, dict):
            raise TypeError("invalid_object")
        return parsed
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise IntelligenceError("malformed_json", retryable=True) from None


def usage_from(reply):
    usage = reply.get("usage")
    if not isinstance(usage, dict):
        raise IntelligenceError("invalid_usage")
    prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
    details = usage.get("completion_tokens_details") or {}
    if not isinstance(details, dict):
        raise IntelligenceError("invalid_usage")
    reasoning = details.get("reasoning_tokens")
    if any(type(v) is not int or v < 0 for v in (prompt, completion)):
        raise IntelligenceError("invalid_usage")
    if reasoning is not None and (type(reasoning) is not int or not 0 <= reasoning <= completion):
        raise IntelligenceError("invalid_usage")
    if "total_tokens" in usage and usage["total_tokens"] != prompt + completion:
        raise IntelligenceError("invalid_usage")
    return {"input_tokens": prompt, "output_tokens": completion, "reasoning_tokens": reasoning}


class DeepSeek:
    def __init__(self, live=False):
        if live is not True or os.environ.get("SPECGUARD_LIVE") != "1":
            raise IntelligenceError("live_processing_disabled")
        self._key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not self._key:
            raise IntelligenceError("missing_api_key")
        if any(not 33 <= ord(c) <= 126 for c in self._key):
            raise IntelligenceError("invalid_api_key")
        self.base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        if self.base not in ("https://api.deepseek.com", "https://api.deepseek.com/v1"):
            raise IntelligenceError("unsupported_provider_endpoint")
        self.models = {
            "fast": os.environ.get("DEEPSEEK_FAST_MODEL", "deepseek-flash"),
            "reasoning": os.environ.get("DEEPSEEK_REASONING_MODEL", "deepseek-v4-pro"),
        }
        self.budget = Budget(
            os.environ.get("SPECGUARD_BUDGET_DB", str(Path.home() / ".specguard" / "usage.sqlite3")),
            setting("SPECGUARD_RUN_TOKENS", 1000000, 1, 6000000),
            setting("SPECGUARD_GLOBAL_TOKENS", 6000000, 1, 6000000),
            setting("SPECGUARD_CONCURRENCY", 2, 1, 8),
        )
        self.retries = setting("SPECGUARD_RETRIES", 1, 0, 2)
        self.timeout = setting("SPECGUARD_TIMEOUT_SECONDS", 120, 1, 180)
        self.reasoning_effort = os.environ.get("SPECGUARD_REASONING_EFFORT", "high")
        if self.reasoning_effort not in {"low", "high", "max"}:
            raise IntelligenceError("invalid_provider_settings")
        self.max_calls = setting("SPECGUARD_RUN_CALLS", 64, 1, 128)
        self.records = []
        self._calls = 0
        self._lock = threading.Lock()
        self._available = None

    def _request(self, path, payload=None):
        raw = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.base + path,
            data=raw,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self._key,
            },
        )
        deadline = time.monotonic() + self.timeout
        try:
            with build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                data = bytearray()
                while True:
                    if time.monotonic() > deadline:
                        raise IntelligenceError("provider_timeout", retryable=True)
                    chunk = response.read1(65536)
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > 1048576:
                        raise IntelligenceError("provider_reply_too_large")
            return json_object(data)
        except HTTPError as exc:
            status = exc.code
            retry_after = rate_limit_delay(exc.headers.get("Retry-After")) if exc.headers else 0
            exc.close()
            if status == 429:
                raise IntelligenceError(
                    "provider_rate_limited", retryable=retry_after <= 5, retry_after=retry_after
                ) from None
            if status in (401, 403):
                raise IntelligenceError("provider_access_denied") from None
            if status == 402:
                raise IntelligenceError("provider_balance_insufficient") from None
            raise IntelligenceError("provider_http_error", retryable=status in (500, 502, 503, 504)) from None
        except (TimeoutError, socket.timeout):  # noqa: UP041 -- distinct types on Python 3.9.
            raise IntelligenceError("provider_timeout", retryable=True) from None
        except (URLError, OSError, HTTPException):
            raise IntelligenceError("provider_connection_error", retryable=True) from None

    def _check_model(self, model):
        if self._available is None:
            reply = self._request("/models")
            rows = reply.get("data")
            if not isinstance(rows, list):
                raise IntelligenceError("invalid_model_listing")
            self._available = {r["id"] for r in rows if isinstance(r, dict) and isinstance(r.get("id"), str)}
        if model not in self._available:
            raise IntelligenceError("model_unavailable")

    def verify_audit_models(self):
        """Confirm both configured tiers before beginning an official multi-stage run."""
        for model in self.models.values():
            self._check_model(model)

    def complete(self, role, version, tier, max_input, max_output, messages, verify):
        model = self.models[tier]
        # UTF-8 bytes bound byte-level tokenizer input, plus allowance for chat framing.
        upper_input = 128 + sum(len(m["content"].encode("utf-8")) for m in messages)
        if upper_input > max_input:
            raise IntelligenceError("role_context_limit")
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_output,
            "thinking": {"type": "enabled" if tier == "reasoning" else "disabled"},
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        if tier == "fast":
            body["temperature"] = 0
        else:
            body["reasoning_effort"] = self.reasoning_effort
        reserved = upper_input + max_output
        for attempt in range(1, self.retries + 2):
            with self._lock:
                if self._calls >= self.max_calls:
                    raise IntelligenceError("run_call_limit")
                self._calls += 1
            lease = self.budget.reserve(reserved)
            started = time.monotonic()
            record = {
                "role": role,
                "model": model,
                "prompt_version": version,
                "attempt": attempt,
                "status": "failed",
                "input_tokens": None,
                "output_tokens": None,
                "reasoning_tokens": None,
            }
            actual = 0
            retry_delay = 0
            try:
                self._check_model(model)
                actual = None
                reply = self._request("/chat/completions", body)
                record.update(usage_from(reply))
                actual = record["input_tokens"] + record["output_tokens"]
                if actual > reserved:
                    raise IntelligenceError("provider_usage_exceeds_reservation")
                if reply.get("model") != model:
                    raise IntelligenceError("unexpected_provider_model")
                choices = reply.get("choices")
                if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                    raise IntelligenceError("invalid_provider_response", retryable=True)
                choice = choices[0]
                if choice.get("finish_reason") != "stop":
                    raise IntelligenceError(
                        "incomplete_provider_response", retryable=choice.get("finish_reason") == "length"
                    )
                msg = choice.get("message")
                content = msg.get("content") if isinstance(msg, dict) else None
                if not isinstance(content, str) or not content.strip():
                    raise IntelligenceError("empty_provider_response", retryable=True)
                result = verify(json_object(content))
                record["status"] = "validated"
                return result
            except IntelligenceError as exc:
                record["status"] = exc.code
                if not exc.retryable or attempt > self.retries:
                    raise
                retry_delay = max(2 ** (attempt - 1), exc.retry_after)
            finally:
                record["duration_ms"] = round((time.monotonic() - started) * 1000)
                self.records.append(record)
                self.budget.settle(lease, reserved, actual)
            time.sleep(retry_delay)
        raise IntelligenceError("retry_limit")
