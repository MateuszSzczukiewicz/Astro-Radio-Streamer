import struct
from datetime import UTC, datetime

from astro_radio_streamer.protocol.constants import (
    CRC_SIZE,
    FRAME_ID_SIZE,
    HEADER_SIZE,
    MIN_FRAME_SIZE,
    PAYLOAD_LEN_SIZE,
    SYNC_WORD,
    SYNC_WORD_SIZE,
)
from astro_radio_streamer.protocol.crc import crc32
from astro_radio_streamer.protocol.frame import TelemetryFrame
from astro_radio_streamer.protocol.types import (
    Checksum,
    FrameId,
    RawPayload,
    ReceivedAt,
)


def _encode(frame_id: int, payload: bytes) -> bytes:
    hdr = SYNC_WORD + struct.pack(">IH", frame_id, len(payload))
    body = hdr[SYNC_WORD_SIZE:] + payload
    return hdr + payload + struct.pack(">I", crc32(body))


class TestTypes:
    def test_aliases_resolve(self) -> None:
        fid: FrameId = 42
        payload: RawPayload = b"\x00"
        checksum: Checksum = 123
        ts: ReceivedAt = datetime.now(UTC)
        assert isinstance(fid, int)
        assert isinstance(payload, bytes)
        assert isinstance(checksum, int)
        assert isinstance(ts, datetime)


class TestConstants:
    def test_sync_word(self) -> None:
        assert SYNC_WORD == b"\xAA\xBB"
        assert SYNC_WORD_SIZE == 2

    def test_sizes(self) -> None:
        assert FRAME_ID_SIZE == 4
        assert PAYLOAD_LEN_SIZE == 2
        assert HEADER_SIZE == 8
        assert CRC_SIZE == 4
        assert MIN_FRAME_SIZE == 12


class TestCRC32:
    def test_empty(self) -> None:
        assert crc32(b"") == 0x00000000

    def test_known_value(self) -> None:
        assert crc32(b"123456789") == 0xCBF43926

    def test_deterministic(self) -> None:
        data = b"\xDE\xAD\xBE\xEF"
        assert crc32(data) == crc32(data)

    def test_different_inputs(self) -> None:
        assert crc32(b"A") != crc32(b"B")

    def test_single_byte(self) -> None:
        result = crc32(b"\x00")
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFFFFFF


class TestTelemetryFrame:
    def test_creation(self) -> None:
        ts = datetime.now(UTC)
        frame = TelemetryFrame(
            frame_id=1,
            payload=b"\x01\x02",
            checksum=0xDEAD,
            received_at=ts,
        )
        assert frame.frame_id == 1
        assert frame.payload == b"\x01\x02"
        assert frame.checksum == 0xDEAD
        assert frame.received_at == ts

    def test_frozen(self) -> None:
        frame = TelemetryFrame(
            frame_id=1,
            payload=b"",
            checksum=0,
            received_at=datetime.now(UTC),
        )
        try:
            frame.frame_id = 2
            raise AssertionError("Should not reach here")
        except AttributeError:
            pass

    def test_timestamp(self) -> None:
        before = datetime.now(UTC)
        ts = TelemetryFrame.timestamp()
        after = datetime.now(UTC)
        assert before <= ts <= after

    def test_slots(self) -> None:
        frame = TelemetryFrame(
            frame_id=1,
            payload=b"",
            checksum=0,
            received_at=datetime.now(UTC),
        )
        assert not hasattr(frame, "__dict__")
