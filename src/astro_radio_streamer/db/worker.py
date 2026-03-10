from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncpg import Pool

    from ..protocol.frame import SpacePacket

from ..metrics import db_flush_duration_seconds, db_flush_packets_total

logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "100"))
FLUSH_TIMEOUT = float(os.environ.get("FLUSH_TIMEOUT", "2.0"))

INSERT_SQL = """
    INSERT INTO telemetry (time, apid, data_field, fecf)
    VALUES ($1, $2, $3, $4)
"""


async def db_worker(
    pool: Pool,
    queue: asyncio.Queue[SpacePacket],
) -> None:
    batch: list[SpacePacket] = []

    while True:
        try:
            packet = await asyncio.wait_for(queue.get(), timeout=FLUSH_TIMEOUT)
            batch.append(packet)

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


async def _flush(pool: Pool, batch: list[SpacePacket]) -> None:
    records = [(p.received_at, p.apid, p.data_field, p.fecf) for p in batch]

    t0 = time.monotonic()
    try:
        async with pool.acquire() as conn:
            await conn.executemany(INSERT_SQL, records)
        db_flush_duration_seconds.observe(time.monotonic() - t0)
        db_flush_packets_total.inc(len(batch))
        logger.info("Flushed %d packets to TimescaleDB", len(batch))
    except Exception:
        logger.exception("Failed to flush %d packets", len(batch))
