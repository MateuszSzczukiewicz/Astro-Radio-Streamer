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

SYNC_WORD = b"\xAA\xBB"


def _crc32_bytes(data: bytes) -> bytes:
    return crc32(data).to_bytes(4, "big")


def build_telemetry_request() -> Request:
    return Request(
        "telemetry-frame",
        children=(
            Static("sync", default_value=SYNC_WORD),
            Block(
                "crc-scope",
                children=(
                    DWord(
                        "frame_id",
                        default_value=1,
                        endian=">",
                    ),
                    Size(
                        "payload_length",
                        block_name="payload-block",
                        length=2,
                        endian=">",
                    ),
                    Block(
                        "payload-block",
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
                "crc32",
                block_name="crc-scope",
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
