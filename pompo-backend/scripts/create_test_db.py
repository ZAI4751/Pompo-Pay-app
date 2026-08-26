"""Create the isolated test database (pompo_test), if it doesn't already exist.

Run this once per environment before running the test suite against a real
PostgreSQL instance — Docker Compose only provisions the *development*
database (`POSTGRES_DB=pompo` in docker-compose.yml); the test database is
deliberately separate (see docs/testing.md) so running tests never touches
dev data, and nothing in the Docker stack creates it automatically.

Usage (from inside the backend container, or any shell that can reach the
Postgres server named in --url):

    python scripts/create_test_db.py \
        --url postgresql://pompo:pompo_secret@postgres:5432/postgres \
        --database pompo_test

Connects to Postgres's own `postgres` maintenance database (never to the
database being created — you cannot CREATE DATABASE while connected to it)
using asyncpg directly rather than SQLAlchemy: CREATE DATABASE cannot run
inside a transaction block, which SQLAlchemy's async engine wraps requests
in by default, so the lower-level driver is the simpler and more correct
tool for this one-off administrative statement.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import asyncpg


async def create_database_if_missing(maintenance_url: str, database_name: str) -> bool:
    """Create ``database_name`` if it doesn't exist. Returns True if created."""
    # asyncpg wants a plain postgres:// DSN, not SQLAlchemy's postgresql+asyncpg://
    dsn = maintenance_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", database_name
        )
        if exists:
            return False
        # Table/database identifiers can't be parameterized — database_name
        # comes from our own --database CLI flag (operator-controlled, not
        # user input), and is quoted defensively regardless.
        safe_name = database_name.replace('"', '""')
        await conn.execute(f'CREATE DATABASE "{safe_name}"')
        return True
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        required=True,
        help="Maintenance connection URL, pointed at the 'postgres' database "
        "(e.g. postgresql://pompo:pompo_secret@postgres:5432/postgres)",
    )
    parser.add_argument("--database", default="pompo_test", help="Database name to create")
    args = parser.parse_args()

    created = asyncio.run(create_database_if_missing(args.url, args.database))
    if created:
        print(f"Created database: {args.database}")
    else:
        print(f"Database already exists, nothing to do: {args.database}")
    sys.exit(0)


if __name__ == "__main__":
    main()
