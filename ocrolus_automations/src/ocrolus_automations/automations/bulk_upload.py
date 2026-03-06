"""
Bulk-upload automation: create books from local folders and upload documents.

Input: one or more directories, each containing subfolders.
Each subfolder = one book (name = folder name).
Files inside each subfolder are uploaded via /v1/book/upload/mixed.

Only files with allowed extensions (.pdf, .png, .jpg, .jpeg, .tiff, .tif) are uploaded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ocrolus_automations.clients.ocrolus_client import OcrolusClient
from ocrolus_automations.log_config import get_logger

logger = get_logger(__name__)

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DocumentUploadResult:
    """Result of a single document upload attempt."""

    filename: str
    success: bool
    error: str | None = None
    response_data: dict[str, Any] | None = None


@dataclass
class BookUploadResult:
    """Result of creating and populating a single book."""

    book_name: str
    folder_path: str
    book_created: bool
    book_uuid: str | None = None
    error: str | None = None
    documents: list[DocumentUploadResult] = field(default_factory=list)

    @property
    def total_docs(self) -> int:
        return len(self.documents)

    @property
    def successful_docs(self) -> int:
        return sum(1 for d in self.documents if d.success)

    @property
    def failed_docs(self) -> int:
        return sum(1 for d in self.documents if not d.success)

    @property
    def success(self) -> bool:
        return self.book_created and self.failed_docs == 0


@dataclass
class BulkUploadResult:
    """Aggregate result of the entire bulk-upload run."""

    books: list[BookUploadResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return all(b.success for b in self.books)

    @property
    def total_books(self) -> int:
        return len(self.books)

    @property
    def successful_books(self) -> int:
        return sum(1 for b in self.books if b.success)

    @property
    def total_docs(self) -> int:
        return sum(b.total_docs for b in self.books)

    @property
    def successful_docs(self) -> int:
        return sum(b.successful_docs for b in self.books)


# ---------------------------------------------------------------------------
# Directory discovery
# ---------------------------------------------------------------------------


def discover_books(
    input_dirs: list[Path],
) -> list[tuple[str, Path, list[Path]]]:
    """
    Scan input directories for book folders containing uploadable files.

    Returns list of (book_name, folder_path, [file_paths]) tuples.
    Skips hidden directories and folders with no matching files.
    """
    results: list[tuple[str, Path, list[Path]]] = []
    for input_dir in input_dirs:
        if not input_dir.is_dir():
            logger.warning("Input path is not a directory, skipping: %s", input_dir)
            continue
        for child in sorted(input_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            files = sorted(
                f
                for f in child.iterdir()
                if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
            )
            if not files:
                logger.warning(
                    "No uploadable files in folder %s (skipping)", child.name
                )
                continue
            results.append((child.name, child, files))
    return results


# ---------------------------------------------------------------------------
# Summary formatting
# ---------------------------------------------------------------------------


def format_summary(result: BulkUploadResult, dry_run: bool = False) -> str:
    """Render a human-readable summary of the bulk-upload run."""
    lines: list[str] = []
    tag = " (DRY RUN)" if dry_run else ""
    lines.append(f"\n{'=' * 40}")
    lines.append(f"Bulk Upload Summary{tag}")
    lines.append("=" * 40)

    if dry_run:
        lines.append(
            f"Would create {result.total_books} book(s) "
            f"and upload {result.total_docs} document(s) total.\n"
        )
        for book in result.books:
            lines.append(f'Book: "{book.book_name}" (folder: {book.folder_path})')
            lines.append(f"  Would upload {book.total_docs} document(s):")
            for doc in book.documents:
                lines.append(f"    {doc.filename}")
            lines.append("")
    else:
        lines.append(
            f"Total books: {result.total_books} | "
            f"Successful: {result.successful_books} | "
            f"Failed: {result.total_books - result.successful_books}"
        )
        lines.append(
            f"Total documents: {result.total_docs} | "
            f"Uploaded: {result.successful_docs} | "
            f"Failed: {result.total_docs - result.successful_docs}\n"
        )
        for book in result.books:
            lines.append(f'Book: "{book.book_name}" (folder: {book.folder_path})')
            if book.book_created:
                lines.append(f"  Status: SUCCESS | UUID: {book.book_uuid}")
                lines.append(
                    f"  Documents: {book.successful_docs}/{book.total_docs} uploaded"
                )
                for doc in book.documents:
                    tag_doc = "[OK]  " if doc.success else "[FAIL]"
                    line = f"    {tag_doc} {doc.filename}"
                    if not doc.success and doc.error:
                        line += f" — {doc.error}"
                    lines.append(line)
            else:
                lines.append(
                    f"  Status: FAILED — {book.error or 'Book creation error'}"
                )
                lines.append(
                    f"  Documents: 0/{book.total_docs} uploaded (skipped)"
                )
            lines.append("")

    lines.append("=" * 40)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main automation
# ---------------------------------------------------------------------------


def run_bulk_upload(
    input_dirs: list[str | Path],
    org: str = "org1",
    dry_run: bool = False,
    client: OcrolusClient | None = None,
    return_result: bool = False,
) -> int | BulkUploadResult:
    """
    Run the bulk-upload automation.

    For each subfolder in input_dirs:
      1. Create a book (name = folder name)
      2. Upload each document file via /v1/book/upload/mixed

    Returns exit code (0 = all success, 1 = any failure) unless return_result=True.
    """
    cl = client or OcrolusClient()

    # Auth
    cl.get_token(org)
    logger.info("Auth success (org: %s)", org)

    # Discover books
    paths = [Path(d) for d in input_dirs]
    books_to_upload = discover_books(paths)

    if not books_to_upload:
        logger.warning("No book folders with uploadable files found")
        result = BulkUploadResult()
        logger.info(format_summary(result, dry_run=dry_run))
        return result if return_result else 0

    logger.info(
        "Found %d book(s) with %d total document(s)",
        len(books_to_upload),
        sum(len(files) for _, _, files in books_to_upload),
    )

    result = BulkUploadResult()

    for book_name, folder_path, files in books_to_upload:
        if dry_run:
            book_result = BookUploadResult(
                book_name=book_name,
                folder_path=str(folder_path),
                book_created=False,
                documents=[
                    DocumentUploadResult(filename=f.name, success=False)
                    for f in files
                ],
            )
            logger.info(
                "Dry-run: would create book %r and upload %d document(s)",
                book_name,
                len(files),
            )
            result.books.append(book_result)
            continue

        # Create book
        book_result = BookUploadResult(
            book_name=book_name,
            folder_path=str(folder_path),
            book_created=False,
        )

        try:
            book_uuid = cl.create_book(book_name, org)
            book_result.book_created = True
            book_result.book_uuid = book_uuid
            logger.info(
                "Created book %r -> uuid=%s", book_name, book_uuid
            )
        except Exception as e:
            logger.exception("Failed to create book %r: %s", book_name, e)
            book_result.error = str(e)
            # Record skipped docs
            book_result.documents = [
                DocumentUploadResult(filename=f.name, success=False, error="Book creation failed")
                for f in files
            ]
            result.books.append(book_result)
            continue

        # Upload documents
        for i, file_path in enumerate(files, 1):
            logger.info(
                "Uploading doc %d/%d: %s -> book %s",
                i,
                len(files),
                file_path.name,
                book_uuid,
            )
            try:
                with open(file_path, "rb") as fobj:
                    resp_data = cl.upload_mixed_document(
                        book_uuid, file_path.name, fobj, org
                    )
                book_result.documents.append(
                    DocumentUploadResult(
                        filename=file_path.name,
                        success=True,
                        response_data=resp_data,
                    )
                )
                logger.info("Upload success: %s", file_path.name)
            except Exception as e:
                logger.exception(
                    "Upload failure for %s: %s", file_path.name, e
                )
                book_result.documents.append(
                    DocumentUploadResult(
                        filename=file_path.name,
                        success=False,
                        error=str(e),
                    )
                )

        result.books.append(book_result)

    # Summary
    logger.info(format_summary(result, dry_run=dry_run))

    if return_result:
        return result
    return 0 if result.success else 1
