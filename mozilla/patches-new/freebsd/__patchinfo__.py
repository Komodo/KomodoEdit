
"""Apply these patches on FreeBSD."""

def applicable(config):
    return config.platinfo["os"] == "freebsd"

