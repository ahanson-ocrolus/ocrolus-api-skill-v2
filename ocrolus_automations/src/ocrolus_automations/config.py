"""Configuration via pydantic-settings (.env and environment variables)."""

from __future__ import annotations

import os
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env from cwd (optional for local runs)
except ImportError:
    pass

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OrgCredentials(BaseSettings):
    """Credentials for a single Ocrolus org."""

    model_config = SettingsConfigDict(extra="ignore")

    client_id: str = ""
    client_secret: str = ""


def _load_orgs_from_env() -> dict[str, dict[str, str]]:
    """Parse OCROLUS_ORGS__<ORG>__CLIENT_ID / CLIENT_SECRET from environment."""
    prefix = "OCROLUS_ORGS__"
    org_data: dict[str, dict[str, str]] = {}
    for key, value in os.environ.items():
        if not key.startswith(prefix) or not value:
            continue
        rest = key[len(prefix) :]
        parts = rest.split("__", 1)
        if len(parts) != 2:
            continue
        org_name_raw, field = parts[0], parts[1].lower()
        org_name = org_name_raw.lower()
        if org_name not in org_data:
            org_data[org_name] = {}
        if field == "client_id":
            org_data[org_name]["client_id"] = value
        elif field == "client_secret":
            org_data[org_name]["client_secret"] = value
    return org_data


class Settings(BaseSettings):
    """Application settings loaded from .env and environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    ocrolus_api_base: str = "https://api.ocrolus.com"
    ocrolus_auth_base: str = "https://auth.ocrolus.com"
    ocrolus_orgs: dict[str, OrgCredentials] = {}

    log_level: str = "INFO"
    log_file: str = "logs/ocrolus_automations.log"

    @field_validator("ocrolus_orgs", mode="before")
    @classmethod
    def parse_orgs(cls, v: Any) -> dict[str, OrgCredentials]:
        if isinstance(v, dict) and v and not isinstance(next(iter(v.values())), dict):
            return v
        # Build from env: OCROLUS_ORGS__ORG1__CLIENT_ID etc.
        env_orgs = _load_orgs_from_env()
        if env_orgs:
            return {k: OrgCredentials(**data) for k, data in env_orgs.items()}
        if isinstance(v, dict):
            return {k: OrgCredentials(**val) if isinstance(val, dict) else val for k, val in v.items()}
        return {}


def get_settings() -> Settings:
    """Return loaded settings (singleton-style; pydantic-settings caches per model)."""
    return Settings()
