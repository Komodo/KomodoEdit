
"""Apply these patches to the PyXPCOM Mercurial repository (default branch)."""

def applicable(config):
    return config.mozVer == 35.0 and \
           config.patch_target == "pyxpcom"

def patch_args(config):
    # patch $topsrcdir/extensions/python
    return ['-p1']

