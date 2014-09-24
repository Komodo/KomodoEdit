"""
Module to get the mozilla tree corresponding to a version number
"""

import logging
import urllib2, re, subprocess
import os.path
import time
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

g_tag_cache = {}

def genTagsFromTrees(trees):
    for tree in trees:
        if tree in g_tag_cache:
            for tag in g_tag_cache:
                yield (tree, tag)
            continue
        tags_url = "http://hg.mozilla.org/releases/%s/raw-tags" % (tree,)
        # Hg isn't the most stable, so give it a few tries:
        for tries in range(5):
            try:
                response = urllib2.urlopen(tags_url)
            except urllib2.HTTPError:
                continue
            else:
                break
        else:
            raise urllib2.HTTPError("Couldn't reach url %r", tags_url)
            
        tags = []
        for line in response.read().splitlines():
            tag, _ = line.strip().rsplit("\t", 1)
            tags.append(tag)
            yield (tree, tag)
        g_tag_cache[tree] = tags
            

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

    wanted_tag = None
    if version is None:
        # use default
        version = "31.1.1"
    elif ":" in version:
        # Obsolete syntax, version:TAG; just use the tag
        version, wanted_tag = version.split(":", 1)
    elif version.startswith("FIREFOX_") and version.endswith("_RELEASE"):
        # A specific TAG
        wanted_tag = version

    if wanted_tag:
        # Look in trees for the wanted tag - it must be an exact match.
        if "esr_" in wanted_tag:
            trees = ("mozilla-esr31",)
        else:
            trees = ("mozilla-release", "mozilla-beta", "mozilla-aurora")
        for tree, tag in genTagsFromTrees(trees):
            if tag == wanted_tag:
                return (tree, tag)
        raise ValueError("Tag %r not found")

    # Figure out the closest version to what the user asked for.
    try:
        wanted_version = StrictVersion(version)
    except ValueError:
        wanted_version = LooseVersion(version)
    log.debug("looking for version: %s", wanted_version)

    # Look for a matching release version.
    max_ver = 0.0
    for tree, tag in genTagsFromTrees(("mozilla-release", "mozilla-beta", "mozilla-aurora")):
        if not tag.startswith("FIREFOX_") or not tag.endswith("_RELEASE"):
            continue
        ver = ".".join(tag.split("_", 1)[1].rsplit("_", 1)[0].split("_"))
        #log.debug("  checking ver %s", ver)
        try:
            if ver == wanted_version:
                log.debug("Found exact match in %s: %s", tree, tag)
                return (tree, tag)
        except ValueError, ex:
            # Not a correctly formatter version.
            continue
        if tree == "mozilla-release":
            ver = float(ver.split(".")[0])
            if ver > max_ver:
                max_ver = ver

    # No specific tag; try the defaults of the branches, starting from the newest
    # Note that once we get here we only check the major version, so you can't,
    # for example, specifically ask for alpha 1. (They don't have that
    # information anyway.)
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

    # Ugh... Try for... anything?  This doesn't really make sense.
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

def test():
    import unittest
    class GetMozillaTreeTests(unittest.TestCase):
        def test_version(self):
            tree, tag = getTreeFromVersion("24.0")
            self.assertEqual(tree, "mozilla-release")
            self.assertEqual(tag, "FIREFOX_24_0_RELEASE")
        def test_version_and_tag_release(self):
            tree, tag = getTreeFromVersion("2400:FIREFOX_24_0_RELEASE")
            self.assertEqual(tree, "mozilla-release")
            self.assertEqual(tag, "FIREFOX_24_0_RELEASE")
        def test_version_and_tag_beta(self):
            tree, tag = getTreeFromVersion("2400:FIREFOX_24_0b1_RELEASE")
            self.assertEqual(tree, "mozilla-release")
            self.assertEqual(tag, "FIREFOX_24_0b1_RELEASE")
        def test_tag_beta(self):
            tree, tag = getTreeFromVersion("FIREFOX_24_0b1_RELEASE")
            self.assertEqual(tree, "mozilla-release")
            self.assertEqual(tag, "FIREFOX_24_0b1_RELEASE")
        def test_version_and_tag_esr(self):
            tree, tag = getTreeFromVersion("3100:FIREFOX_31_1_1esr_RELEASE")
            self.assertEqual(tree, "mozilla-esr31")
            self.assertEqual(tag, "FIREFOX_31_1_1esr_RELEASE")
        def test_tag_esr(self):
            tree, tag = getTreeFromVersion("FIREFOX_31_1_1esr_RELEASE")
            self.assertEqual(tree, "mozilla-esr31")
            self.assertEqual(tag, "FIREFOX_31_1_1esr_RELEASE")

    suite = unittest.TestLoader().loadTestsFromTestCase(GetMozillaTreeTests)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    logging.basicConfig()
    log.setLevel(logging.DEBUG)
    import argparse
    import sys
    parser = argparse.ArgumentParser(description='Download the Mozilla source tree')
    parser.add_argument("version", metavar="version[:tag]", default=None,
                        help="Which version / tag to download")
    parser.add_argument("--dry-run", action="store_true", default=False,
                        help="Do not download the source tree, just determine "
                             "which repoistory / head will be used.")
    parser.add_argument("--test", action="store_true", default=False,
                        help="Run unit tests instead of doing anything normal.")
    args = parser.parse_args()
    if args.test:
        test()
        sys.exit(0)
    tree, tag = getTreeFromVersion(args.version)
    log.debug("tree: %s, tag: %s", tree, tag)
    if not args.dry_run:
        cloneFromTree(tree, tag=tag)
