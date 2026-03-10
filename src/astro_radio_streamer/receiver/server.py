from __future__ import annotations

import asyncio
import logging
import signal

from .buffer import READ_SIZE, FrameBuffer

logger = logging.getLogger(__name__)

HOST = "0.0.0.0"
PORT = 8888
READ_TIMEOUT = 10.0


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    peer = writer.get_extra_info("peername")
    logger.info("Connection from %s", peer)

    buf = FrameBuffer()

    try:
        while True:
            data = await asyncio.wait_for(
                reader.read(READ_SIZE),
                timeout=READ_TIMEOUT,
            )
            if not data:
                break

            frames = buf.feed(data)

            if frames:
                logger.info(
                    "Decoded %d frames (buffer: %d B)",
                    len(frames),
                    buf.pending,
                )
    except TimeoutError:
        logger.warning("Read timeout (%ss), closing: %s", READ_TIMEOUT, peer)
    except ConnectionError:
        logger.warning("Connection lost: %s", peer)
    finally:
        writer.close()
        await writer.wait_closed()
        logger.info("Closed connection: %s", peer)


async def start_server(
    host: str = HOST,
    port: int = PORT,
) -> None:
    server = await asyncio.start_server(handle_client, host, port)

    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    logger.info("Listening on %s", addrs)

    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    async with server:
        server_task = asyncio.create_task(server.serve_forever())
        await stop
        logger.info("Shutdown signal received, draining connections…")
        server.close()
        await server.wait_closed()
        server_task.cancel()
        logger.info("Server stopped")
