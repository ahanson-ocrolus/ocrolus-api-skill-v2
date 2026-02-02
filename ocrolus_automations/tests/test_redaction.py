"""Tests for secret redaction in logging."""

from __future__ import annotations

import pytest

from ocrolus_automations.log_config import REDACT_PLACEHOLDER, redact_secrets


def test_redact_empty() -> None:
    """Empty or None message returns empty or unchanged."""
    assert redact_secrets("") == ""
    assert redact_secrets(None) == ""


def test_redact_bearer_token() -> None:
    """Bearer token in message is redacted."""
    msg = "Authorization: Bearer sk-abc123xyz"
    out = redact_secrets(msg)
    assert "sk-abc123xyz" not in out
    assert REDACT_PLACEHOLDER in out


def test_redact_json_client_secret() -> None:
    """JSON-style client_secret value is redacted."""
    msg = '{"client_secret": "my-secret-key", "name": "test"}'
    out = redact_secrets(msg)
    assert "my-secret-key" not in out
    assert REDACT_PLACEHOLDER in out
    assert "client_secret" in out


def test_redact_key_value_pattern() -> None:
    """key=value style secret is redacted."""
    msg = "client_id=abc123"
    out = redact_secrets(msg)
    assert "abc123" not in out
    assert REDACT_PLACEHOLDER in out


def test_redact_preserves_non_secrets() -> None:
    """Non-secret content is preserved."""
    msg = "User name is Alice and book_uuid is 123"
    out = redact_secrets(msg)
    assert out == msg


def test_redact_case_insensitive() -> None:
    """Secret key matching is case-insensitive."""
    msg = "Authorization: Bearer token123"
    out = redact_secrets(msg)
    assert "token123" not in out
    assert REDACT_PLACEHOLDER in out
