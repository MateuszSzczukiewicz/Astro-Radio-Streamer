from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncpg import Pool

    from ..protocol.frame import TelemetryFrame

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
FLUSH_TIMEOUT = 2.0

INSERT_SQL = """
    INSERT INTO telemetry (time, frame_id, payload, checksum)
    VALUES ($1, $2, $3, $4)
"""


async def db_worker(
    pool: Pool,
    queue: asyncio.Queue[TelemetryFrame],
) -> None:
    batch: list[TelemetryFrame] = []

    while True:
        try:
            frame = await asyncio.wait_for(queue.get(), timeout=FLUSH_TIMEOUT)
            batch.append(frame)

            if len(batch) < BATCH_SIZE:
                continue
        except TimeoutError:
            pass

        if not batch:
            continue

        await _flush(pool, batch)

        for _ in batch:
            queue.task_done()

        batch.clear()


async def _flush(pool: Pool, batch: list[TelemetryFrame]) -> None:
    records = [
        (f.received_at, f.frame_id, f.payload, f.checksum)
        for f in batch
    ]

    try:
        async with pool.acquire() as conn:
            await conn.executemany(INSERT_SQL, records)
        logger.info("Flushed %d frames to TimescaleDB", len(batch))
    except Exception:
        logger.exception("Failed to flush %d frames", len(batch))
