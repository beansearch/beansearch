#!/usr/bin/env python3

from git import Repo
import logging

logging.basicConfig(level=logging.INFO)

repo = Repo(".")
expected_changes = sorted([".history", "3bs.db"])


if sorted([item.a_path for item in repo.index.diff(None)]) == expected_changes:
    repo.git.add(expected_changes)
    repo.index.commit("Episode Updates")
    repo.remote().push()
