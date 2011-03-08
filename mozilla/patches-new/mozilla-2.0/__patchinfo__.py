
"""Apply these patches to the Mozilla-Central Mercurial branch."""

def applicable(config):
    return hasattr(config, "mozVer") and config.mozVer == 2.00

def patch_args(config):
    # use -p1 to better match hg patches
    return ['-p1']

