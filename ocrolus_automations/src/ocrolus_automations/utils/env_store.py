"""Shared .env credential store: read, write, parse org names."""

from __future__ import annotations

import re
from pathlib import Path

# .env file lives at the package root (next to pyproject.toml)
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def read_env_lines(path: Path | None = None) -> list[str]:
    """Read .env file lines, or return empty list if it doesn't exist."""
    p = path or ENV_FILE
    if p.is_file():
        return p.read_text().splitlines()
    return []


def write_env_lines(lines: list[str], path: Path | None = None) -> None:
    """Write lines back to .env file."""
    p = path or ENV_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n")


def parse_org_names(path: Path | None = None) -> list[str]:
    """Extract unique org names from OCROLUS_ORGS__<ORG>__CLIENT_ID lines."""
    pattern = re.compile(r"^OCROLUS_ORGS__(\w+)__CLIENT_ID\s*=", re.IGNORECASE)
    orgs: list[str] = []
    for line in read_env_lines(path):
        m = pattern.match(line.strip())
        if m:
            orgs.append(m.group(1).lower())
    return orgs


def add_org(
    name: str,
    client_id: str,
    client_secret: str,
    path: Path | None = None,
) -> None:
    """Add or overwrite org credentials in .env."""
    key = name.upper()
    prefix = f"OCROLUS_ORGS__{key}__"
    lines = read_env_lines(path)
    # Remove existing entries for this org
    lines = [ln for ln in lines if not ln.strip().upper().startswith(prefix)]
    lines.append(f"OCROLUS_ORGS__{key}__CLIENT_ID={client_id}")
    lines.append(f"OCROLUS_ORGS__{key}__CLIENT_SECRET={client_secret}")
    write_env_lines(lines, path)


def remove_org(name: str, path: Path | None = None) -> bool:
    """Remove org credentials from .env. Returns True if org was found."""
    key = name.upper()
    prefix = f"OCROLUS_ORGS__{key}__"
    lines = read_env_lines(path)
    filtered = [ln for ln in lines if not ln.strip().upper().startswith(prefix)]
    if len(filtered) == len(lines):
        return False
    write_env_lines(filtered, path)
    return True
