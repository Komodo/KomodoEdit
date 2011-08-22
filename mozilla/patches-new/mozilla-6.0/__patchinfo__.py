
"""Apply these patches to the Mozilla-Central Mercurial branch."""

def applicable(config):
    return hasattr(config, "mozVer") and config.mozVer == 6.0

def patch_args(config):
    # use -p1 to better match hg patches
    return ['-p1']

def patchfile_applicable(config, filepath):
    if filepath.endswith("msys-perl-always.patch"):
        # Only apply when running in Windows msys environment.
        import os
        import sys
        if sys.platform.startswith("win") and os.environ.has_key("MSYSTEM"):
            return True
        return False
    return True

