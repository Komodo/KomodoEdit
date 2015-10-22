#!/usr/bin/env python

"""
Generate a headless Scintilla makefile from the original platform makefile.
"""

import sys
from os.path import join
import shutil

if sys.platform == "win32":
    # scintilla.mak depends on Scintilla.def and ScintRes.rc
    shutil.copy(join("..", "win32", "Scintilla.def"), "Scintilla.def")
    file("Scintilla.def", "a+").write("\n\tscintilla_new\n\tscintilla_send_message")
    shutil.copy(join("..", "win32", "ScintRes.rc"), "ScintRes.rc")
    plat_makefile = join("..", "win32", "scintilla.mak")
    contents = file(plat_makefile).read()
    # Change names and remove unused parts.
    contents = contents.replace("Win.obj", "Headless.obj")
    contents = contents.replace("WinL.obj", "HeadlessL.obj")
    contents = contents.replace("WinS.obj", "HeadlessS.obj")
    contents = contents.replace("Win.cxx", "Headless.cxx")
    contents = contents.replace("$(DIR_O)\\HanjaDic.obj", "")
    contents = contents.replace("../src/ScintillaBase.h \\\n	PlatWin.h", "../src/ScintillaBase.h")
    contents = contents.replace("../src/ScintillaBase.h \\\n	HanjaDic.h", "../src/ScintillaBase.h")

    # Change library name.
    contents = contents.replace("SciLexer.dll", "ScintillaHeadless.dll")
    # Write new makefile
    file("scintilla.mak", "w").write(contents)
elif sys.platform == "darwin":
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
    contents = contents.replace("ScintillaWrapGTK.o", "")
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
