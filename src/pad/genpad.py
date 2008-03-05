#!/usr/bin/env python
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

"""Generate a PAD file for distribution on sites for this Komodo build."""

__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import join, dirname, abspath, basename, exists
import sys
import re
import datetime
from pprint import pprint
import traceback
import optparse
import logging



#---- exceptions and globals

log = logging.getLogger("genpad")

g_sysreqs_from_os = {
     "win32": "Windows x86 architecture, 233 MHz+ CPU (500 MHz+ PIII recommended), 128 MB RAM (256 MB+ recommended)",
     "linux": "Linux Debian Stable/Ubuntu 5.04+, Red Hat Enterprise Linux 4+, Fedora Core 4, Suse/Novell: Suse 9.0+",
     "macosx": "Mac Intel processor or PowerPC G4, 256 MB RAM, 90 MB hard disk space",
}

g_os_support_from_os = {
    "win32": "Windows2000,WinXP,Windows Vista Starter,Windows Vista Home Basic,Windows Vista Home Premium,Windows Vista Business,Windows Vista Enterprise,Windows Vista Ultimate,Windows Vista Home Basic x64,Windows Vista Home Premium x64,Windows Vista Business x64,Windows Vista Enterprise x64,Windows Vista Ultimate x64",
    "macosx": "Mac OS X,Mac OS X 10.3,Mac OS X 10.4,Mac OS X 10.5",
    "linux": "Linux",
}


class GenPadError(Exception):
    pass



#---- main functionality

def genpad():
    DEBUG = True
    num_errors = 0

    top_dir = _get_top_dir()
    sys.path.insert(0, top_dir)
    sys.path.insert(0, join(top_dir, "util"))
    import preprocess
    import platinfo
    import bkconfig
    
    # Some general info.
    today = datetime.date.today()
    ver_info = _ver_info_from_long_ver_str(bkconfig.version)
    pi = platinfo.PlatInfo()

    # Gather PAD info.
    if len(ver_info) > 3 and ver_info[3] == 'a':
        release_status = "Alpha"
    elif len(ver_info) > 3 and ver_info[3] == 'b':
        release_status = "Beta"
    elif ver_info[2] == 0:
        release_status = "Major Update"
    else:
        release_status = "Minor Update"
    platname = bkconfig.buildPlatform
    os_support = g_os_support_from_os.get(pi.os)
    if os_support is None:
        raise GenPadError("what is appropriate PAD <Program_OS_Support> "
                          "for %r (see http://www.asp-shareware.org/pad/specs.php)"
                          % platname)
    install_pkg_path = join(top_dir, bkconfig.komodoInstallerPackage)
    if not exists(install_pkg_path):
        num_errors += 1
        log.error("`%s' installer package doesn't exist (run `bk build`)",
                  install_pkg_path)
        size_bytes = 0
    else:
        size_bytes = os.stat(install_pkg_path).st_size
    short_ver = _short_ver_str_from_ver_info(ver_info)
    pad_info = {
        "$PAD_PROGRAM_NAME": "Komodo %s" % bkconfig.prettyProductType,
        "$PAD_VERSION": bkconfig.komodoShortVersion,
        "$PAD_RELEASE_YEAR": today.year,
        "$PAD_RELEASE_MONTH": today.month,
        "$PAD_RELEASE_DAY": today.day,
        "$PAD_RELEASE_STATUS": release_status,
        "$PAD_OS_SUPPORT": os_support,
        "$PAD_SYSREQ": g_sysreqs_from_os[pi.os],
        "$PAD_SIZE_BYTES": size_bytes,
        "$PAD_SIZE_K": int(float(size_bytes) / 1024.0),
        "$PAD_SIZE_MB": "%.1f" % (float(size_bytes) / 1024.0 / 1024.0),
        "$PAD_RELEASES_VER": short_ver,
        "$PAD_INSTALLER_PKG_NAME": basename(bkconfig.komodoInstallerPackage),
    }
    eula_path = join(bkconfig.readmeDir, "license.txt")
    if not exists(eula_path):
        log.warn("`%s' doesn't exist for PAD EULA (run `bk build`)", eula_path)
    else:
        pad_info["$PAD_EULA"] = open(eula_path).read()
    if DEBUG:
        pad_info_summary = pad_info.copy()
        pad_info_summary["$PAD_EULA"] = pad_info_summary["$PAD_EULA"][:50] + "..."
        pprint(pad_info_summary)

    # Preprocess the template.
    template_path = join(dirname(__file__), "komodo_pad.p.xml")
    plat = bkconfig.buildPlatform.replace('-', '_')
    output_path = join(dirname(__file__), "komodo_edit_%s.xml" % (prefix, plat))
    log.info("genpad `%s'", output_path)
    preprocess.preprocess(template_path, outfile=output_path,
                          defines=pad_info, substitute=True)
    
    # Sanity check that add "$PAD_*" vars were handled.
    content = open(output_path, 'r').read()
    if "$PAD" in content:
        pad_pat = re.compile(r"\$PAD_\w+\b")
        for hit in pad_pat.findall(content):
            num_errors += 1
            log.error("'%s' from template not replaced", hit)
    
    return num_errors
    

#---- internal support stuff

def _get_top_dir():
    dir = dirname(abspath(__file__))
    while True:
        if exists(join(dir, "Blackfile.py")):
            return dir

        up_dir = dirname(dir)
        if up_dir == dir:
            break
        dir = up_dir
    else:
        raise GenPadError("couldn't find top Komodo dir (with Blackfile.py)")

def _short_ver_str_from_ver_info(ver_info):
    def isint(s):
        try:
            int(s)
        except ValueError:
            return False
        else:
            return True

    dotted = []
    for bit in ver_info:
        if bit is None:
            continue
        if dotted and isint(dotted[-1]) and isint(bit):
            dotted.append('.')
        dotted.append(str(bit))
    return ''.join(dotted)    

def _ver_info_from_long_ver_str(long_ver_str):
    """Return a version info tuple for the given long version string.
    
    Examples of a "long" version string are:
        4.0.0-alpha3-12345, 1.2.3-beta-54321, 4.2.5-2598, 5.0.0-43251
    "Short" would be more like:
        4.0.0a3, 1.2.3b, 4.2.5
    
    The returned tuple will be:
        (<major>, <minor>, <patch>, <quality>, <quality-num>, <build-num>)
    where <quality> is a letter ('a' for alpha, 'b' for beta, 'c' if not
    given). <quality-num> and <build-num> default to None. The defaults are
    chosen to make sorting result in a natural order.
    """
    def _isalpha(ch):
        return 'a' <= ch <= 'z' or 'A' <= ch <= 'Z'
    def _isdigit(ch):
        return '0' <= ch <= '9'
    def _split_quality(s):
        for i in reversed(range(1, len(s)+1)):
            if not _isdigit(s[i-1]):
                break
        if i == len(s):
            quality_name, quality_num = s, None
        else:
            quality_name, quality_num = s[:i], int(s[i:])
        quality = {'alpha': 'a', 'beta': 'b', 'devel': 'd'}[quality_name]
        return quality, quality_num

    bits = []
    for i, undashed in enumerate(long_ver_str.split('-')):
        for undotted in undashed.split('.'):
            if len(bits) == 3:
                # This is the "quality" section: 2 bits
                if _isalpha(undotted[0]):
                    bits += list(_split_quality(undotted))
                    continue
                else:
                    bits += ['c', None]
            try:
                bits.append(int(undotted))
            except ValueError:
                bits.append(undotted)
        # After first undashed segment should have: (major, minor, patch)
        if i == 0:
            while len(bits) < 3:
                bits.append(0)
    return tuple(bits)



#---- mainline

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit( genpad() )
