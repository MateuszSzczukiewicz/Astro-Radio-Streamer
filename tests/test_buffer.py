import struct

from astro_radio_streamer.protocol.constants import (
    CRC_SIZE,
    HEADER_SIZE,
    SYNC_WORD,
    SYNC_WORD_SIZE,
)
from astro_radio_streamer.protocol.crc import crc32
from astro_radio_streamer.receiver.buffer import (
    MAX_BUFFER_SIZE,
    FrameBuffer,
)


def _encode(frame_id: int, payload: bytes) -> bytes:
    hdr = SYNC_WORD + struct.pack(">IH", frame_id, len(payload))
    body = hdr[SYNC_WORD_SIZE:] + payload
    return hdr + payload + struct.pack(">I", crc32(body))


class TestFrameBufferBasic:
    def test_single_valid_frame(self) -> None:
        buf = FrameBuffer()
        raw = _encode(1, b"\x01\x02\x03")
        frames = buf.feed(raw)
        assert len(frames) == 1
        assert frames[0].frame_id == 1
        assert frames[0].payload == b"\x01\x02\x03"

    def test_multiple_frames_one_chunk(self) -> None:
        buf = FrameBuffer()
        raw = _encode(10, b"AAA") + _encode(20, b"BBB")
        frames = buf.feed(raw)
        assert len(frames) == 2
        assert frames[0].frame_id == 10
        assert frames[1].frame_id == 20

    def test_empty_payload(self) -> None:
        buf = FrameBuffer()
        raw = _encode(99, b"")
        frames = buf.feed(raw)
        assert len(frames) == 1
        assert frames[0].payload == b""

    def test_max_payload(self) -> None:
        buf = FrameBuffer()
        payload = b"\xFF" * 1000
        raw = _encode(5, payload)
        frames = buf.feed(raw)
        assert len(frames) == 1
        assert frames[0].payload == payload


class TestFrameBufferGarbage:
    def test_garbage_prefix(self) -> None:
        buf = FrameBuffer()
        raw = b"\xFF\xFF\xFF\x00\x00" + _encode(42, b"DATA")
        frames = buf.feed(raw)
        assert len(frames) == 1
        assert frames[0].frame_id == 42

    def test_pure_garbage(self) -> None:
        buf = FrameBuffer()
        frames = buf.feed(b"\x01\x02\x03\x04\x05")
        assert frames == []
        assert buf.pending == 0

    def test_garbage_between_frames(self) -> None:
        buf = FrameBuffer()
        raw = _encode(1, b"A") + b"\xFF\xFF" + _encode(2, b"B")
        frames = buf.feed(raw)
        assert len(frames) == 2
        assert frames[0].frame_id == 1
        assert frames[1].frame_id == 2


class TestFrameBufferPartial:
    def test_split_frame(self) -> None:
        buf = FrameBuffer()
        raw = _encode(7, b"SPLIT")
        mid = len(raw) // 2
        assert buf.feed(raw[:mid]) == []
        assert buf.pending > 0
        frames = buf.feed(raw[mid:])
        assert len(frames) == 1
        assert frames[0].frame_id == 7

    def test_header_only(self) -> None:
        buf = FrameBuffer()
        raw = _encode(1, b"X")
        assert buf.feed(raw[:HEADER_SIZE]) == []
        frames = buf.feed(raw[HEADER_SIZE:])
        assert len(frames) == 1

    def test_split_sync_word(self) -> None:
        buf = FrameBuffer()
        assert buf.feed(b"\xFF\xAA") == []
        assert buf.pending == 1
        raw = _encode(99, b"SYNC")
        frames = buf.feed(b"\xBB" + raw[SYNC_WORD_SIZE:])
        assert len(frames) == 1
        assert frames[0].frame_id == 99

    def test_no_trailing_sync_byte(self) -> None:
        buf = FrameBuffer()
        assert buf.feed(b"\xFF\xFF\x00") == []
        assert buf.pending == 0


class TestFrameBufferCRC:
    def test_bad_crc_rejected(self) -> None:
        buf = FrameBuffer()
        raw = bytearray(_encode(6, b"BAD"))
        raw[-1] ^= 0xFF
        frames = buf.feed(bytes(raw))
        assert frames == []

    def test_bad_crc_doesnt_block_next(self) -> None:
        buf = FrameBuffer()
        bad = bytearray(_encode(1, b"BAD"))
        bad[-1] ^= 0xFF
        good = _encode(2, b"GOOD")
        frames = buf.feed(bytes(bad) + good)
        assert len(frames) == 1
        assert frames[0].frame_id == 2

    def test_crc_scope(self) -> None:
        buf = FrameBuffer()
        raw = _encode(1, b"TEST")
        frames = buf.feed(raw)
        expected_crc = crc32(raw[SYNC_WORD_SIZE : HEADER_SIZE + 4])
        assert frames[0].checksum == expected_crc


class TestFrameBufferOOM:
    def test_overflow_purge(self) -> None:
        buf = FrameBuffer(max_size=100)
        frames = buf.feed(b"\x00" * 101)
        assert frames == []
        assert buf.pending == 0

    def test_cumulative_overflow(self) -> None:
        buf = FrameBuffer(max_size=100)
        buf.feed(b"\x00" * 60)
        frames = buf.feed(b"\x00" * 50)
        assert frames == []
        assert buf.pending == 0

    def test_normal_under_limit(self) -> None:
        buf = FrameBuffer(max_size=1024)
        raw = _encode(1, b"OK")
        frames = buf.feed(raw)
        assert len(frames) == 1


class TestFrameBufferProperties:
    def test_pending(self) -> None:
        buf = FrameBuffer()
        assert buf.pending == 0
        buf.feed(SYNC_WORD)
        assert buf.pending > 0

    def test_clear(self) -> None:
        buf = FrameBuffer()
        buf.feed(SYNC_WORD + b"\x00" * 20)
        buf.clear()
        assert buf.pending == 0
