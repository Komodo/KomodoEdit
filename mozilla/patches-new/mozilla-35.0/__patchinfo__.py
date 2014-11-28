
"""Apply these patches to the Mozilla Mercurial checkout.

Note that any patches that have an "_ide.patch" suffix only apply for Komodo
IDE, and these patches will not be included in the mozilla-patches.zip that gets
added to the main downloads area.
"""

def applicable(config):
    return config.mozVer == 35.0 and \
           config.patch_target == "mozilla"

def patch_args(config):
    # use -p1 to better match hg patches
    return ['-p1']

