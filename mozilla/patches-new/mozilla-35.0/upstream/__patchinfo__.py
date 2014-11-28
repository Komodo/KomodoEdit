
"""Apply these patches to the Mozilla Mercurial checkout.

These patches come from upstream repository (like mozilla-central). It should be
safe to drop these patches when next upgrading Komodo.
"""

def applicable(config):
    return config.mozVer == 35.0 and \
           config.patch_target == "mozilla"

def patch_args(config):
    # use -p1 to better match hg patches
    return ['-p1']

