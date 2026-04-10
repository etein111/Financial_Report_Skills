#!/usr/bin/env python3

from __future__ import annotations

import glob
import os
import subprocess
from pathlib import Path


DB_HOST = "47.239.121.31"
DB_PORT = "31439"
DB_USER = "supabase_admin"
DB_PASS = "u9hI31H68ozy42B5cKde0nRfxGjYiLr7"
DB_NAME = "postgres"


def psql_env() -> dict:
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASS
    return env


PSQL_BASE = [
    "psql",
    "-h",
    DB_HOST,
    "-p",
    DB_PORT,
    "-U",
    DB_USER,
    "-d",
    DB_NAME,
    "-v",
    "ON_ERROR_STOP=1",
]


def query_one(sql: str) -> str:
    r = subprocess.run(
        PSQL_BASE + ["-t", "-A", "-c", sql],
        env=psql_env(),
        check=True,
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


def exec_sql(sql: str) -> None:
    subprocess.run(
        PSQL_BASE + ["-c", sql],
        env=psql_env(),
        check=True,
    )


def exec_file(fpath: str) -> None:
    subprocess.run(
        PSQL_BASE + ["-f", fpath],
        env=psql_env(),
        check=True,
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    migration_dir = project_root / "supabase" / "migrations"

    migration_files = sorted(glob.glob(str(migration_dir / "*.sql")))
    if not migration_files:
        print("no migration files found")
        return

    print("[1/2] ensuring supabase_migrations.schema_migrations table exists")
    exec_sql("CREATE SCHEMA IF NOT EXISTS supabase_migrations")
    exec_sql("""
        CREATE TABLE IF NOT EXISTS supabase_migrations.schema_migrations (
            version text NOT NULL PRIMARY KEY,
            statements text[],
            name text
        )
    """)

    print(f"[2/2] applying {len(migration_files)} migration(s)")
    for fpath in migration_files:
        fname = Path(fpath).name
        version = fname.split("_")[0]

        count = query_one(
            f"SELECT count(*) FROM supabase_migrations.schema_migrations WHERE version = '{version}'"
        )
        if count != "0":
            print(f"  skip (already applied): {fname}")
            continue

        print(f"  applying: {fname}")
        exec_file(fpath)
        exec_sql(
            f"INSERT INTO supabase_migrations.schema_migrations (version, name) VALUES ('{version}', '{fname}')"
        )

    print("zeabur push completed")


if __name__ == "__main__":
    main()
