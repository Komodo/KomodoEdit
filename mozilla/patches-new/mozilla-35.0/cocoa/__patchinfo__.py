
"""Apply these patches to the Mozilla Mercurial checkout."""

import sys

def applicable(config):
    return config.mozVer == 35.0 and \
           config.patch_target == "mozilla" and \
           sys.platform == 'darwin'

def patch_args(config):
    # use -p1 to better match hg patches
    return ['-p1']

