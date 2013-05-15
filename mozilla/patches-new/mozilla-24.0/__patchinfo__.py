
"""Apply these patches to the Mozilla Mercurial checkout."""

def applicable(config):
    return config.mozVer >= 24.0 and config.mozVer <= 24.99 and \
           config.patch_target == "mozilla"

def patch_args(config):
    # use -p1 to better match hg patches
    return ['-p1']

