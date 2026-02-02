"""
Logging setup with structured messages and secret redaction.

Use this module to configure logging for the application. Secrets (client_id,
client_secret, tokens, etc.) are redacted from log records.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

# Keys and patterns whose values should be redacted in log messages
REDACT_KEYS = frozenset(
    {
        "client_id",
        "client_secret",
        "token",
        "access_token",
        "authorization",
        "password",
        "secret",
        "api_key",
    }
)
REDACT_PLACEHOLDER = "***REDACTED***"


def redact_secrets(message: str | None) -> str:
    """
    Redact common secret patterns from a string.
    Handles JSON-like key: value and key=value patterns.
    """
    if not message:
        return "" if message is None else message
    out = message
    # Bearer token first so "Authorization: Bearer xxx" is fully redacted
    out = re.sub(
        r"(Bearer\s+)([A-Za-z0-9_\-\.]+)",
        r"\1" + REDACT_PLACEHOLDER,
        out,
        flags=re.IGNORECASE,
    )
    # JSON-style "key": "value" or "key": "value"
    for key in REDACT_KEYS:
        # "client_secret": "sk-xxx" or 'client_secret': 'sk-xxx'
        pattern = r'(["\']?' + re.escape(key) + r'["\']?\s*[:=]\s*)(["\']?)([^"\'}\s,]+)\2'
        out = re.sub(pattern, r"\1\2" + REDACT_PLACEHOLDER + r"\2", out, flags=re.IGNORECASE)
    return out


class RedactingFormatter(logging.Formatter):
    """Formatter that redacts secret values from the log message and args."""

    def format(self, record: logging.LogRecord) -> str:
        # Build final message (msg % args), redact it, then pass through with no args
        # so the parent formatter does not try to re-interpolate (which would raise
        # "not all arguments converted").
        original_msg = record.getMessage()
        record.msg = redact_secrets(original_msg)
        record.args = ()
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """
    Configure root logger: console handler with RedactingFormatter,
    optional file handler. Level and log_file can come from config.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers when called multiple times (e.g. in tests)
    if not root.handlers:
        fmt = RedactingFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Avoid duplicate file handler for same path
        existing = [h for h in root.handlers if getattr(h, "baseFilename", None) == str(path.absolute())]
        if not existing:
            file_handler = logging.FileHandler(path, encoding="utf-8")
            file_handler.setFormatter(
                RedactingFormatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name."""
    return logging.getLogger(name)
