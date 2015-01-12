"""Add these files to the lexers/scintilla tree."""

import sys

def patchfile_applicable(config, filepath):
    if filepath.startswith("win32") and not sys.platform.startswith("win32"):
        return False
    if filepath.startswith("gtk") and not sys.platform.startswith("linux"):
        return False
    if filepath.startswith("cocoa") and sys.platform != "darwin":
        return False
    return True

def remove(config):
    return [
        "lexers/LexTCL.cxx",
    ]

def add(config):
    manifest = [
        ("copy/lexers", "lexers", "force"),
        ("copy/headless", "headless", "force"),
        ("copy/include", "include", "force"),
    ]

    if sys.platform.startswith("win"):
        manifest.append(("copy/win32", "win32", "force"))
    elif sys.platform.startswith("linux"):
        manifest.append(("copy/gtk", "gtk", "force"))
    elif sys.platform == "darwin":
        manifest.append(("copy/cocoa", "cocoa", "force"))
    else:
        raise RuntimeError("Unexpected platform %r" % (sys.platform))

    return manifest
