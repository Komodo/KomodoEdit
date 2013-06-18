"""
Module to get the mozilla tree corresponding to a version number
"""

import logging
import urllib2, re, subprocess
import os.path
from subprocess import check_call
from distutils.version import LooseVersion, StrictVersion

log = logging.getLogger("get_mozilla_tree")

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
    log.debug("Getting tree for version %s", version)

    if version is None:
        # use default
        version = "7.0.1"

    # Prefer a specific tag in mozilla-release
    response = urllib2.urlopen("http://hg.mozilla.org/releases/mozilla-release/tags")

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

    log.debug("tags: %r", tags)
    log.debug("mozilla_release is at: %s", max_ver)

    try:
        if not "." in version:
            matches = re.match(r"FIREFOX_(?P<version>(?:\d+_)*)RELEASE", version)
            if matches:
                # version is a tag, FIREFOX_0_0_0_RELEASE
                version = ".".join(matches.group("version").strip("_").split("_"))
            else:
                # assume version string like "700" which should be mapped to "7.0.0"
                version = ("%s00" % (version))[:max(3,len(version))]
                version = ".".join((version[:-2], version[-2], version[-1]))
        wanted_version = StrictVersion(version)
    except ValueError:
        wanted_version = LooseVersion(version)

    log.debug("looking for version: %s", wanted_version)

    for verstr, tag in tags.items():
        if wanted_version == verstr:
            log.debug("Found matching version %s (%s)", wanted_version, verstr)
            return ("mozilla-release", tag)

    # No specific tag; try the defaults of the branches, starting from the newest
    # Note that once we get here we only check the major version, so you can't,
    # for example, specifically ask for beta 2 of a branch
    for branch_part in "mozilla-central", "releases/mozilla-aurora", "releases/mozilla-beta":
        mstone_url = "https://hg.mozilla.org/%s/raw-file/default/config/milestone.txt" % (branch_part,)
        branch = branch_part.split("/")[-1]
        mstone_file = urllib2.urlopen(mstone_url)
        try:
            for line in mstone_file:
                ver_str = line.strip()
                if (ver_str + "#").startswith("#"):
                    continue # comment line
                try:
                    ver = StrictVersion(ver_str)
                except ValueError:
                    ver = LooseVersion(ver_str)
                break
        finally:
            mstone_file.close()
        if ver and ver.version[0] == wanted_version.version[0]:
            # Have the right tree (going by major version only)
            log.debug("%s major version %s matches %s",
                      branch, ver, wanted_version)
            return (branch, "default")
        log.debug("%s major version %s does not match %s",
                  branch, ver, wanted_version)

    # Ugh... Try for... anything?
    if wanted_version.version[0] <= max_ver:
        return ("mozilla-release", "default")
    elif wanted_version.version[0] <= max_ver + 1:
        return ("mozilla-beta", "default")
    elif wanted_version.version[0] <= max_ver + 2:
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
    logging.basicConfig()
    log.setLevel(logging.DEBUG)
    import sys
    tree, tag = getTreeFromVersion((sys.argv + [None])[1])
    log.debug("tree: %s, tag: %s", tree, tag)
    if "--dry-run" not in sys.argv:
        cloneFromTree(tree, tag=tag)
