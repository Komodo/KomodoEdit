"""Add these files to the src/scintilla tree."""

def remove(config):
    return [
        "src/LexTCL.cxx",
    ]

def add(config):
    return [
        ("cons", "."),
        ("src", "src", "force"),
    ]

