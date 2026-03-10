from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .types import APID, FECF, PacketDataField, ReceivedAt


@dataclass(frozen=True, slots=True)
class SpacePacket:
    apid: APID
    data_field: PacketDataField
    fecf: FECF
    received_at: ReceivedAt

    @staticmethod
    def timestamp() -> ReceivedAt:
        return datetime.now(UTC)
