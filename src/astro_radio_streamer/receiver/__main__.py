from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from ..db.pool import create_pool
from ..db.worker import db_worker
from .server import start_server

if TYPE_CHECKING:
    from ..protocol.frame import SpacePacket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


async def _run() -> None:
    pool = await create_pool()
    queue: asyncio.Queue[SpacePacket] = asyncio.Queue(maxsize=10_000)

    worker_task = asyncio.create_task(db_worker(pool, queue))

    try:
        await start_server(queue)
    finally:
        await queue.join()
        worker_task.cancel()
        await pool.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
