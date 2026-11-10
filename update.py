#!/usr/bin/env python3
"""Commit and push the files transcribe.py updates.

Run from cron straight after transcribe.py. Commits whichever of .history
and 3bs.db have changed, then pushes main to origin.
"""

import logging
import os
import subprocess
import sys
from typing import List

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

REPO_DIR: str = os.path.dirname(os.path.abspath(__file__))
BRANCH: str = "main"
EXPECTED_CHANGES: List[str] = [".history", "3bs.db"]


def git(*args: str) -> str:
    """Run git in the repo, raising CalledProcessError on a non-zero exit."""
    return subprocess.run(
        ("git", *args),
        cwd=REPO_DIR,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.rstrip("\n")


def changed_files() -> List[str]:
    """Tracked files with modifications, staged or not. Untracked are ignored."""
    status: str = git("status", "--porcelain", "--untracked-files=no")
    # Porcelain v1 is fixed-width: two status columns, a space, then the path.
    return sorted(line[3:] for line in status.splitlines())


def main() -> int:
    changed: List[str] = changed_files()
    unexpected: List[str] = [f for f in changed if f not in EXPECTED_CHANGES]

    # Only the episode data is ever committed. Anything else in the working
    # tree means a human was in here, so leave the lot alone and complain.
    if unexpected:
        logging.error("Unexpected changes, not committing: %s", ", ".join(changed))
        return 1

    if changed:
        logging.info("Committing %s", ", ".join(changed))
        git("add", "--", *changed)
        git("commit", "-m", "Episode Updates")
    else:
        logging.info("No episode updates to commit.")

    # Push anything local that origin hasn't got, not just this run's commit.
    pending: int = int(git("rev-list", "--count", f"origin/{BRANCH}..{BRANCH}"))
    if not pending:
        logging.info("Nothing to push.")
        return 0

    logging.info("Pushing %d commit(s) to origin/%s", pending, BRANCH)
    git("push", "origin", BRANCH)
    logging.info("Pushed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(
            "%s failed (exit %d): %s",
            " ".join(e.cmd),
            e.returncode,
            (e.stderr or e.stdout or "").strip(),
        )
        sys.exit(1)
