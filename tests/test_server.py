import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock

import pytest

from astro_radio_streamer.receiver.server import (
    HOST,
    PORT,
    READ_TIMEOUT,
    handle_client,
    start_server,
)


def _make_reader_writer(
    chunks: list[bytes],
) -> tuple[AsyncMock, MagicMock]:
    reader = AsyncMock(spec=asyncio.StreamReader)
    reader.read = AsyncMock(side_effect=[*chunks, b""])
    writer = MagicMock(spec=asyncio.StreamWriter)
    writer.get_extra_info = MagicMock(return_value=("127.0.0.1", 9999))
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return reader, writer


class TestHandleClient:
    @pytest.mark.asyncio
    async def test_clean_disconnect(self) -> None:
        reader, writer = _make_reader_writer([b"\x00\x01\x02"])
        queue: asyncio.Queue = asyncio.Queue()
        await handle_client(reader, writer, queue)
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_enqueues_valid_packets(self) -> None:
        import struct

        from astro_radio_streamer.protocol.constants import ASM, ASM_SIZE
        from astro_radio_streamer.protocol.crc import crc32

        data_field = b"\x01\x02\x03\x04"
        hdr = ASM + struct.pack(">IH", 1, len(data_field))
        body = hdr[ASM_SIZE:] + data_field
        raw = hdr + data_field + struct.pack(">I", crc32(body))

        reader, writer = _make_reader_writer([raw])
        queue: asyncio.Queue = asyncio.Queue()
        await handle_client(reader, writer, queue)
        assert queue.qsize() == 1
        pkt = queue.get_nowait()
        assert pkt.apid == 1

    @pytest.mark.asyncio
    async def test_timeout_closes_connection(self) -> None:
        reader = AsyncMock(spec=asyncio.StreamReader)
        reader.read = AsyncMock(side_effect=asyncio.TimeoutError)
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.get_extra_info = MagicMock(return_value=("127.0.0.1", 9999))
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        queue: asyncio.Queue = asyncio.Queue()
        await handle_client(reader, writer, queue)
        writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_error_handled(self) -> None:
        reader = AsyncMock(spec=asyncio.StreamReader)
        reader.read = AsyncMock(side_effect=ConnectionResetError)
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.get_extra_info = MagicMock(return_value=("127.0.0.1", 9999))
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        queue: asyncio.Queue = asyncio.Queue()
        await handle_client(reader, writer, queue)
        writer.close.assert_called_once()


class TestStartServer:
    @pytest.mark.asyncio
    async def test_start_and_signal_shutdown(self) -> None:
        queue: asyncio.Queue = asyncio.Queue()

        async def trigger_shutdown() -> None:
            await asyncio.sleep(0.3)
            import os

            os.kill(os.getpid(), signal.SIGINT)

        asyncio.create_task(trigger_shutdown())
        await start_server(queue, host="127.0.0.1", port=0)


class TestServerConstants:
    def test_defaults(self) -> None:
        assert HOST == "0.0.0.0"
        assert PORT == 8888
        assert READ_TIMEOUT == 10.0
