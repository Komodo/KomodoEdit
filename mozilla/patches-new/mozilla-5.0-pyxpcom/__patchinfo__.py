
"""Apply these patches to the PyXPCOM Mercurial repository (default branch)."""

def applicable(config):
    return hasattr(config, "mozVer") and config.mozVer == 5.0

def patch_args(config):
    # patch $topsrcdir/extensions/python
    return ['-d', 'extensions/python', '-p1']

