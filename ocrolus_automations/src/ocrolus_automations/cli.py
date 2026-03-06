"""Typer CLI: automations + credential management."""

from __future__ import annotations

import json
from typing import Optional

import typer

from ocrolus_automations.automations.bulk_upload import run_bulk_upload
from ocrolus_automations.automations.move_book import run_move_book
from ocrolus_automations.clients.ocrolus_client import OcrolusClient
from ocrolus_automations.config import get_settings
from ocrolus_automations.log_config import setup_logging
from ocrolus_automations.utils.env_store import (
    ENV_FILE,
    add_org as env_add_org,
    parse_org_names,
    remove_org as env_remove_org,
)

app = typer.Typer(
    name="ocrolus-auto",
    help="Ocrolus API automations: move books, list automations, test single APIs, etc.",
)


def _ensure_logging() -> None:
    settings = get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file or None)


@app.command("move-book")
def move_book(
    source_book_uuid: str = typer.Option(..., "--source-book-uuid", help="Source book UUID"),
    target_book_name: str = typer.Option(..., "--target-book-name", help="Name for the new book in target org"),
    org_source: str = typer.Option("org1", "--org-source", help="Source org name (config key)"),
    org_target: str = typer.Option("org2", "--org-target", help="Target org name (config key)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without creating/uploading"),
    max_docs: Optional[int] = typer.Option(None, "--max-docs", help="Max documents to transfer (default: all)"),
) -> None:
    """Move a book from source org to target org (copy docs into a new book)."""
    _ensure_logging()
    exit_code = run_move_book(
        source_book_uuid=source_book_uuid,
        target_book_name=target_book_name,
        org_source=org_source,
        org_target=org_target,
        dry_run=dry_run,
        max_docs=max_docs,
    )
    raise typer.Exit(exit_code)


@app.command("bulk-upload")
def bulk_upload(
    input_dir: str = typer.Option(
        ...,
        "--input-dir",
        help="Path to directory containing book folders (each subfolder = one book)",
    ),
    org: str = typer.Option(
        "org1",
        "--org",
        help="Org name (config key for credentials)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print what would happen without creating books or uploading files",
    ),
) -> None:
    """Bulk-upload: create books from local folders and upload documents via /v1/book/upload/mixed."""
    _ensure_logging()
    exit_code = run_bulk_upload(
        input_dirs=[input_dir],
        org=org,
        dry_run=dry_run,
    )
    raise typer.Exit(exit_code)


@app.command("list-automations")
def list_automations() -> None:
    """Show available automations."""
    _ensure_logging()
    typer.echo("Available automations:")
    typer.echo("  bulk-upload Bulk-create books from local folders and upload documents")
    typer.echo("  move-book   Copy a book from one org to another (new book in target org)")
    typer.echo("  book-status Call GET /v1/book/status for a book (test single API)")
    typer.echo("")
    typer.echo("Credential management:")
    typer.echo("  add-org     Add org credentials to .env")
    typer.echo("  list-orgs   List configured orgs")
    typer.echo("  remove-org  Remove an org from .env")
    typer.echo("")
    typer.echo("Usage examples:")
    typer.echo("  ocrolus-auto bulk-upload --input-dir /path/to/books --org bulk_upload_test [--dry-run]")
    typer.echo("  ocrolus-auto move-book --source-book-uuid <uuid> --target-book-name \"My Book\" [--dry-run]")
    typer.echo("  ocrolus-auto book-status --book-uuid <uuid> --org org1")


# ---------------------------------------------------------------------------
# Credential management
# ---------------------------------------------------------------------------


@app.command("add-org")
def add_org(
    name: str = typer.Option(..., "--name", prompt="Org name (e.g. my_org)", help="Org name identifier"),
    client_id: str = typer.Option(..., "--client-id", prompt="Client ID", help="OAuth2 client ID"),
    client_secret: str = typer.Option(
        ..., "--client-secret", prompt="Client Secret", hide_input=True, help="OAuth2 client secret"
    ),
) -> None:
    """Add org credentials to .env file."""
    existing = parse_org_names()
    if name.lower() in existing:
        overwrite = typer.confirm(f"Org '{name}' already exists. Overwrite?", default=False)
        if not overwrite:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    env_add_org(name, client_id, client_secret)
    typer.echo(f"Saved credentials for org '{name}' to {ENV_FILE}")


@app.command("list-orgs")
def list_orgs() -> None:
    """List configured org names from .env."""
    orgs = parse_org_names()
    if not orgs:
        typer.echo("No orgs configured. Use 'ocrolus-auto add-org' to add one.")
        return
    typer.echo("Configured orgs:")
    for org in orgs:
        typer.echo(f"  {org}")


@app.command("remove-org")
def remove_org(
    name: str = typer.Option(..., "--name", prompt="Org name to remove", help="Org name to remove"),
) -> None:
    """Remove an org's credentials from .env."""
    existing = parse_org_names()
    if name.lower() not in existing:
        typer.echo(f"Org '{name}' not found.")
        raise typer.Exit(1)

    confirm = typer.confirm(f"Remove credentials for org '{name}'?", default=False)
    if not confirm:
        typer.echo("Aborted.")
        raise typer.Exit(0)

    env_remove_org(name)
    typer.echo(f"Removed org '{name}' from {ENV_FILE}")


@app.command("book-status")
def book_status(
    book_uuid: str = typer.Option(..., "--book-uuid", help="Book UUID"),
    org: str = typer.Option("org1", "--org", help="Org name (config key for credentials)"),
) -> None:
    """Call GET /v1/book/status for the given book and print the JSON (test single API)."""
    _ensure_logging()
    client = OcrolusClient()
    client.get_token(org)
    typer.echo(f"Auth success (org: {org}). Fetching book status...", err=True)
    data = client.get_book_status(book_uuid, org)
    typer.echo(json.dumps(data, indent=2))


if __name__ == "__main__":
    app()
