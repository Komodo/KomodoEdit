"""Minimal compat shim for the legacy `util/testlib.py` import surface that
`test_python.py` needs -- NOT a port of the real ~725-line testlib.py
(generic ActiveState test-discovery/runner framework). pytest already
provides discovery, skip handling, and xfail marking, so only the four
names test_python.py actually imports are reproduced here, mapped onto
pytest's equivalents.
"""
import unittest

import pytest


class TestError(Exception):
    pass


class TestFailed(AssertionError):
    pass


class TestSkipped(unittest.SkipTest):
    pass


def tag(*tags):
    """Legacy `@tag(...)` only ever needs one real effect ported here: the
    "knownfailure" tag, which test2/test.py's runner excluded by default
    (default_tags=["-knownfailure","-xpcom"]) -- mapped to pytest's
    equivalent, `xfail`, so those cases still run (and are flagged if they
    unexpectedly start passing) rather than silently vanishing. Bug-number
    tags (the vast majority) are purely informational in the original
    harness and are dropped rather than registered as pytest markers."""

    def decorator(func):
        if "knownfailure" in tags:
            return pytest.mark.xfail(
                reason="ported from legacy @tag(\"knownfailure\")", strict=False
            )(func)
        return func

    return decorator
