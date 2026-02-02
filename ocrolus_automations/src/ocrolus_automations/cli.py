"""Typer CLI: move-book, list-automations, book-status (test single API)."""

from __future__ import annotations

import json
from typing import Optional

import typer

from ocrolus_automations.automations.move_book import run_move_book
from ocrolus_automations.clients.ocrolus_client import OcrolusClient
from ocrolus_automations.config import get_settings
from ocrolus_automations.log_config import setup_logging

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


@app.command("list-automations")
def list_automations() -> None:
    """Show available automations."""
    _ensure_logging()
    typer.echo("Available automations:")
    typer.echo("  move-book   Copy a book from one org to another (new book in target org)")
    typer.echo("  book-status Call GET /v1/book/status for a book (test single API)")
    typer.echo("")
    typer.echo("Usage examples:")
    typer.echo("  ocrolus-auto move-book --source-book-uuid <uuid> --target-book-name \"My Book\" [--dry-run]")
    typer.echo("  ocrolus-auto book-status --book-uuid <uuid> --org org1")
    typer.echo("  python -m ocrolus_automations move-book --source-book-uuid <uuid> --target-book-name \"My Book\"")


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
