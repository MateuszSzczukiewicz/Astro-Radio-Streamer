from __future__ import annotations

import logging
import struct

from ..protocol.constants import (
    CRC_SIZE,
    HEADER_SIZE,
    SYNC_WORD,
    SYNC_WORD_SIZE,
)
from ..protocol.crc import crc32
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
        frames: list[TelemetryFrame] = []

        while True:
            sync_idx = self._buf.find(SYNC_WORD)

            if sync_idx == -1:
                if self._buf[-1:] == SYNC_WORD[:1]:
                    tail = self._buf[-1:]
                    self._buf.clear()
                    self._buf.extend(tail)
                else:
                    self._buf.clear()
                break

            if sync_idx > 0:
                del self._buf[:sync_idx]

            if len(self._buf) < HEADER_SIZE:
                break

            payload_len = struct.unpack_from(
                ">H", self._buf, SYNC_WORD_SIZE + 4
            )[0]
            total = HEADER_SIZE + payload_len + CRC_SIZE

            if len(self._buf) < total:
                break

            raw_frame = bytes(self._buf[:total])
            del self._buf[:total]

            frame_id = struct.unpack_from(">I", raw_frame, SYNC_WORD_SIZE)[0]
            payload = raw_frame[HEADER_SIZE : HEADER_SIZE + payload_len]
            received_crc = struct.unpack_from(
                ">I", raw_frame, HEADER_SIZE + payload_len
            )[0]

            computed_crc = crc32(raw_frame[SYNC_WORD_SIZE : HEADER_SIZE + payload_len])

            if computed_crc != received_crc:
                logger.warning(
                    "CRC mismatch on frame %d: expected %08X, got %08X",
                    frame_id,
                    received_crc,
                    computed_crc,
                )
                continue

            frames.append(
                TelemetryFrame(
                    frame_id=frame_id,
                    payload=payload,
                    checksum=received_crc,
                    received_at=TelemetryFrame.timestamp(),
                )
            )

        return frames

    @property
    def pending(self) -> int:
        return len(self._buf)

    def clear(self) -> None:
        self._buf.clear()
