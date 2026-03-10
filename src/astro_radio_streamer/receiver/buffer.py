from __future__ import annotations

import logging
import struct

from ..protocol.constants import (
    ASM,
    ASM_SIZE,
    FECF_SIZE,
    HEADER_SIZE,
)
from ..protocol.crc import crc32
from ..protocol.frame import SpacePacket

logger = logging.getLogger(__name__)

READ_SIZE = 4096
MAX_BUFFER_SIZE = 1_048_576


class FrameBuffer:
    def __init__(self, max_size: int = MAX_BUFFER_SIZE) -> None:
        self._buf = bytearray()
        self._max_size = max_size

    def feed(self, chunk: bytes) -> list[SpacePacket]:
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
        packets: list[SpacePacket] = []

        while True:
            asm_idx = self._buf.find(ASM)

            if asm_idx == -1:
                if self._buf[-1:] == ASM[:1]:
                    tail = self._buf[-1:]
                    self._buf.clear()
                    self._buf.extend(tail)
                else:
                    self._buf.clear()
                break

            if asm_idx > 0:
                del self._buf[:asm_idx]

            if len(self._buf) < HEADER_SIZE:
                break

            data_field_len = struct.unpack_from(">H", self._buf, ASM_SIZE + 4)[0]
            total = HEADER_SIZE + data_field_len + FECF_SIZE

            if len(self._buf) < total:
                break

            raw_packet = bytes(self._buf[:total])
            del self._buf[:total]

            apid = struct.unpack_from(">I", raw_packet, ASM_SIZE)[0]
            data_field = raw_packet[HEADER_SIZE : HEADER_SIZE + data_field_len]
            received_fecf = struct.unpack_from(
                ">I", raw_packet, HEADER_SIZE + data_field_len
            )[0]

            computed_fecf = crc32(raw_packet[ASM_SIZE : HEADER_SIZE + data_field_len])

            if computed_fecf != received_fecf:
                logger.warning(
                    "FECF mismatch on APID %d: expected %08X, got %08X",
                    apid,
                    received_fecf,
                    computed_fecf,
                )
                continue

            packets.append(
                SpacePacket(
                    apid=apid,
                    data_field=data_field,
                    fecf=received_fecf,
                    received_at=SpacePacket.timestamp(),
                )
            )

        return packets

    @property
    def pending(self) -> int:
        return len(self._buf)

    def clear(self) -> None:
        self._buf.clear()
