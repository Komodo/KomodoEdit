"""Add these files to the lexers/scintilla tree."""

import sys

def patchfile_applicable(config, filepath):
    return True

def remove(config):
    return [
        "lexers/LexTCL.cxx",
    ]

def add(config):
    return [
        ("cons", "."),
        ("lexers", "lexers", "force"),
        ("headless", "headless", "force"),
        ("include", "include", "force"),
    ]

