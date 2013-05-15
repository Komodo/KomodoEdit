
"""Apply these patches if the target mozApp is Komodo."""

def applicable(config):
    return config.mozApp == "komodo" and \
           config.patch_target == "komodoapp" and \
           config.mozVer >= 24.0 and config.mozVer <= 24.99


def add(config):
    return [
        # Copy the "komodo/..." tree to the top-level mozilla dir.
        ("komodo", "komodo"),
    ]

