from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import asyncpg

if TYPE_CHECKING:
    from asyncpg import Pool

logger = logging.getLogger(__name__)

DSN = "postgresql://astro:astro@localhost:5432/telemetry"


async def create_pool(dsn: str = DSN) -> Pool:
    pool: Pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
    logger.info("Connection pool created (%s)", dsn.split("@")[1])
    return pool
