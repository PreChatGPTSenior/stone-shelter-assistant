# Local infrastructure

Adapted from the Java project's compose.yaml and MinIO Dockerfile. Kafka, the Java API and the Java-linked UI service are excluded. PostgreSQL/pgvector, Redis and MinIO retain the source image selections. The Python API runs on the host with uv. Ollama runs separately on the host, as in the source setup.

## Startup and checks

A local ignored `.env` supplies credentials. For a fresh checkout, copy `.env.example` to `.env` and replace both password placeholders. Do not commit `.env`.

```sh
docker compose config --quiet
docker compose up -d --wait
docker compose ps
```

Start only the database when needed with `docker compose up -d --wait postgres`. Stop services with `docker compose stop`; `docker compose down` removes containers and the network but retains named volumes. Avoid `docker compose down -v` unless intentionally deleting this project's infrastructure data.

## Host endpoints

| Service | Default address |
| --- | --- |
| PostgreSQL | 127.0.0.1:55432 |
| Redis | 127.0.0.1:56379 |
| MinIO S3 API | http://127.0.0.1:59000 |
| MinIO console | http://127.0.0.1:59001 |
| Ollama (separate host installation) | http://127.0.0.1:11434 |

All published ports bind to loopback. The default Compose project name is `stone-shelter-assistant`; its network and volumes are separate from the Java project. Image layers may be shared, but data volumes are not. Redis persistence is disabled; Redis data does not survive container replacement.

PostgreSQL data is mounted at `/var/lib/postgresql`, matching the PostgreSQL 18 image layout. The image contains pgvector binaries, but the database extension must be enabled later through an explicit migration. No business tables, application migrations, buckets or reference documents are created by this setup.

## Python integration to implement later

Use the host endpoints above when running the API through uv. Compose reads `.env` for variable interpolation; Python does not automatically read it. Configure pydantic-settings, the SQLAlchemy async engine/session factory, and Alembic separately. Build the SQLAlchemy connection URL from individual fields using URL.create rather than manually interpolating a password. The driver name is `postgresql+asyncpg`.

Future Redis and S3 clients will use these same environment settings. MinIO root credentials are for isolated local development; add restricted application credentials when implementing storage permissions. No Python Redis, S3 or model dependencies are installed by Compose.

MinIO can reuse the existing local image. If absent, Compose builds `infra/minio/Dockerfile`, which verifies the downloaded release binary checksum. A successful build of that fallback path must be checked separately when needed. Ollama models are not downloaded by this setup.
