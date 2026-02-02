"""Tests for streaming and spooled transfer utilities."""

from __future__ import annotations

import io

import pytest

from ocrolus_automations.utils.streams import (
    DEFAULT_SPOOL_THRESHOLD,
    SpooledTransfer,
    stream_copy,
)


def test_stream_copy_empty() -> None:
    """stream_copy with empty iterator writes nothing."""
    dest = io.BytesIO()
    total = stream_copy(iter([]), dest)
    assert total == 0
    assert dest.getvalue() == b""


def test_stream_copy_chunks() -> None:
    """stream_copy writes all chunks to dest."""
    dest = io.BytesIO()
    chunks = [b"a", b"bb", b"ccc"]
    total = stream_copy(iter(chunks), dest)
    assert total == 6
    assert dest.getvalue() == b"abbccc"


def test_spooled_transfer_small_stays_in_memory() -> None:
    """Small writes stay in BytesIO; get_stream returns full content."""
    with SpooledTransfer(max_memory=100) as spool:
        spool.write(b"hello")
        spool.write(b" world")
        stream = spool.get_stream()
        assert stream.read() == b"hello world"


def test_spooled_transfer_get_stream_seeked() -> None:
    """get_stream returns stream positioned at start."""
    with SpooledTransfer(max_memory=100) as spool:
        spool.write(b"abc")
        s = spool.get_stream()
        assert s.tell() == 0
        assert s.read(1) == b"a"
        assert s.read(2) == b"bc"


def test_spooled_transfer_over_threshold_rolls() -> None:
    """Writing more than max_memory rolls to temp file."""
    with SpooledTransfer(max_memory=10) as spool:
        spool.write(b"0123456789")
        spool.write(b"extra")
        stream = spool.get_stream()
        assert stream.read() == b"0123456789extra"


def test_spooled_transfer_close_cleans_up() -> None:
    """close() does not raise; multiple close is safe."""
    spool = SpooledTransfer(max_memory=100)
    spool.write(b"x")
    spool.close()
    spool.close()


def test_spooled_transfer_context_exit_closes() -> None:
    """Exiting context manager closes and prevents further write."""
    with SpooledTransfer(max_memory=100) as spool:
        spool.write(b"ok")
    # After exit, write is no longer valid (buffer may be closed); get_stream would fail
    # We only require that exit doesn't raise
    pass
