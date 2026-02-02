"""
Spooled temp file and streaming helpers for document transfer.

Use in-memory buffer or spooled temp file so PDFs are not written to disk
beyond the process; temp files are deleted when closed.
"""

from __future__ import annotations

import io
import tempfile
from typing import BinaryIO, Iterator

from ocrolus_automations.log_config import get_logger

logger = get_logger(__name__)

# Default max in-memory size before spooling to disk (5 MiB)
DEFAULT_SPOOL_THRESHOLD = 5 * 1024 * 1024


class SpooledTransfer:
    """
    Wraps a write stream that starts in-memory and spools to a temporary file
    if size exceeds threshold. The temp file is deleted when the context exits.
    Use for streaming download -> upload without persisting to disk.
    """

    def __init__(self, max_memory: int = DEFAULT_SPOOL_THRESHOLD) -> None:
        self._max_memory = max_memory
        self._buffer: BinaryIO = io.BytesIO()
        self._file: tempfile.SpooledTemporaryFile[bytes] | None = None
        self._rolled = False

    def write(self, chunk: bytes) -> int:
        """Write chunk; roll to temp file if over threshold."""
        n = len(chunk)
        if self._file is not None:
            return self._file.write(chunk)
        self._buffer.write(chunk)
        if self._buffer.tell() >= self._max_memory:
            self._roll_to_temp()
        return n

    def _roll_to_temp(self) -> None:
        """Switch from BytesIO to a spooled temp file and copy existing data."""
        self._file = tempfile.SpooledTemporaryFile(max_size=self._max_memory, mode="w+b")
        self._buffer.seek(0)
        while True:
            data = self._buffer.read(64 * 1024)
            if not data:
                break
            self._file.write(data)
        self._buffer.close()
        self._buffer = io.BytesIO()
        self._rolled = True
        logger.debug("Spooled transfer rolled to temp file (size > %s)", self._max_memory)

    def get_stream(self) -> BinaryIO:
        """
        Return a readable stream of all data written so far.
        Caller should read from the start; seek(0) is done here.
        """
        if self._file is not None:
            self._file.seek(0)
            return self._file
        self._buffer.seek(0)
        return self._buffer

    def close(self) -> None:
        """Close buffer and temp file; temp file is deleted on close."""
        if self._buffer is not None and not self._rolled:
            self._buffer.close()
            self._buffer = io.BytesIO()
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self) -> SpooledTransfer:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def stream_copy(
    source: Iterator[bytes],
    dest: BinaryIO,
    chunk_size: int = 64 * 1024,
) -> int:
    """
    Read from source iterator (e.g. response.iter_content) and write to dest.
    Returns total bytes written.
    """
    total = 0
    for chunk in source:
        if chunk:
            dest.write(chunk)
            total += len(chunk)
    return total
