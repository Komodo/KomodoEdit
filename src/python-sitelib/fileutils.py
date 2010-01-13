import os
from os.path import islink, realpath, join

def _walk_avioiding_cycles(top, topdown=True, onerror=None, followlinks=False):
    seen_rpaths = {top: 1}
    for root, dirs, files in os.walk(top, topdown, onerror, followlinks):
        # We modify the original "dirs" list, so that os.walk will then ignore
        # the directories we've removed.
        for dir in dirs[:]:  # a copy, so we can modify in-place.
            dirpath = join(root, dir)
            if islink(dirpath):
                rpath = realpath(dirpath)
                if rpath in seen_rpaths:
                    #print "Found cyclical path: %s to %s" % (dirpath, rpath)
                    dirs.remove(dir)
                    continue
                seen_rpaths[rpath] = 1
        yield (root, dirs, files)

def walk_avioiding_cycles(top, topdown=True, onerror=None, followlinks=False):
    """Modified os.walk, one that will keep track of followed symlinks in order
    to avoid cyclical links."""

    if not followlinks:
        return os.walk(top, topdown, onerror, followlinks)
    else:
        # Can only avoid cycles if topdown is True.
        if not topdown:
            raise Exception("walk_avioiding_cycles can only avoid cycles when "
                            "topdown is True")
        return _walk_avioiding_cycles(top, topdown, onerror, followlinks)
