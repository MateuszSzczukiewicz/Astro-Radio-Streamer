from unittest.mock import patch, MagicMock

from astro_radio_streamer.receiver.__main__ import main


class TestMain:
    def test_main_calls_asyncio_run(self) -> None:
        with patch(
            "astro_radio_streamer.receiver.__main__.asyncio"
        ) as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()
