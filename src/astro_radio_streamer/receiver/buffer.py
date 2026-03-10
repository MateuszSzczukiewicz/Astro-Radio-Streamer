from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..protocol.frame import TelemetryFrame

logger = logging.getLogger(__name__)

READ_SIZE = 4096
MAX_BUFFER_SIZE = 1_048_576


class FrameBuffer:
    def __init__(self, max_size: int = MAX_BUFFER_SIZE) -> None:
        self._buf = bytearray()
        self._max_size = max_size

    def feed(self, chunk: bytes) -> list[TelemetryFrame]:
        if len(self._buf) + len(chunk) > self._max_size:
            logger.error(
                "Buffer overflow attempt: %d + %d > %d B — purging",
                len(self._buf),
                len(chunk),
                self._max_size,
            )
            self._buf.clear()
            return []

        self._buf.extend(chunk)
        return []

    @property
    def pending(self) -> int:
        return len(self._buf)

    def clear(self) -> None:
        self._buf.clear()
