
"""Apply these patches if the target mozApp is Komodo."""

import os, shutil

def applicable(config):
    return config.mozApp == "komodo"

def add(config):
    base = os.path.dirname(__file__)
    if float(config.mozVer) >= 1.9:
        src = os.path.join(base, "Makefile-trunk.in")
    else:
        src = os.path.join(base, "Makefile-18.in")
    shutil.copy(src, os.path.join(base, "Makefile.in"))
        
    return [
        # Copy the "komodo/..." tree to the top-level mozilla dir.
        ("Makefile.in", os.path.join("komodo","app")),
    ]

