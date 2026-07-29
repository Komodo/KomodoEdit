"""Pytest bootstrap for the codeintel3 regression suite.

`codeintel3` (and its siblings SilverCity/langinfo/styles) are only
importable as top-level packages once `qtedit/qtedit/` is on sys.path --
the same trick `codeintel3/oop_driver_main.py` uses for the real subprocess
launch (see that file's docstring). Done here, once, so every test module
under `tests/` can just `from codeintel3.manager import Manager` etc.
without repeating the path dance.
"""
import shutil
import sys
from pathlib import Path

_QTEDIT_PKG_DIR = Path(__file__).resolve().parent.parent / "qtedit"
if str(_QTEDIT_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_QTEDIT_PKG_DIR))

TEST_DB_BASE_DIR = Path(__file__).resolve().parent / "tmp-db-base-dir"


def pytest_configure(config):
    # Mirrors legacy test2/test.py's own setup step
    # (citestsupport.rmtree(test_db_base_dir)) -- a stale codeintel scan-
    # cache DB from a previous run/interrupted session could otherwise
    # mask real bugs (or cause spurious ones) in this run.
    shutil.rmtree(TEST_DB_BASE_DIR, ignore_errors=True)
