"""
Module to get the mozilla tree corresponding to a version number
"""

import urllib2, re, subprocess
import os.path
from subprocess import check_call
from distutils.version import LooseVersion, StrictVersion

try:
    from which import which
except ImportError:
    import sys
    sys.path.append(os.path.abspath("../../util"))
    from which import which
    sys.path.pop()

def getTreeFromVersion(version=None):
    """Get the tree name of the upstream Mozilla Mercurial repository from a
    given version number.
    @param version {str} The Mozilla version number, e.g. 7.0.1
    @returns {tuple of str} A tuple, consisting of two strings:
        - The name of the tree, e.g. "mozilla-release"
        - The name of the tag/hash to check out, e.g. "FIREFOX_7_0_1_RELEASE"
    @note This makes network requests
    """

    response = urllib2.urlopen("http://hg.mozilla.org/releases/mozilla-release/tags")

    if version is None:
        # use default
        version = "7.0.1"

    max_ver = 0.0
    tags = {}
    matcher = re.compile(r"(?P<tag>FIREFOX_(?P<version>(?:\d+_)*)RELEASE).*rev/(?P<hash>[0-9a-f]*)")
    for line in response.read().splitlines():
        if not "|" in line:
            continue
        for part in line.split("|"):
            matches = matcher.search(part)
            if not matches:
                continue
            ver = ".".join(matches.group("version").strip("_").split("_"))
            if not ver:
                # bad tag, e.g. "FIREFOX_RELEASE_5" - we don't care about that
                continue
            tags[ver] = matches.group("tag")
            ver = float(ver.split(".")[0])
            if ver > max_ver:
                max_ver = ver

    try:
        if not "." in version:
            # assume version string like "700" which should be mapped to "7.0.0"
            version = ("%s00" % (version))[:max(3,len(version))]
            version = ".".join((version[:-2], version[-2], version[-1]))
        ver = StrictVersion(version)
    except ValueError:
        ver = LooseVersion(version)
    for verstr, tag in tags.items():
        if ver == verstr:
            return ("mozilla-release", tag)
    ver = float(version.split(".")[0])
    if ver <= max_ver + 1:
        return ("mozilla-beta", "default")
    elif ver <= max_ver + 2:
        return ("mozilla-aurora", "default")
    return ("mozilla-central", "default")

def getRepoFromTree(tree):
    """Get the URL of a tree given its name"""
    if tree != "mozilla-central":
        tree = "releases/%s" % (tree,)
    return "http://hg.mozilla.org/%s" % (tree,)

def getBundleFromTree(tree):
    """Get the URL of a bundle given a tree name"""
    url = "http://ftp.mozilla.org/pub/mozilla.org/firefox/bundles/%s.hg" % (tree,)
    wget = which("wget")
    filename = os.path.abspath("%s.hg" % (tree,))
    check_call([wget, "--progress=dot:mega", "-O", filename, url])
    return filename

def cloneFromTree(tree, tag=None, dest="src"):
    """Clone the given tree
    @param tree {str} The name of the tree, e.g. "mozilla-release"
    @param tag {str} The tag to check out, e.g. "FIREFOX_7_0_1_RELEASE"
    @param dest {str} The directory to check out to
    """
    bundle = getBundleFromTree(tree)
    repo = os.path.abspath(dest)
    hg = which("hg")
    check_call([hg, "init", repo])
    check_call([hg, "--cwd", repo, "unbundle", bundle])
    fixRemoteRepo(tree, repo)
    check_call([hg, "--cwd", repo, "pull"])
    if tag is not None:
        check_call([hg, "--cwd", repo, "up", "--rev", tag])

def fixRemoteRepo(tree, repo):
    """Fix up the default remote repo URL for an unbundled repo
    @param tree {str} The name of the tree, e.g. "mozilla-release"
    @param repo {str} The path to the repo, e.g. "/temp/mozilla/src"
    """
    url = getRepoFromTree(tree)
    filename = os.path.join(repo, ".hg", "hgrc")
    from ConfigParser import RawConfigParser
    config = RawConfigParser()
    config.read([filename])
    if not config.has_section("paths"):
        config.add_section("paths")
    config.set("paths", "default", getRepoFromTree(tree))
    f = open(filename, "w")
    try:
        config.write(f)
    finally:
        f.close()

if __name__ == '__main__':
    import sys
    tree, tag = getTreeFromVersion((sys.argv + [None])[1])
    cloneFromTree(tree, tag=tag)
