"""
Shared Ocrolus API client: auth, book, document APIs.

API assumptions (isolated here for easy adjustment):
- Auth: POST {auth_base}/oauth/token with client_id, client_secret, grant_type=client_credentials.
  Response: { "access_token": "...", "expires_in": 3600 } (or similar; we use access_token and optional expires_in).
- Book status: GET {api_base}/v1/book/status?book_uuid=... -> doc list extracted via configurable path (see automations).
- Book add: POST {api_base}/v1/book/add with JSON body including name; response has book uuid (path TBD).
- Document download: GET {api_base}/v2/document/download?doc_uuid=... returns raw bytes (streaming).
- Book upload: POST {api_base}/v1/book/upload multipart/form-data: file + book_uuid (or similar; exact field names TBD).
"""

from __future__ import annotations

import time
from typing import Any, BinaryIO, Iterator

import requests

from ocrolus_automations.config import OrgCredentials, get_settings
from ocrolus_automations.log_config import get_logger
from ocrolus_automations.utils.http import OcrolusAPIError, request_with_retry

logger = get_logger(__name__)

# Default token expiry buffer (refresh if less than this many seconds left)
TOKEN_EXPIRY_BUFFER = 60


class OcrolusClient:
    """
    Ocrolus API client with per-org Bearer tokens (cached in memory with expiry).
    """

    def __init__(
        self,
        api_base: str | None = None,
        auth_base: str | None = None,
        org_credentials: dict[str, OrgCredentials] | None = None,
    ) -> None:
        settings = get_settings()
        self.api_base = (api_base or settings.ocrolus_api_base).rstrip("/")
        self.auth_base = (auth_base or settings.ocrolus_auth_base).rstrip("/")
        self._creds = org_credentials or settings.ocrolus_orgs
        self._tokens: dict[str, tuple[str, float]] = {}  # org_name -> (token, expiry_ts)

    def get_token(self, org_name: str) -> str:
        """
        Return Bearer token for the org (cached with expiry).
        Org name is lowercased for lookup.
        """
        key = org_name.lower()
        if key not in self._creds:
            raise OcrolusAPIError(
                message=f"No credentials configured for org {org_name!r}. "
                "Set OCROLUS_ORGS__<ORG>__CLIENT_ID and OCROLUS_ORGS__<ORG>__CLIENT_SECRET."
            )
        creds = self._creds[key]
        now = time.time()
        if key in self._tokens:
            token, expiry = self._tokens[key]
            if expiry > now + TOKEN_EXPIRY_BUFFER:
                return token
        token, expires_in = self._fetch_token(creds.client_id, creds.client_secret)
        expiry = now + (expires_in or 3600) - TOKEN_EXPIRY_BUFFER
        self._tokens[key] = (token, expiry)
        return token

    def _fetch_token(self, client_id: str, client_secret: str) -> tuple[str, int]:
        """POST oauth/token; return (access_token, expires_in)."""
        url = f"{self.auth_base}/oauth/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }
        resp = request_with_retry("POST", url, data=data)
        body = resp.json()
        token = body.get("access_token")
        if not token:
            raise OcrolusAPIError(
                message="Auth response missing access_token",
                response_text=resp.text,
            )
        expires_in = body.get("expires_in", 3600)
        return token, int(expires_in)

    def _headers(self, org_name: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_token(org_name)}"}

    def get_book_status(self, book_uuid: str, org_name: str) -> dict[str, Any]:
        """GET /v1/book/status for the given book; return JSON body."""
        url = f"{self.api_base}/v1/book/status"
        params = {"book_uuid": book_uuid}
        resp = request_with_retry(
            "GET",
            url,
            params=params,
            headers=self._headers(org_name),
        )
        return resp.json()

    def create_book(
        self,
        name: str,
        org_name: str,
        **payload_extra: Any,
    ) -> str:
        """
        POST /v1/book/add with name (and optional extra payload).
        Returns the new book UUID (path into response is configurable; we assume top-level 'book_uuid' or 'uuid').
        """
        url = f"{self.api_base}/v1/book/add"
        body: dict[str, Any] = {"name": name, **payload_extra}
        resp = request_with_retry(
            "POST",
            url,
            json=body,
            headers=self._headers(org_name),
        )
        data = resp.json()
        # API may wrap payload in {"status", "message", "response": { ... } } (same as book/status)
        payload = data.get("response", data) if isinstance(data, dict) else data
        if not isinstance(payload, dict):
            payload = {}
        # Prefer common response shapes: top-level or nested book
        book_uuid = (
            payload.get("book_uuid")
            or payload.get("uuid")
            or (payload.get("book") or {}).get("uuid")
            or data.get("book_uuid")
            or data.get("uuid")
        )
        if not book_uuid:
            raise OcrolusAPIError(
                message="Create book response missing book_uuid/uuid",
                response_text=resp.text,
            )
        return str(book_uuid)

    def download_document(
        self,
        doc_uuid: str,
        org_name: str,
        stream: bool = True,
    ) -> requests.Response:
        """
        GET /v2/document/download?doc_uuid=...; return response with stream=True.
        Caller should use response.iter_content() and not persist to disk.
        """
        url = f"{self.api_base}/v2/document/download"
        params = {"doc_uuid": doc_uuid}
        return request_with_retry(
            "GET",
            url,
            params=params,
            headers=self._headers(org_name),
            stream=stream,
        )

    def upload_document(
        self,
        book_uuid: str,
        filename: str,
        fileobj: BinaryIO,
        org_name: str,
    ) -> dict[str, Any]:
        """
        POST /v1/book/upload multipart: file + book_uuid.
        Exact field names may vary (e.g. 'file' vs 'document', 'book_uuid' vs 'book_uuid').
        """
        url = f"{self.api_base}/v1/book/upload"
        fileobj.seek(0)
        files = {"file": (filename, fileobj)}
        data = {"book_uuid": book_uuid}
        resp = request_with_retry(
            "POST",
            url,
            data=data,
            files=files,
            headers=self._headers(org_name),
        )
        return resp.json() if resp.content else {}

    def upload_mixed_document(
        self,
        book_uuid: str,
        filename: str,
        fileobj: BinaryIO,
        org_name: str,
    ) -> dict[str, Any]:
        """
        POST /v1/book/upload/mixed multipart: file + book_uuid.
        Used for uploading mixed document types to a single book.
        """
        url = f"{self.api_base}/v1/book/upload/mixed"
        fileobj.seek(0)
        files = {"file": (filename, fileobj)}
        data = {"book_uuid": book_uuid}
        resp = request_with_retry(
            "POST",
            url,
            data=data,
            files=files,
            headers=self._headers(org_name),
        )
        return resp.json() if resp.content else {}
