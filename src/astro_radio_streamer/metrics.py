from prometheus_client import Counter, Gauge, Histogram, start_http_server

METRICS_PORT = 9090

packets_received_total = Counter(
    "packets_received_total",
    "Total valid CCSDS packets decoded",
)

packets_crc_failed_total = Counter(
    "packets_crc_failed_total",
    "Packets rejected due to FECF mismatch",
)

buffer_overflows_total = Counter(
    "buffer_overflows_total",
    "Buffer overflow events (OOM guard triggered)",
)

connections_active = Gauge(
    "connections_active",
    "Currently open TCP connections",
)

queue_depth = Gauge(
    "queue_depth",
    "Packets waiting in asyncio.Queue",
)

db_flush_duration_seconds = Histogram(
    "db_flush_duration_seconds",
    "Time spent flushing a batch to TimescaleDB",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

db_flush_packets_total = Counter(
    "db_flush_packets_total",
    "Total packets successfully flushed to TimescaleDB",
)


def start_metrics_server(port: int = METRICS_PORT) -> None:
    start_http_server(port)
