"""Automation modules."""

from ocrolus_automations.automations.bulk_upload import run_bulk_upload
from ocrolus_automations.automations.move_book import run_move_book

__all__ = ["run_bulk_upload", "run_move_book"]
