#!/usr/bin/env python

"""Do a quick install of the latest Komodo on Linux and start it.

This script is to assist in the basic compat testing of Komodo on
various Linux distros.

Usage:
    export TMPDIR=/tmp/koinst-$USER
    rm -rf $TMPDIR
    mkdir -p $TMPDIR
    cd $TMPDIR
    wget -q http://svn.openkomodo.com/openkomodo/checkout/openkomodo/trunk/util/ko-linux-install-test.py
    python ko-linux-install-test.py | tee ko-linux-install-test-$HOSTNAME.log

Then, if your testing shows something new (e.g., if this is for a distro which
isn't already mentioned on bug 79495) then please attach the created log file
to:
    http://bugs.activestate.com/show_bug.cgi?id=79495
with a message something like:
    Ubuntu 6.04: failed to install
    RHEL 9: success installing and starting up
"""

import sys
import os
from os.path import exists, basename
import getpass
import urllib2
import re
from pprint import pprint
import fnmatch
import logging


log = logging.getLogger("ko-linux-install-test")



#---- internal support stuff

def get_latest_komodo_nightly_pkg_url(pi):
    latest_dir = "http://downloads.activestate.com/Komodo/nightly/komodoide/latest-trunk/"
    links = links_from_url(latest_dir)
    linux_pkgs = fnmatch.filter(links, "Komodo-*-linux-*%s.tar.gz" % pi.arch)
    if not linux_pkgs:
        log.warn("couldn't find a Komodo `%s' build in `%s' (trying "
                 "any linux architecture build)", pi.name(), latest_dir)
        linux_pkgs = fnmatch.filter(links, "Komodo-*-linux-*.tar.gz")
    #pprint(linux_pkgs)
    if linux_pkgs:
        linux_pkgs.sort()
        return latest_dir + linux_pkgs[-1]
    log.error("couldn't find a Komodo linux build in `%s'", latest_dir)
    return None

_a_pat = re.compile(r'<a href="(.*?)">.*?</a>')
def links_from_url(url, cache=False):
    html = urllib2.urlopen(url).read()
    links = set(href for href in _a_pat.findall(html))
    return links

def wget(url):
    run("wget -q %s" % url)

def run(cmd):
    retval = os.system(cmd)
    if retval:
        raise RuntimeError("error running `%s'" % cmd)


#---- mainline

def main(argv):
    log.setLevel(logging.INFO)

    # Option handle (such as it is).
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0

    # Get platform info.
    wget("http://svn.openkomodo.com/openkomodo/checkout/openkomodo/trunk/util/platinfo.py")
    import platinfo
    pi = platinfo.PlatInfo()
    print(pi.as_yaml())

    # Download the installer package.
    url = get_latest_komodo_nightly_pkg_url(pi)
    if url is None:
        return 1
    log.info("downloading `%s'", url)
    wget(url)

    # Install and startup.
    log.info("installing `%s'", basename(url))
    run("tar xzf %s" % basename(url))
    run("Komodo-*/install.sh -s -I ko")
    log.info("starting Komodo...")
    run("ko/bin/komodo -v")

    return 0


if __name__ == "__main__":
    logging.basicConfig()
    sys.exit(main(sys.argv))

