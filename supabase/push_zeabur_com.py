#!/usr/bin/env python3

from __future__ import annotations

import subprocess
from pathlib import Path


DB_URL = "postgresql://supabase_admin:u9hI31H68ozy42B5cKde0nRfxGjYiLr7@47.239.121.31:31439/postgres"


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent

    print("[1/1] push migrations to Zeabur Supabase")
    subprocess.run(
        ["supabase", "db", "push", "--db-url", DB_URL],
        cwd=project_root,
        check=True,
    )

    print("zeabur push completed")


if __name__ == "__main__":
    main()
