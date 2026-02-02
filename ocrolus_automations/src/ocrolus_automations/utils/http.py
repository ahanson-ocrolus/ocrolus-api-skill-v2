"""HTTP request helpers, retry policy, and error classes for Ocrolus API."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

import requests
from requests import Response
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from ocrolus_automations.log_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class OcrolusAPIError(Exception):
    """Raised when an Ocrolus API request fails with HTTP error or bad response."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.request_id = request_id

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        if self.response_text:
            snippet = self.response_text[:200] + "..." if len(self.response_text) > 200 else self.response_text
            parts.append(f"response={snippet!r}")
        return " | ".join(parts)


def _is_transient_error(exception: BaseException) -> bool:
    """True if the error is transient (429, 5xx, timeout, connection)."""
    if isinstance(exception, requests.RequestException):
        if isinstance(exception, requests.Timeout):
            return True
        if isinstance(exception, requests.ConnectionError):
            return True
        if getattr(exception, "response", None) is not None:
            status = exception.response.status_code
            if status == 429:
                return True
            if 500 <= status < 600:
                return True
    return False


def _raise_for_ocrolus_error(response: Response) -> None:
    """Raise OcrolusAPIError with status, text snippet, and request id if present."""
    if response.ok:
        return
    request_id = response.headers.get("X-Request-Id") or response.headers.get("Request-Id")
    try:
        text = response.text
    except Exception:
        text = ""
    raise OcrolusAPIError(
        message=f"Ocrolus API error: {response.reason or response.status_code}",
        status_code=response.status_code,
        response_text=text,
        request_id=request_id,
    )


def request_with_retry(
    method: str,
    url: str,
    *,
    max_attempts: int = 5,
    retry_only_transient: bool = True,
    **kwargs: Any,
) -> Response:
    """
    Perform an HTTP request with exponential backoff retries for transient failures.
    Retries on: 429, 5xx, timeouts, connection errors.
    """
    session = kwargs.pop("session", None) or requests.Session()

    @retry(
        retry=retry_if_exception(_is_transient_error) if retry_only_transient else retry_if_exception(requests.RequestException),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            "Retrying after %s: %s",
            retry_state.outcome.exception() if retry_state.outcome else None,
            retry_state.retry_object.retry.__name__,
        ),
    )
    def _do_request() -> Response:
        resp = session.request(method, url, **kwargs)
        if not resp.ok:
            # Raise HTTPError for 429/5xx so tenacity retries; convert to OcrolusAPIError after
            if _is_transient_error(requests.HTTPError(response=resp)):
                resp.raise_for_status()
            _raise_for_ocrolus_error(resp)
        return resp

    try:
        return _do_request()
    except requests.HTTPError as e:
        if e.response is not None:
            _raise_for_ocrolus_error(e.response)
        raise OcrolusAPIError(str(e))


def session_request(
    session: requests.Session,
    method: str,
    url: str,
    raise_for_status: bool = True,
    **kwargs: Any,
) -> Response:
    """
    Thin wrapper: session.request + optional Ocrolus-style raise.
    Use this when you want a single attempt (no retry) or when retries are handled elsewhere.
    """
    resp = session.request(method, url, **kwargs)
    if raise_for_status and not resp.ok:
        _raise_for_ocrolus_error(resp)
    return resp
