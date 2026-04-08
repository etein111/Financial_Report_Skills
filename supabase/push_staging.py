#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
from pathlib import Path


PROJECT_REF = "ckkpgowyadrdbdqaoymr"
SUPABASE_ACCESS_TOKEN = "***REMOVED-SUPABASE-PAT***"
STAGING_DB_PASSWORD = "pwd4neolyst"


def run_step(label: str, args: list[str], project_root: Path) -> None:
    print(label)
    env = os.environ.copy()
    env["SUPABASE_ACCESS_TOKEN"] = SUPABASE_ACCESS_TOKEN
    subprocess.run(args, cwd=project_root, env=env, check=True)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    run_step(
        f"[1/3] link staging project: {PROJECT_REF}",
        [
            "supabase",
            "link",
            "--project-ref",
            PROJECT_REF,
            "--password",
            STAGING_DB_PASSWORD,
        ],
        project_root,
    )

    run_step(
        "[2/3] check linked migrations",
        ["supabase", "migration", "list", "--linked"],
        project_root,
    )

    run_step(
        "[3/3] push migrations and seed",
        ["supabase", "db", "push", "--include-seed", "--yes"],
        project_root,
    )

    print(f"staging push completed: {PROJECT_REF}")


if __name__ == "__main__":
    main()
