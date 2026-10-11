from __future__ import annotations

import logging
import re
import sys

_SECRET_TOKENS = ("api_key", "apikey", "password", "passwd", "secret", "token", "authorization")

_SECRET_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|password|passwd|secret|token|authorization)\b\s*[:=]\s*([\"']?)([^\s\"',;}]+)\2"
)


def redact_text(message: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        return f"{match.group(1)}=***"

    return _SECRET_PATTERN.sub(_replace, message)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - logging must never fail
            return True
        if any(token in message.lower() for token in _SECRET_TOKENS):
            redacted = redact_text(message)
            record.msg = redacted
            record.args = ()
        return True


def configure_logging(level: str = "INFO") -> logging.Logger:
    root = logging.getLogger()
    root.handlers.clear()
    fmt = "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)
    root.setLevel(level.upper())
    root.addFilter(RedactingFilter())
    return logging.getLogger("app")
