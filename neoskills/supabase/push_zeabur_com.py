#!/usr/bin/env python3

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ZEBUR_CONFIG = _PROJECT_ROOT / "supabase" / "staging.json"


def _load_zeabur_config() -> dict:
    if not _ZEBUR_CONFIG.exists():
        raise FileNotFoundError(
            f"Zeabur config not found: {_ZEBUR_CONFIG}\n"
            "Create it with: {\"host\":..., \"port\":..., \"user\":..., \"password\":..., \"dbname\":...}"
        )
    return json.loads(_ZEBUR_CONFIG.read_text())


_cfg = _load_zeabur_config()
DB_HOST = _cfg["host"]
DB_PORT = _cfg["port"]
DB_USER = _cfg["user"]
DB_PASS = _cfg["password"]
DB_NAME = _cfg["dbname"]


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
    project_root = Path(__file__).resolve().parents[1]
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
        if not re.fullmatch(r"\d+", version):
            raise ValueError(f"invalid migration version: {fname}")

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
