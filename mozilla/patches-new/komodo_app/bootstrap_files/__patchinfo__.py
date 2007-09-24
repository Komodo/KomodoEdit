
"""files to add to xpfe/bootstrap/..."""

import os

def applicable(config):
    #XXX Disable for now because (1) I don't think we need it anymore
    #    and (2) it currently would require an upgrade to patchtree.py
    #    to allow forcefull adds (presumably with an extra tuple arg
    #    "force").
    return False

def add(config):
    def bootdir(*p):
        return os.path.join("xpfe", "bootstrap", *p)
    return [
        ("InfoPlist.strings", bootdir("macbuild", "Contents", "Resources", "English.lproj")),
        ("Info.p.plist", bootdir("macbuild", "Contents")),
        ("komodo.icns", bootdir("macbuild", "Contents", "Resources")),
        ("komodo.ico", bootdir()),
        ("module.p.ver", bootdir()),
    ]

