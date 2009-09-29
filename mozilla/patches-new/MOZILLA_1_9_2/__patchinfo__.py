
"""Apply these patches to the Mozilla Mercurial 1.9.2 branch."""

def applicable(config):
    return hasattr(config, "mozVer") and config.mozVer == 1.92
