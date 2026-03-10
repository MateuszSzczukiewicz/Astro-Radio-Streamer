import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from astro_radio_streamer.db.pool import DSN, create_pool
from astro_radio_streamer.db.worker import (
    BATCH_SIZE,
    FLUSH_TIMEOUT,
    INSERT_SQL,
    _flush,
    db_worker,
)
from astro_radio_streamer.protocol.frame import TelemetryFrame


def _frame(fid: int = 1) -> TelemetryFrame:
    return TelemetryFrame(
        frame_id=fid,
        payload=b"\x01\x02",
        checksum=0xDEAD,
        received_at=datetime.now(UTC),
    )


class TestPool:
    def test_dsn_default(self) -> None:
        assert "astro" in DSN
        assert "telemetry" in DSN
        assert "5432" in DSN

    @pytest.mark.asyncio
    async def test_create_pool_calls_asyncpg(self) -> None:
        mock_pool = MagicMock()

        async def fake_create_pool(**kwargs):  # noqa: ANN003, ANN202
            return mock_pool

        with patch(
            "astro_radio_streamer.db.pool.asyncpg.create_pool",
            side_effect=fake_create_pool,
        ):
            pool = await create_pool("postgresql://test:test@localhost/test")
            assert pool is mock_pool


class TestWorkerConstants:
    def test_defaults(self) -> None:
        assert BATCH_SIZE == 100
        assert FLUSH_TIMEOUT == 2.0
        assert "$1" in INSERT_SQL


class TestFlush:
    @pytest.mark.asyncio
    async def test_successful_flush(self) -> None:
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock())
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        batch = [_frame(1), _frame(2)]
        await _flush(mock_pool, batch)
        mock_conn.executemany.assert_awaited_once()
        args = mock_conn.executemany.call_args
        assert len(args[0][1]) == 2

    @pytest.mark.asyncio
    async def test_flush_exception_logged(self) -> None:
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock())
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            side_effect=ConnectionError("db down")
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        await _flush(mock_pool, [_frame(1)])


class TestDbWorker:
    @pytest.mark.asyncio
    async def test_flush_on_timeout(self) -> None:
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock())
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(_frame(1))
        queue.put_nowait(_frame(2))

        task = asyncio.create_task(db_worker(mock_pool, queue))
        await asyncio.sleep(FLUSH_TIMEOUT + 0.5)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_conn.executemany.assert_awaited_once()
        args = mock_conn.executemany.call_args
        assert len(args[0][1]) == 2

    @pytest.mark.asyncio
    async def test_flush_on_batch_size(self) -> None:
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock())
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        queue: asyncio.Queue = asyncio.Queue()
        for i in range(BATCH_SIZE):
            queue.put_nowait(_frame(i))

        task = asyncio.create_task(db_worker(mock_pool, queue))
        await asyncio.sleep(0.5)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_conn.executemany.assert_awaited_once()
        args = mock_conn.executemany.call_args
        assert len(args[0][1]) == BATCH_SIZE

    @pytest.mark.asyncio
    async def test_empty_queue_no_flush(self) -> None:
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock())
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        queue: asyncio.Queue = asyncio.Queue()

        task = asyncio.create_task(db_worker(mock_pool, queue))
        await asyncio.sleep(FLUSH_TIMEOUT + 0.5)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_conn.executemany.assert_not_awaited()
