from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .types import Checksum, FrameId, RawPayload, ReceivedAt


@dataclass(frozen=True, slots=True)
class TelemetryFrame:
    frame_id: FrameId
    payload: RawPayload
    checksum: Checksum
    received_at: ReceivedAt

    @staticmethod
    def timestamp() -> ReceivedAt:
        return datetime.now(UTC)
