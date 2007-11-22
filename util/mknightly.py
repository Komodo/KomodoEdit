#!/usr/bin/env python
#
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

r"""Make the latest Komodo build a nightly.

Being a "nightly" means that it shows up on the nightly channel of
the Komodo update service.

Yes the script name is "mk" and this just uploads stuff. Get over it.
By default this will grab the latest dev build of Komodo and plop
it properly into the nightly downloads area.

Supported project names:
    komodoide
    komodoedit
"""

__version_info__ = (0, 2, 0)
__version__ = '.'.join(map(str, __version_info__))

    
import os
import sys
import re
from pprint import pprint
from glob import glob
import time
import traceback
import logging
import tempfile
import optparse

import buildutils



#---- exceptions

class Error(Exception):
    pass



#---- globals

log = logging.getLogger("mknightly")

#TODO: get from or keep in sync with pkgutils.py
#      `KomodoReleasesGuru.nightly_base_dir_from_project`.
upload_base_dir_from_project = {
    "komodoedit": "box17:/data/download/",
    "komodoide": "crimper:/home/apps/Komodo/fakey-downloads",
}
pkg_pats_from_project = {
    "komodoedit": ["Komodo-Edit-*"],
    "komodoide": ["Komodo-IDE-*"],
}

devbuilds_base_dir_from_project = {
    "komodoide": "crimper:/home/apps/Komodo",
    "komodoedit": "crimper:/home/apps/Komodo",
}
scc_repo_name_from_project = {
    "komodoide": "assvn",  # ActiveState SVN
    "komodoedit": "oksvn", # svn.openkomodo.com
}



#---- module API

def mknightly(project, branch="trunk", upload_base_dir=None,
              dry_run=True, can_link=False):
    """Make the latest Komodo IDE/Edit devbuild a nightly.
    
    @param project {str} is the name for the project for which to
        make a nightly.
    @param branch {str} is the source tree branch whose builds to use
        (is "trunk" be default).
    @param upload_base_dir {str} an override for the default hardcoded
        base dir for the given project name.
    @param dry_run {boolean} can be used to just go through the motions.
    @param can_link {boolean} indicates if hard-linking files is allowed
        if the devbuilds dir and downloads dir are on the same server.
    """
    from posixpath import join, basename, dirname
    
    if upload_base_dir is None:
        upload_base_dir = upload_base_dir_from_project[project]
    log.debug("mknightly(%r, upload_base_dir=%r, dry_run=%r)",
              project, upload_base_dir, dry_run)
    assert buildutils.is_remote_path(upload_base_dir)

    # Get the source packages dir.
    devbuilds_dir = _get_devbuilds_dir(project, branch)
    log.info("mknightly %s %s", devbuilds_dir, upload_base_dir)

    # Sanity guard: the project dir on the upload site must exist
    # already.
    upload_base_dir = join(upload_base_dir, project, "nightly")
    if not buildutils.remote_exists(upload_base_dir):
        raise Error("`%s' does not exist: as a sanity check you must "
                    "make the project dir manually" % upload_base_dir)

    # Figure out what serial number to use (to avoid collisions
    # for multiple builds for same day).
    year, month, day = time.localtime()[:3]
    upload_dir_pat = join(upload_base_dir, str(year), str(month),
        "%04d-%02d-%02d-*-%s" % (year, month, day, branch))
    used_serials = []
    for d in buildutils.remote_glob(upload_dir_pat):
        try:
            used_serials.append(int(basename(d).split('-')[3]))
        except ValueError:
            pass
    used_serials.sort()
    if not used_serials:
        serial = 0
    else:
        serial = used_serials[-1] + 1
    if serial > 99:
        raise Error("too many nightly builds for today: serial=%r"
                    % serial)
    
    # Do the upload.
    upload_dir = join(upload_base_dir, str(year), str(month),
        "%04d-%02d-%02d-%02d-%s" % (year, month, day, serial, branch))
    excludes = ["internal", "*RemoteDebugging*"]
    includes = pkg_pats_from_project[project]
    _upload(devbuilds_dir, upload_dir,
            includes=includes, excludes=excludes,
            dry_run=dry_run, can_link=can_link)
    
    # MD5SUMs info file in the 'updates' subdir.
    _mk_mar_md5sums(join(upload_dir, "updates"))
    
    # Symlinks.
    # latest-$branch -> $upload_dir
    dst = join(upload_base_dir, "latest-" + branch)
    if not dry_run and buildutils.remote_exists(dst):
        buildutils.remote_rm(dst)
    src_relpath = buildutils.remote_relpath(upload_dir, dirname(dst))
    log.info("ln -s %s %s", src_relpath, dst)
    if not dry_run:
        buildutils.remote_symlink(src_relpath, dst, log.debug)



#---- internal support stuff

def _mk_mar_md5sums(rdir):
    """Create a (slightly non-standard) MD5SUMs file in the given
    dir. The format of the file is:
    
        <md5sum> <size> <filename>
    
    One line for each .mar file in that dir. This file is used by the
    "nightly" channel of the update server to be able to get size and md5
    info without resorting the ssh (just HTTP).
    """
    from posixpath import join, basename

    if not buildutils.remote_exists(rdir):
        return
    
    path = join(rdir, "MD5SUMs")
    log.info("create %s", path)
    
    info = []
    for rpath in buildutils.remote_glob(join(rdir, "*.mar"), log.debug):
        size = buildutils.remote_size(rpath, log.debug)
        md5sum = buildutils.remote_md5sum(rpath, log.debug)
        info.append((md5sum, size, basename(rpath)))
    
    tmppath = tempfile.mktemp()
    f = open(tmppath, 'w')
    f.write('\n'.join("%s %s %s" % i for i in info) + '\n')
    f.close()
    buildutils.remote_cp(tmppath, path)
    os.remove(tmppath)

def _upload(src_dir, dst_dir, includes=None, excludes=[],
            dry_run=False, can_link=False):
    from posixpath import join, normpath, dirname
    from fnmatch import fnmatch
    
    log.debug("upload %s %s", src_dir, dst_dir)
    if not dry_run and not buildutils.remote_exists(dst_dir, log.debug):
        buildutils.remote_makedirs(dst_dir, log.debug)

    for dirpath, dnames, fnames in buildutils.remote_walk(src_dir):
        rel_rdir = buildutils.remote_relpath(dirpath, src_dir)
        reldir = rel_rdir.split(':', 1)[1]

        for dname in dnames[:]:
            matches = [x for x in excludes if fnmatch(dname, x)]
            if matches:
                log.debug("skipping `%s' (matches exclusion pattern)", dname)
                dnames.remove(dname)
            
        for fname in fnames:
            if includes:
                for include in includes:
                    if fnmatch(fname, include):
                        break
                else:
                    log.debug("skipping `%s' (doesn't match any includes)", fname)
                    continue
            matches = [x for x in excludes if fnmatch(fname, x)]
            if matches:
                log.debug("skipping `%s' (matches exclusion pattern)", fname)
                continue
            src = join(dirpath, fname)
            dst = normpath(join(dst_dir, reldir, fname))
            log.info("cp %s %s", src, dst)
            if not dry_run:
                if not buildutils.remote_exists(dirname(dst), log.debug):
                    buildutils.remote_makedirs(dirname(dst), log.debug)
                buildutils.remote_cp(src, dst, log.debug,
                                     hard_link_if_can=can_link)

def _get_devbuilds_dir(project, branch, ver=None, build_num=None):
    from posixpath import join, basename
    
    base_dir = devbuilds_base_dir_from_project[project]
        
    # Find the appropriate version dir.
    if ver:
        ver_dir = join(base_dir, ver)
        assert buildutils.remote_exists(ver_dir), \
            "'%s' does not exist" % ver_dir
    else:
        vers = []
        for d in buildutils.remote_glob(join(base_dir, "*")):
            try:
                vers.append((_split_short_ver(basename(d), intify=True), d))
            except ValueError:
                pass
        assert vers, "no devbuilds in '%s'" % base_dir
        vers.sort()
        ver_dir = vers[-1][1]
    
    # Find the appropriate build dir.
    # Individual build dirs are of the form: SCCNAME-BRANCH-BUILDNUM
    scc_repo_name = scc_repo_name_from_project[project]
    if build_num:
        build_dir = join(ver_dir, "DevBuilds",
                         "%s-%s-%s" % (scc_repo_name, branch, build_num))
        assert buildutils.remote_exists(ver_dir), \
            "'%s' does not exist" % ver_dir
    else:
        builds = []
        pat = join(ver_dir, "DevBuilds", "%s-%s-*" % (scc_repo_name, branch))
        for d in buildutils.remote_glob(pat):
            try:
                build_num = int(basename(d).split('-')[2])
            except ValueError:
                pass
            else:
                builds.append( (build_num, d) )
        assert builds, "no devbuilds matching '%s'" % pat
        builds.sort()
        build_dir = builds[-1][1]
    return build_dir

def _intify(s):
    try:
        return int(s)
    except ValueError:
        return s
    
# Recipe: ver (1.0.1)
def _split_full_ver(ver_str):
    """Split a full version string to component bits.

    >>> _split_full_ver('4.0.0-alpha3-12345')
    (4, 0, 0, 'alpha', 3, 12345)
    >>> _split_full_ver('4.1.0-beta-12345')
    (4, 1, 0, 'beta', None, 12345)
    >>> _split_full_ver('4.1.0-12345')
    (4, 1, 0, None, None, 12345)
    >>> _split_full_ver('4.1-12345')
    (4, 1, 0, None, None, 12345)
    """
    def _isalpha(ch):
        return 'a' <= ch <= 'z' or 'A' <= ch <= 'Z'
    def _isdigit(ch):
        return '0' <= ch <= '9'
    def split_quality(s):
        for i in reversed(range(1, len(s)+1)):
            if not _isdigit(s[i-1]):
                break
        if i == len(s):
            quality, quality_num = s, None
        else:
            quality, quality_num = s[:i], int(s[i:])
        return quality, quality_num

    bits = []
    for i, undashed in enumerate(ver_str.split('-')):
        for undotted in undashed.split('.'):
            if len(bits) == 3:
                # This is the "quality" section: 2 bits
                if _isalpha(undotted[0]):
                    bits += list(split_quality(undotted))
                    continue
                else:
                    bits += [None, None]
            try:
                bits.append(int(undotted))
            except ValueError:
                bits.append(undotted)
        # After first undashed segment should have: (major, minor, patch)
        if i == 0:
            while len(bits) < 3:
                bits.append(0)
    return tuple(bits)

_short_ver_re = re.compile("(\d+)(\.\d+)*([a-z](\d+)?)?")
def _split_short_ver(ver_str, intify=False, pad_zeros=None):
    """Parse the given version into a tuple of "significant" parts.

    @param intify {bool} indicates if numeric parts should be converted
        to integers.
    @param pad_zeros {int} is a number of numeric parts before any
        "quality" letter (e.g. 'a' for alpha).
   
    >>> _split_short_ver("4.1.0")
    ('4', '1', '0')
    >>> _split_short_ver("1.3a2")
    ('1', '3', 'a', '2')
    >>> _split_short_ver("1.3a2", intify=True)
    (1, 3, 'a', 2)
    >>> _split_short_ver("1.3a2", intify=True, pad_zeros=3)
    (1, 3, 0, 'a', 2)
    >>> _split_short_ver("1.3", intify=True, pad_zeros=3)
    (1, 3, 0)
    >>> _split_short_ver("1", pad_zeros=3)
    ('1', '0', '0')
    """
    def isint(s):
        try:
            int(s)
        except ValueError:
            return False
        else:
            return True
    def do_intify(s):
        try:
            return int(s)
        except ValueError:
            return s

    if not _short_ver_re.match(ver_str):
        raise ValueError("%r is not a valid short version string" % ver_str)

    hit_quality_bit = False
    bits = []
    for bit in re.split("(\.|[a-z])", ver_str):
        if bit == '.':
            continue
        if intify:
            bit = do_intify(bit)
        if pad_zeros and not hit_quality_bit and not isint(bit):
            hit_quality_bit = True
            while len(bits) < pad_zeros:
                bits.append(not intify and "0" or 0)
        bits.append(bit)
    if pad_zeros and not hit_quality_bit:
        while len(bits) < pad_zeros:
            bits.append(not intify and "0" or 0)
    return tuple(bits)

def _join_short_ver(ver_tuple, pad_zeros=None):
    """Join the given version-tuple, inserting '.' as appropriate.

    @param pad_zeros {int} is a number of numeric parts before any
        "quality" letter (e.g. 'a' for alpha).
    
    >>> _join_short_ver( ('4', '1', '0') )
    '4.1.0'
    >>> _join_short_ver( ('1', '3', 'a', '2') )
    '1.3a2'
    >>> _join_short_ver(('1', '3', 'a', '2'), pad_zeros=3)
    '1.3.0a2'
    >>> _join_short_ver(('1', '3'), pad_zeros=3)
    '1.3.0'
    """
    def isint(s):
        try:
            int(s)
        except ValueError:
            return False
        else:
            return True

    if pad_zeros:
        bits = []
        hit_quality_bit = False
        for bit in ver_tuple:
            if not hit_quality_bit and not isint(bit):
                hit_quality_bit = True
                while len(bits) < pad_zeros:
                    bits.append(0)
            bits.append(bit)
        if not hit_quality_bit:
            while len(bits) < pad_zeros:
                bits.append(0)
    else:
        bits = ver_tuple

    dotted = []
    for bit in bits:
        if dotted and isint(dotted[-1]) and isint(bit):
            dotted.append('.')
        dotted.append(str(bit))
    return ''.join(dotted)


class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

# Recipe: pretty_logging (0.1)
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.

    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.lowerlevelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging(stream=None):
    """Do logging setup:

    We want a prettier default format:
         do: level: ...
    Spacing. Lower case. Skip " level:" if INFO-level. 
    """
    hdlr = logging.StreamHandler(stream)
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)



#---- mainline

def main(argv):
    usage = "usage: %prog [OPTIONS...] [PROJECTS]"
    version = "%prog "+__version__
    parser = optparse.OptionParser(usage=usage,
        version=version, description=__doc__,
        formatter=_NoReflowFormatter())
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARNING,
                      help="quieter output")
    parser.add_option("-n", "--dry-run", action="store_true",
                      help="do a dry-run")
    parser.add_option("-b", "--branch",
        help="Komodo source tree branch builds to use (default is 'trunk')")
    parser.set_defaults(log_level=logging.INFO, dry_run=False,
                        branch="trunk")
    opts, projects = parser.parse_args()
    log.setLevel(opts.log_level)

    if not projects:
        log.info("You probably want to specify some projects. "
                 "(See `mknightly -h'.)")
    for project in projects:
        mknightly(project, branch=opts.branch, dry_run=opts.dry_run,
                  can_link=True)


if __name__ == "__main__":
    _setup_logging()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if log.level <= logging.DEBUG:
            import traceback
            print
            traceback.print_exception(*exc_info)
        else:
            if hasattr(exc_info[0], "__name__"):
                #log.error("%s: %s", exc_info[0].__name__, exc_info[1])
                log.error(exc_info[1])
            else:  # string exception
                log.error(exc_info[0])
        sys.exit(1)
    else:
        sys.exit(retval)



