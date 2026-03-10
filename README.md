# Astro-Radio-Streamer

**High-throughput satellite telemetry ingestion system built with Python `asyncio`, TimescaleDB, and CCSDS-aligned domain modeling.**

[![CI](https://github.com/MateuszSzczukiewicz/Astro-Radio-Streamer/actions/workflows/ci.yml/badge.svg)](https://github.com/MateuszSzczukiewicz/Astro-Radio-Streamer/actions)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![Coverage 93%](https://img.shields.io/badge/coverage-93%25-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Overview

Astro-Radio-Streamer is an asynchronous, event-driven Proof of Concept simulating a real-world **space-to-ground telemetry pipeline**. It receives a raw TCP byte stream, synchronizes on custom frame markers, validates data integrity via CRC32, and persists validated telemetry into TimescaleDB — with full observability through Grafana and Prometheus.

The project demonstrates backend engineering practices relevant to satellite operations: handling fragmented, high-velocity data streams, performing protocol-level validation, managing high-frequency I/O without blocking, and monitoring system health in real time.

---

## Architecture

```
Ground Station (TCP :8888)
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│  Receiver (asyncio)                                          │
│                                                              │
│  StreamReader ──▶ FrameBuffer ──▶ asyncio.Queue ──▶ DB Worker│
│    (TCP I/O)      (ASM sync,       (backpressure     (batch  │
│                    CRC32 FECF       10k cap)          INSERT)│
│                    validation)                               │
└──────────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
   Prometheus           TimescaleDB            Grafana
   (:9091)              (:5432)                (:3000)
   app metrics          hypertable             Mission Control
                        30-day retention       dashboard
```

---

## CCSDS Domain Modeling

The type system is modeled after the **CCSDS Space Packet Protocol** (Consultative Committee for Space Data Systems), the standard used by NASA, ESA, and commercial space companies:

| CCSDS Concept | Code Representation | Description |
|---|---|---|
| **ASM** (Attached Sync Marker) | `ASM = b"\xAA\xBB"` | Bit pattern for frame synchronization in noisy RF streams |
| **APID** (Application Process Identifier) | `type APID = int` | Identifies the source instrument (camera, thermal sensor, etc.) |
| **Packet Data Field** | `type PacketDataField = bytes` | Raw sensor payload |
| **FECF** (Frame Error Control Field) | `type FECF = int` | CRC32 integrity check over the transfer frame |
| **Space Packet** | `SpacePacket` (frozen dataclass) | Immutable, slotted representation of a decoded packet |

---

## Key Features

### Protocol Engine
- **Custom CRC32** — Bit-by-bit implementation using polynomial `0xEDB88320` (no `zlib` dependency)
- **Frame synchronization** — ASM-based sync with support for split markers across TCP chunks
- **Zero-copy validation** — FECF computed over header + data field, compared against received checksum

### Resilience & Security
- **OOM guard** — Configurable `MAX_BUFFER_SIZE` (default 1 MB) prevents memory exhaustion from malformed streams
- **I/O timeouts** — `READ_TIMEOUT` closes stale connections (critical for satellite link drops)
- **Fuzz testing** — Boofuzz-based protocol fuzzer with CRC-aware mutation (`fuzzer.py`)

### Data Pipeline
- **Producer-Consumer pattern** — `asyncio.Queue` with 10,000-element backpressure cap
- **Batch INSERT** — Worker accumulates packets into batches of 100 (or flushes on 2s timeout)
- **Graceful shutdown** — Signal handlers drain the queue before closing the connection pool

### Observability
- **Grafana dashboard** — Auto-provisioned "Mission Control" with 3 panels:
  - Packet Ingest Rate (5s `time_bucket` bars)
  - Total Data Volume (cumulative bytes)
  - Recent Space Packets (live table with APID, payload size, FECF hex)
- **Prometheus metrics** — 7 application metrics:
  - `packets_received_total`, `packets_crc_failed_total`, `buffer_overflows_total`
  - `connections_active`, `queue_depth`
  - `db_flush_duration_seconds` (histogram), `db_flush_packets_total`

### Infrastructure
- **Docker Compose** — One-command stack: TimescaleDB + Grafana + Prometheus
- **Terraform IaC** — AWS production skeleton: VPC, ECS Fargate, ECR (immutable + CVE scan), RDS, CloudWatch
- **CI Pipeline** — 4-step GitHub Actions: Ruff (lint + format), MyPy (strict), Bandit (security), Pytest (53 tests, 90% gate)

---

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker & Docker Compose

### Run the Full Stack

```bash
git clone https://github.com/MateuszSzczukiewicz/Astro-Radio-Streamer.git
cd Astro-Radio-Streamer

# Start infrastructure (TimescaleDB + Grafana + Prometheus)
docker compose up -d

# Install dependencies
cp .env.example .env
uv sync

# Start the receiver
uv run astro-receiver

# In another terminal — send test packets
python3 -c "
import asyncio, random, struct

ASM = b'\xAA\xBB'
POLY = 0xEDB88320

def crc32(data):
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8): crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1
    return crc ^ 0xFFFFFFFF

def pkt(apid, payload):
    hdr = ASM + struct.pack('>IH', apid, len(payload))
    body = hdr[2:] + payload
    return hdr + payload + struct.pack('>I', crc32(body))

async def main():
    _, w = await asyncio.open_connection('127.0.0.1', 8888)
    for _ in range(200):
        w.write(pkt(random.randint(1,50), random.randbytes(random.randint(8,128))))
        await w.drain()
    w.close()

asyncio.run(main())
"
```

### Access

| Service | URL | Credentials |
|---|---|---|
| **Grafana** | http://localhost:3000 | `admin` / `admin` |
| **Prometheus** | http://localhost:9091 | — |
| **TimescaleDB** | `localhost:5432` | `astro` / `astro` / `telemetry` |
| **Receiver** | `localhost:8888` | TCP raw |
| **Metrics** | http://localhost:9090/metrics | Prometheus format |

---

## Project Structure

```
.
├── src/astro_radio_streamer/
│   ├── protocol/
│   │   ├── types.py          # APID, PacketDataField, FECF, ReceivedAt
│   │   ├── constants.py      # ASM, sizes, MIN_PACKET_SIZE
│   │   ├── crc.py            # Bit-level CRC32 (poly 0xEDB88320)
│   │   └── frame.py          # SpacePacket (frozen, slotted dataclass)
│   ├── receiver/
│   │   ├── buffer.py         # FrameBuffer — sync, parse, validate, OOM guard
│   │   ├── server.py         # asyncio TCP server with timeouts
│   │   └── __main__.py       # Entry point
│   ├── db/
│   │   ├── pool.py           # asyncpg connection pool
│   │   └── worker.py         # Batch INSERT consumer with flush histogram
│   ├── metrics.py            # Prometheus counters, gauges, histogram
│   └── fuzzer.py             # Boofuzz protocol-aware fuzzer
├── tests/                    # 53 tests, 93% coverage
├── infra/
│   ├── init.sql              # TimescaleDB schema (hypertable + retention)
│   ├── terraform/            # AWS IaC: VPC, ECS, RDS, ECR, CloudWatch
│   ├── grafana/              # Auto-provisioned datasources + dashboard
│   └── prometheus/           # Scrape configuration
├── docs/                     # Step-by-step design documentation (PL)
├── .github/workflows/ci.yml  # 4-step CI pipeline
├── docker-compose.yml        # Full observability stack
├── .env.example              # All configurable environment variables
└── pyproject.toml            # uv/pip, ruff, mypy, pytest, coverage config
```

---

## Configuration

All runtime parameters are configurable via environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://astro:astro@localhost:5432/telemetry` | TimescaleDB connection string |
| `RECEIVER_HOST` | `0.0.0.0` | TCP bind address |
| `RECEIVER_PORT` | `8888` | TCP listen port |
| `READ_TIMEOUT` | `10.0` | Seconds before closing idle connection |
| `BATCH_SIZE` | `100` | Packets per DB batch INSERT |
| `FLUSH_TIMEOUT` | `2.0` | Force flush after N seconds even if batch is incomplete |
| `MAX_BUFFER_SIZE` | `1048576` | Buffer OOM guard threshold (bytes) |

---

## CI Pipeline

Every push to `main` and every Pull Request passes 4 parallel checks:

| Step | Tool | Purpose |
|---|---|---|
| Lint & Format | **Ruff** | PEP 8 compliance, unused imports, consistent formatting |
| Type Check | **MyPy** (strict) | Static analysis of CCSDS domain type aliases |
| Security Scan | **Bandit** | Hardcoded secrets, unsafe bindings, dangerous functions |
| Unit Tests | **Pytest** | 53 tests, 93% coverage, 90% gate |

---

## Testing

```bash
# Run all tests with coverage
uv run pytest tests/ -v --cov --cov-report=term-missing

# Lint + type check
uv run ruff check src/ tests/
uv run mypy src/astro_radio_streamer/ --ignore-missing-imports

# Security scan
uv run bandit -r src/astro_radio_streamer/

# Fuzz testing (requires running receiver)
uv run astro-fuzzer
```

---

## Technologies

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Concurrency | `asyncio` (event loop, non-blocking I/O) |
| Database | PostgreSQL 17 + TimescaleDB (hypertables, `time_bucket`, retention policies) |
| Observability | Grafana (dashboards) + Prometheus (application metrics) |
| Fuzz Testing | Boofuzz (protocol-aware mutation) |
| CI | GitHub Actions (Ruff, MyPy, Bandit, Pytest) |
| IaC | Terraform (AWS: VPC, ECS Fargate, RDS, ECR, CloudWatch) |
| Containerization | Docker, Docker Compose |
| Package Management | uv |

---

## License

MIT
