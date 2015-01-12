"""Add these files to the lexers/scintilla tree."""

import sys

def patchfile_applicable(config, filepath):
    if filepath.endswith("perf_no_abandon_paint.patch"):
        # Only apply on Darwin - bug 98677.
        return sys.platform == "darwin"
    return True

def remove(config):
    return [
        "lexers/LexTCL.cxx",
    ]

def add(config):
    return [
        ("cocoa", "cocoa"),
        ("cons", "."),
        ("lexers", "lexers", "force"),
        ("headless", "headless", "force"),
        ("include", "include", "force"),
    ]

