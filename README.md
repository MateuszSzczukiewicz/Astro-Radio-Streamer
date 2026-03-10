# Astro-Radio-Streamer

## High-Throughput Telemetry Ingestion Simulator

Astro-Radio-Streamer is an asynchronous, event-driven Proof of Concept (PoC) designed to simulate the unpredictable nature of raw space-to-ground radio communication and demonstrate robust backend engineering practices. It focuses on handling fragmented, high-velocity telemetry data streams, performing real-time validation, and efficiently storing the results in a time-series optimized database.

This project was built to address common challenges in satellite operations, such as handling irregular data bursts, verifying data integrity at the protocol level, and managing high-frequency I/O operations without blocking the main execution thread.

## Key Features & Architecture

- **Asynchronous I/O Pipeline (asyncio):** The core ingestion engine utilizes Python's `asyncio` to read from simulated radio streams non-blockingly. This ensures the system remains highly responsive even when dealing with thousands of concurrent or fragmented data packets.
- **Custom Frame Demultiplexing & Validation:** Implements a robust buffer-scanning mechanism that identifies sync bytes, extracts frames based on dynamic length payloads, and validates them against a custom CRC32 implementation (inspired by standard space protocols like ESTTC).
- **Chaos Engineering (The Simulator):** Features a dedicated hardware simulator script that intentionally introduces network chaos. It generates telemetry frames but delivers them unpredictably—sending partial frames, introducing random delays, and generating sudden bursts of 100+ frames to stress-test the backend receiver.
- **Time-Series Database Integration:** Utilizes TimescaleDB (built on PostgreSQL) for efficient storage of telemetry data. The backend implements a batching mechanism to aggregate validated frames and insert them into a Hypertable, optimizing write performance for time-stamped metrics.
- **Containerized Environment:** The entire infrastructure, including the database, the chaotic simulator, and the asynchronous receiver, is orchestrated using Docker and docker-compose, ensuring a reproducible and isolated execution environment.

## Technologies Used

- **Language:** Python 3.13
- **Concurrency:** `asyncio` (Event Loop, Non-blocking I/O)
- **Database:** PostgreSQL with TimescaleDB extension
- **Infrastructure:** Docker, Docker Compose
- **Core Concepts Demonstrated:** Custom CRC32 validation, Buffer management, Batch processing, Type Aliasing for domain modeling.
