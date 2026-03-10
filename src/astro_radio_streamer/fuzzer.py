from boofuzz import (
    Block,
    Checksum,
    DWord,
    RandomData,
    Request,
    Session,
    Size,
    Static,
    Target,
)
from boofuzz.connections import TCPSocketConnection

from .protocol.crc import crc32

HOST = "127.0.0.1"
PORT = 8888

ASM = b"\xAA\xBB"


def _crc32_bytes(data: bytes) -> bytes:
    return crc32(data).to_bytes(4, "big")


def build_telemetry_request() -> Request:
    return Request(
        "space-packet",
        children=(
            Static("asm", default_value=ASM),
            Block(
                "fecf-scope",
                children=(
                    DWord(
                        "apid",
                        default_value=1,
                        endian=">",
                    ),
                    Size(
                        "data_field_length",
                        block_name="data-field-block",
                        length=2,
                        endian=">",
                    ),
                    Block(
                        "data-field-block",
                        children=(
                            RandomData(
                                "sensor_data",
                                default_value=b"\x01\x02\x03\x04",
                                min_length=4,
                                max_length=256,
                            ),
                        ),
                    ),
                ),
            ),
            Checksum(
                "fecf",
                block_name="fecf-scope",
                algorithm=_crc32_bytes,
                length=4,
                endian=">",
            ),
        ),
    )


def main() -> None:
    session = Session(
        target=Target(connection=TCPSocketConnection(HOST, PORT)),
        sleep_time=0.05,
    )

    request = build_telemetry_request()
    session.connect(request)
    session.fuzz()


if __name__ == "__main__":
    main()
