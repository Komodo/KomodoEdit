
"""Apply these patches if the target mozApp is Komodo."""

def applicable(config):
    return config.mozApp == "komodo"

def add(config):
    return [
        # Copy the "komodo/..." tree to the top-level mozilla dir.
        ("komodo", "komodo"),
    ]

