import struct

from astro_radio_streamer.fuzzer import (
    HOST,
    PORT,
    SYNC_WORD,
    _crc32_bytes,
    build_telemetry_request,
)
from astro_radio_streamer.protocol.constants import (
    HEADER_SIZE,
    SYNC_WORD_SIZE,
)
from astro_radio_streamer.protocol.crc import crc32
from astro_radio_streamer.receiver.buffer import FrameBuffer


class TestCRC32Bytes:
    def test_returns_4_bytes(self) -> None:
        result = _crc32_bytes(b"\x01\x02\x03")
        assert isinstance(result, bytes)
        assert len(result) == 4

    def test_matches_crc32(self) -> None:
        data = b"test data"
        expected = crc32(data).to_bytes(4, "big")
        assert _crc32_bytes(data) == expected


class TestBuildRequest:
    def test_request_name(self) -> None:
        req = build_telemetry_request()
        assert req.name == "telemetry-frame"

    def test_renders_valid_frame(self) -> None:
        raw = build_telemetry_request().render()
        assert raw[:2] == SYNC_WORD
        assert len(raw) >= HEADER_SIZE + 4

    def test_roundtrip_with_parser(self) -> None:
        raw = build_telemetry_request().render()
        buf = FrameBuffer()
        frames = buf.feed(raw)
        assert len(frames) == 1
        assert frames[0].frame_id == 1
        assert frames[0].payload == b"\x01\x02\x03\x04"

    def test_crc_valid(self) -> None:
        raw = build_telemetry_request().render()
        payload_len = struct.unpack_from(">H", raw, SYNC_WORD_SIZE + 4)[0]
        crc_offset = HEADER_SIZE + payload_len
        received_crc = struct.unpack_from(">I", raw, crc_offset)[0]
        computed = crc32(raw[SYNC_WORD_SIZE:crc_offset])
        assert received_crc == computed


class TestFuzzerConstants:
    def test_defaults(self) -> None:
        assert HOST == "127.0.0.1"
        assert PORT == 8888
        assert SYNC_WORD == b"\xAA\xBB"
