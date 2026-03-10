import struct

from astro_radio_streamer.protocol.constants import (
    ASM,
    ASM_SIZE,
    HEADER_SIZE,
)
from astro_radio_streamer.protocol.crc import crc32
from astro_radio_streamer.receiver.buffer import FrameBuffer


def _encode(apid: int, data_field: bytes) -> bytes:
    hdr = ASM + struct.pack(">IH", apid, len(data_field))
    body = hdr[ASM_SIZE:] + data_field
    return hdr + data_field + struct.pack(">I", crc32(body))


class TestFrameBufferBasic:
    def test_single_valid_packet(self) -> None:
        buf = FrameBuffer()
        raw = _encode(1, b"\x01\x02\x03")
        pkts = buf.feed(raw)
        assert len(pkts) == 1
        assert pkts[0].apid == 1
        assert pkts[0].data_field == b"\x01\x02\x03"

    def test_multiple_packets_one_chunk(self) -> None:
        buf = FrameBuffer()
        raw = _encode(10, b"AAA") + _encode(20, b"BBB")
        pkts = buf.feed(raw)
        assert len(pkts) == 2
        assert pkts[0].apid == 10
        assert pkts[1].apid == 20

    def test_empty_data_field(self) -> None:
        buf = FrameBuffer()
        raw = _encode(99, b"")
        pkts = buf.feed(raw)
        assert len(pkts) == 1
        assert pkts[0].data_field == b""

    def test_large_data_field(self) -> None:
        buf = FrameBuffer()
        data = b"\xff" * 1000
        raw = _encode(5, data)
        pkts = buf.feed(raw)
        assert len(pkts) == 1
        assert pkts[0].data_field == data


class TestFrameBufferGarbage:
    def test_garbage_prefix(self) -> None:
        buf = FrameBuffer()
        raw = b"\xff\xff\xff\x00\x00" + _encode(42, b"DATA")
        pkts = buf.feed(raw)
        assert len(pkts) == 1
        assert pkts[0].apid == 42

    def test_pure_garbage(self) -> None:
        buf = FrameBuffer()
        pkts = buf.feed(b"\x01\x02\x03\x04\x05")
        assert pkts == []
        assert buf.pending == 0

    def test_garbage_between_packets(self) -> None:
        buf = FrameBuffer()
        raw = _encode(1, b"A") + b"\xff\xff" + _encode(2, b"B")
        pkts = buf.feed(raw)
        assert len(pkts) == 2
        assert pkts[0].apid == 1
        assert pkts[1].apid == 2


class TestFrameBufferPartial:
    def test_split_packet(self) -> None:
        buf = FrameBuffer()
        raw = _encode(7, b"SPLIT")
        mid = len(raw) // 2
        assert buf.feed(raw[:mid]) == []
        assert buf.pending > 0
        pkts = buf.feed(raw[mid:])
        assert len(pkts) == 1
        assert pkts[0].apid == 7

    def test_header_only(self) -> None:
        buf = FrameBuffer()
        raw = _encode(1, b"X")
        assert buf.feed(raw[:HEADER_SIZE]) == []
        pkts = buf.feed(raw[HEADER_SIZE:])
        assert len(pkts) == 1

    def test_split_asm(self) -> None:
        buf = FrameBuffer()
        assert buf.feed(b"\xff\xaa") == []
        assert buf.pending == 1
        raw = _encode(99, b"SYNC")
        pkts = buf.feed(b"\xbb" + raw[ASM_SIZE:])
        assert len(pkts) == 1
        assert pkts[0].apid == 99

    def test_no_trailing_asm_byte(self) -> None:
        buf = FrameBuffer()
        assert buf.feed(b"\xff\xff\x00") == []
        assert buf.pending == 0


class TestFrameBufferFECF:
    def test_bad_fecf_rejected(self) -> None:
        buf = FrameBuffer()
        raw = bytearray(_encode(6, b"BAD"))
        raw[-1] ^= 0xFF
        pkts = buf.feed(bytes(raw))
        assert pkts == []

    def test_bad_fecf_doesnt_block_next(self) -> None:
        buf = FrameBuffer()
        bad = bytearray(_encode(1, b"BAD"))
        bad[-1] ^= 0xFF
        good = _encode(2, b"GOOD")
        pkts = buf.feed(bytes(bad) + good)
        assert len(pkts) == 1
        assert pkts[0].apid == 2

    def test_fecf_scope(self) -> None:
        buf = FrameBuffer()
        raw = _encode(1, b"TEST")
        pkts = buf.feed(raw)
        expected_fecf = crc32(raw[ASM_SIZE : HEADER_SIZE + 4])
        assert pkts[0].fecf == expected_fecf


class TestFrameBufferOOM:
    def test_overflow_purge(self) -> None:
        buf = FrameBuffer(max_size=100)
        pkts = buf.feed(b"\x00" * 101)
        assert pkts == []
        assert buf.pending == 0

    def test_cumulative_overflow(self) -> None:
        buf = FrameBuffer(max_size=100)
        buf.feed(b"\x00" * 60)
        pkts = buf.feed(b"\x00" * 50)
        assert pkts == []
        assert buf.pending == 0

    def test_normal_under_limit(self) -> None:
        buf = FrameBuffer(max_size=1024)
        raw = _encode(1, b"OK")
        pkts = buf.feed(raw)
        assert len(pkts) == 1


class TestFrameBufferProperties:
    def test_pending(self) -> None:
        buf = FrameBuffer()
        assert buf.pending == 0
        buf.feed(ASM)
        assert buf.pending > 0

    def test_clear(self) -> None:
        buf = FrameBuffer()
        buf.feed(ASM + b"\x00" * 20)
        buf.clear()
        assert buf.pending == 0
