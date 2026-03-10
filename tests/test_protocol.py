from datetime import UTC, datetime

from astro_radio_streamer.protocol.constants import (
    APID_SIZE,
    ASM,
    ASM_SIZE,
    DATA_FIELD_LEN_SIZE,
    FECF_SIZE,
    HEADER_SIZE,
    MIN_PACKET_SIZE,
)
from astro_radio_streamer.protocol.crc import crc32
from astro_radio_streamer.protocol.frame import SpacePacket
from astro_radio_streamer.protocol.types import (
    APID,
    FECF,
    PacketDataField,
    ReceivedAt,
)


class TestTypes:
    def test_aliases_resolve(self) -> None:
        apid: APID = 42
        data: PacketDataField = b"\x00"
        fecf: FECF = 123
        ts: ReceivedAt = datetime.now(UTC)
        assert isinstance(apid, int)
        assert isinstance(data, bytes)
        assert isinstance(fecf, int)
        assert isinstance(ts, datetime)


class TestConstants:
    def test_asm(self) -> None:
        assert ASM == b"\xAA\xBB"
        assert ASM_SIZE == 2

    def test_sizes(self) -> None:
        assert APID_SIZE == 4
        assert DATA_FIELD_LEN_SIZE == 2
        assert HEADER_SIZE == 8
        assert FECF_SIZE == 4
        assert MIN_PACKET_SIZE == 12


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


class TestSpacePacket:
    def test_creation(self) -> None:
        ts = datetime.now(UTC)
        pkt = SpacePacket(
            apid=1,
            data_field=b"\x01\x02",
            fecf=0xDEAD,
            received_at=ts,
        )
        assert pkt.apid == 1
        assert pkt.data_field == b"\x01\x02"
        assert pkt.fecf == 0xDEAD
        assert pkt.received_at == ts

    def test_frozen(self) -> None:
        pkt = SpacePacket(
            apid=1,
            data_field=b"",
            fecf=0,
            received_at=datetime.now(UTC),
        )
        try:
            pkt.apid = 2
            raise AssertionError("Should not reach here")
        except AttributeError:
            pass

    def test_timestamp(self) -> None:
        before = datetime.now(UTC)
        ts = SpacePacket.timestamp()
        after = datetime.now(UTC)
        assert before <= ts <= after

    def test_slots(self) -> None:
        pkt = SpacePacket(
            apid=1,
            data_field=b"",
            fecf=0,
            received_at=datetime.now(UTC),
        )
        assert not hasattr(pkt, "__dict__")
