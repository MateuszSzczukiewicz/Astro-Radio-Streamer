import struct

from astro_radio_streamer.fuzzer import (
    HOST,
    PORT,
    ASM,
    _crc32_bytes,
    build_telemetry_request,
)
from astro_radio_streamer.protocol.constants import (
    ASM_SIZE,
    HEADER_SIZE,
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
        assert req.name == "space-packet"

    def test_renders_valid_packet(self) -> None:
        raw = build_telemetry_request().render()
        assert raw[:2] == ASM
        assert len(raw) >= HEADER_SIZE + 4

    def test_roundtrip_with_parser(self) -> None:
        raw = build_telemetry_request().render()
        buf = FrameBuffer()
        pkts = buf.feed(raw)
        assert len(pkts) == 1
        assert pkts[0].apid == 1
        assert pkts[0].data_field == b"\x01\x02\x03\x04"

    def test_fecf_valid(self) -> None:
        raw = build_telemetry_request().render()
        data_field_len = struct.unpack_from(">H", raw, ASM_SIZE + 4)[0]
        fecf_offset = HEADER_SIZE + data_field_len
        received_fecf = struct.unpack_from(">I", raw, fecf_offset)[0]
        computed = crc32(raw[ASM_SIZE:fecf_offset])
        assert received_fecf == computed


class TestFuzzerConstants:
    def test_defaults(self) -> None:
        assert HOST == "127.0.0.1"
        assert PORT == 8888
        assert ASM == b"\xaa\xbb"
