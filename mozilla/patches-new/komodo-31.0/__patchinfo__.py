
"""Apply these patches if the target mozApp is Komodo."""

def applicable(config):
    return config.mozApp == "komodo" and \
           config.patch_target == "komodoapp" and \
           config.mozVer == 31.0


def add(config):
    return [
        # Copy the "komodo/..." tree to the top-level mozilla dir.
        ("komodo", "komodo"),
    ]

