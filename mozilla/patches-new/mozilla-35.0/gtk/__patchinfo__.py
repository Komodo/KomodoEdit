
"""Apply these patches to the Mozilla Mercurial checkout."""

from os.path import basename, exists
import sys

def applicable(config):
    return config.mozVer == 35.0 and \
           config.patch_target == "mozilla" and \
           sys.platform.startswith('linux')

def patchfile_applicable(config, filepath):
    if basename(filepath) == "centos_buildflags.patch":
        if exists("/etc/redhat-release"):
            contents = file("/etc/redhat-release").read()
            if "CentOS release 6." in contents:
                return True
        return False
    return True

def patch_args(config):
    # use -p1 to better match hg patches
    return ['-p1']

