"""Tests for bulk-upload automation."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ocrolus_automations.automations.bulk_upload import (
    BulkUploadResult,
    discover_books,
    format_summary,
    run_bulk_upload,
)
from ocrolus_automations.clients.ocrolus_client import OcrolusClient
from ocrolus_automations.config import OrgCredentials
from ocrolus_automations.utils.http import OcrolusAPIError


# ---------------------------------------------------------------------------
# discover_books tests
# ---------------------------------------------------------------------------


class TestDiscoverBooks:
    def test_finds_subfolders_with_matching_files(self, tmp_path: Path):
        book = tmp_path / "BookA"
        book.mkdir()
        (book / "doc1.pdf").write_bytes(b"pdf")
        (book / "doc2.png").write_bytes(b"png")
        (book / "notes.txt").write_bytes(b"skip")

        result = discover_books([tmp_path])
        assert len(result) == 1
        name, path, files = result[0]
        assert name == "BookA"
        assert path == book
        assert len(files) == 2
        assert all(f.suffix.lower() in {".pdf", ".png"} for f in files)

    def test_skips_empty_folders(self, tmp_path: Path):
        empty = tmp_path / "EmptyBook"
        empty.mkdir()
        (empty / "readme.txt").write_bytes(b"nope")

        result = discover_books([tmp_path])
        assert len(result) == 0

    def test_skips_hidden_dirs(self, tmp_path: Path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "secret.pdf").write_bytes(b"pdf")

        result = discover_books([tmp_path])
        assert len(result) == 0

    def test_multiple_input_dirs(self, tmp_path: Path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        book1 = dir_a / "Book1"
        book2 = dir_b / "Book2"
        book1.mkdir()
        book2.mkdir()
        (book1 / "f.pdf").write_bytes(b"")
        (book2 / "g.jpg").write_bytes(b"")

        result = discover_books([dir_a, dir_b])
        assert len(result) == 2

    def test_case_insensitive_extensions(self, tmp_path: Path):
        book = tmp_path / "Book"
        book.mkdir()
        (book / "DOC.PDF").write_bytes(b"")
        (book / "photo.JPG").write_bytes(b"")
        (book / "scan.TIFF").write_bytes(b"")

        result = discover_books([tmp_path])
        assert len(result) == 1
        assert len(result[0][2]) == 3

    def test_all_allowed_extensions(self, tmp_path: Path):
        book = tmp_path / "Book"
        book.mkdir()
        for ext in [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"]:
            (book / f"file{ext}").write_bytes(b"")

        result = discover_books([tmp_path])
        assert len(result[0][2]) == 6

    def test_nonexistent_input_dir(self, tmp_path: Path):
        result = discover_books([tmp_path / "nonexistent"])
        assert len(result) == 0

    def test_files_sorted_alphabetically(self, tmp_path: Path):
        book = tmp_path / "Book"
        book.mkdir()
        (book / "c.pdf").write_bytes(b"")
        (book / "a.pdf").write_bytes(b"")
        (book / "b.pdf").write_bytes(b"")

        result = discover_books([tmp_path])
        filenames = [f.name for f in result[0][2]]
        assert filenames == ["a.pdf", "b.pdf", "c.pdf"]


# ---------------------------------------------------------------------------
# run_bulk_upload tests
# ---------------------------------------------------------------------------


def _make_mock_client() -> MagicMock:
    mock = MagicMock(spec=OcrolusClient)
    mock.create_book.return_value = "fake-uuid-123"
    mock.upload_mixed_document.return_value = {"status": "ok"}
    return mock


class TestRunBulkUpload:
    def test_success(self, tmp_path: Path):
        book = tmp_path / "TestBook"
        book.mkdir()
        (book / "doc.pdf").write_bytes(b"content")

        mock_client = _make_mock_client()
        result = run_bulk_upload(
            input_dirs=[str(tmp_path)],
            org="org1",
            client=mock_client,
            return_result=True,
        )

        assert isinstance(result, BulkUploadResult)
        assert result.success is True
        assert result.total_books == 1
        assert result.successful_docs == 1
        mock_client.get_token.assert_called_once_with("org1")
        mock_client.create_book.assert_called_once_with("TestBook", "org1")
        mock_client.upload_mixed_document.assert_called_once()

    def test_dry_run(self, tmp_path: Path):
        book = tmp_path / "DryBook"
        book.mkdir()
        (book / "doc.pdf").write_bytes(b"content")

        mock_client = _make_mock_client()
        result = run_bulk_upload(
            input_dirs=[str(tmp_path)],
            org="org1",
            dry_run=True,
            client=mock_client,
            return_result=True,
        )

        mock_client.create_book.assert_not_called()
        mock_client.upload_mixed_document.assert_not_called()
        assert result.total_books == 1
        assert result.books[0].total_docs == 1

    def test_book_creation_failure_continues(self, tmp_path: Path):
        book_a = tmp_path / "BookA"
        book_b = tmp_path / "BookB"
        book_a.mkdir()
        book_b.mkdir()
        (book_a / "a.pdf").write_bytes(b"")
        (book_b / "b.pdf").write_bytes(b"")

        mock_client = _make_mock_client()
        mock_client.create_book.side_effect = [
            OcrolusAPIError("fail"),
            "uuid-b",
        ]

        result = run_bulk_upload(
            input_dirs=[str(tmp_path)],
            client=mock_client,
            return_result=True,
        )

        assert result.success is False
        assert result.total_books == 2
        assert result.successful_books == 1

    def test_document_failure_continues(self, tmp_path: Path):
        book = tmp_path / "Book"
        book.mkdir()
        (book / "bad.pdf").write_bytes(b"")
        (book / "good.pdf").write_bytes(b"")

        mock_client = _make_mock_client()
        mock_client.create_book.return_value = "uuid-1"
        mock_client.upload_mixed_document.side_effect = [
            OcrolusAPIError("upload fail"),
            {"status": "ok"},
        ]

        result = run_bulk_upload(
            input_dirs=[str(tmp_path)],
            client=mock_client,
            return_result=True,
        )

        assert result.success is False
        assert result.books[0].successful_docs == 1
        assert result.books[0].failed_docs == 1

    def test_exit_code_zero_on_success(self, tmp_path: Path):
        book = tmp_path / "Book"
        book.mkdir()
        (book / "doc.pdf").write_bytes(b"")

        mock_client = _make_mock_client()
        code = run_bulk_upload(
            input_dirs=[str(tmp_path)],
            client=mock_client,
            return_result=False,
        )
        assert code == 0

    def test_exit_code_one_on_failure(self, tmp_path: Path):
        book = tmp_path / "Book"
        book.mkdir()
        (book / "doc.pdf").write_bytes(b"")

        mock_client = _make_mock_client()
        mock_client.create_book.side_effect = OcrolusAPIError("fail")

        code = run_bulk_upload(
            input_dirs=[str(tmp_path)],
            client=mock_client,
            return_result=False,
        )
        assert code == 1

    def test_no_books_found(self, tmp_path: Path):
        result = run_bulk_upload(
            input_dirs=[str(tmp_path)],
            client=_make_mock_client(),
            return_result=True,
        )
        assert result.success is True
        assert result.total_books == 0

    def test_multiple_books_multiple_docs(self, tmp_path: Path):
        for name in ["BookA", "BookB"]:
            book = tmp_path / name
            book.mkdir()
            (book / "doc1.pdf").write_bytes(b"")
            (book / "doc2.png").write_bytes(b"")

        mock_client = _make_mock_client()
        mock_client.create_book.side_effect = ["uuid-a", "uuid-b"]

        result = run_bulk_upload(
            input_dirs=[str(tmp_path)],
            client=mock_client,
            return_result=True,
        )

        assert result.success is True
        assert result.total_books == 2
        assert result.total_docs == 4
        assert result.successful_docs == 4


# ---------------------------------------------------------------------------
# upload_mixed_document client method test
# ---------------------------------------------------------------------------


class TestUploadMixedDocument:
    def test_calls_correct_endpoint(self):
        with patch(
            "ocrolus_automations.clients.ocrolus_client.request_with_retry"
        ) as mock_req:
            mock_resp = MagicMock()
            mock_resp.content = b'{"ok": true}'
            mock_resp.json.return_value = {"ok": True}
            mock_req.return_value = mock_resp

            client = OcrolusClient(
                api_base="https://api.test.com",
                auth_base="https://auth.test.com",
                org_credentials={
                    "org1": OrgCredentials(client_id="id", client_secret="sec")
                },
            )
            client._tokens["org1"] = ("fake-token", float("inf"))

            result = client.upload_mixed_document(
                "book-uuid", "test.pdf", io.BytesIO(b"pdf"), "org1"
            )

            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "https://api.test.com/v1/book/upload/mixed"
            assert call_args[1]["data"] == {"book_uuid": "book-uuid"}
            assert result == {"ok": True}


# ---------------------------------------------------------------------------
# format_summary tests
# ---------------------------------------------------------------------------


class TestFormatSummary:
    def test_success_summary(self):
        result = BulkUploadResult(
            books=[
                MagicMock(
                    book_name="Book1",
                    folder_path="/tmp/Book1",
                    book_created=True,
                    book_uuid="uuid-1",
                    success=True,
                    total_docs=2,
                    successful_docs=2,
                    failed_docs=0,
                    documents=[
                        MagicMock(filename="a.pdf", success=True, error=None),
                        MagicMock(filename="b.pdf", success=True, error=None),
                    ],
                )
            ]
        )
        summary = format_summary(result)
        assert "Book1" in summary
        assert "uuid-1" in summary
        assert "SUCCESS" in summary
        assert "[OK]" in summary

    def test_dry_run_summary(self):
        result = BulkUploadResult(
            books=[
                MagicMock(
                    book_name="Book1",
                    folder_path="/tmp/Book1",
                    total_docs=3,
                    documents=[
                        MagicMock(filename="a.pdf"),
                        MagicMock(filename="b.pdf"),
                        MagicMock(filename="c.pdf"),
                    ],
                )
            ]
        )
        summary = format_summary(result, dry_run=True)
        assert "DRY RUN" in summary
        assert "Would" in summary
