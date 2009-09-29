
"""Apply these patches to the Mozilla Mercurial 1.9.1 branch."""

def applicable(config):
    return hasattr(config, "mozVer") and config.mozVer == 1.91
