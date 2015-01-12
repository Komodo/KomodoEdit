#!/usr/bin/env python

"""
Generate a headless Scintilla makefile from the original platform makefile.
"""

import sys
from os.path import join
import shutil

if sys.platform == "darwin":
    # makefile depends on deps.mak
    shutil.copy(join("..", "cocoa", "deps.mak"), "deps.mak")
    plat_makefile = join("..", "cocoa", "makefile")
    contents = file(plat_makefile).read()
    # Change names and remove unused parts.
    contents = contents.replace("Cocoa.o", "Headless.o")
    contents = contents.replace("ScintillaView.o", "")
    contents = contents.replace("InfoBar.o", "")
    # Ensure symbols are hidden.
    contents = contents.replace("-DSCI_LEXER", "-DSCI_LEXER -fvisibility=hidden")
    # Change library name.
    contents = contents.replace("scintilla.a", "headlessscintilla.a")
    # Write new makefile
    file("makefile", "w").write(contents)
elif sys.platform.startswith("linux"):
    # makefile depends on deps.mak
    shutil.copy(join("..", "gtk", "deps.mak"), "deps.mak")
    plat_makefile = join("..", "gtk", "makefile")
    contents = file(plat_makefile).read()
    # Change names and remove unused parts.
    contents = contents.replace("GTK.o", "Headless.o")
    contents = contents.replace("scintilla-marshal.o", "")
    # Ensure symbols are hidden.
    contents = contents.replace("-DSCI_LEXER", "-DSCI_LEXER -fvisibility=hidden")
    # Change library name.
    contents = contents.replace("scintilla.a", "headlessscintilla.a")
    # Write new makefile
    file("makefile", "w").write(contents)
else:
    sys.stderr.write("Unhandled platform: %r", sys.platform)
    sys.exit(-2)
