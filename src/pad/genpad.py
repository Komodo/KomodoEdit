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
import codecs
import logging



#---- exceptions and globals

log = logging.getLogger("genpad")
# Careyh: Needed the 64 bit lines for testing on my machine for some reason
# Decided to not remove just incase they are needed later and in case I want to
# test and make more edits later.
g_sysreqs_from_os = {
     "win32": "1GHz (or faster) x86 or x86_64 processor with 1 GB RAM, 250 MB hard disk space and 350 MB of temporary hard disk space during installation.",
     #"win64": "1GHz (or faster) x86 or x86_64 processor with 1 GB RAM, 250 MB hard disk space and 350 MB of temporary hard disk space during installation.",
     "linux": "Intel processor, 1 GB RAM, 250 MB hard disk space and 350 MB of temporary hard disk space during installation.",
     "macosx": "1GHz (or faster) x86 or x86_64 processor with 1 GB RAM, 250 MB hard disk space and 350 MB of temporary hard disk space during installation.",
}

g_os_support_from_os = {
    "win32": "Windows Server 2008 or later, Win7 x32, Win7 x64, Win8, Win10",
    #"win64": "Windows Server 2008 or later, Win7 x32, Win7 x64, Win8, Win10",
    "macosx": "Mac OS X 10.9 (Mavericks) or later",
    "linux": "Red Hat Enterprise Linux 6 or later, CentOS 6.0 or later, Fedora Core 15 or later, OpenSUSE 12.1 or later, SuSE Linux Enterprise Desktop/Server 11.3 or later, Ubuntu 12.04 or later"
}

g_pretty_platname_from_platname = {
    "win32-x86": "Windows",
    #"win64-x64": "Windows",
    "macosx": "Mac OS X",
    "macosx-x86": "Mac OS X/Intel",
    "macosx-powerpc": "Mac OS X/PowerPC",    
    "linux-x86": "Linux/x86",
    "linux-x86_64": "Linux/x86_64",
}

g_simple_platform_name_from_os = {
    "win32": "windows",
    #"win64": "windows",
    "macosx": "mac",
    "linux": "linux",
}

g_EUAL_link_from_editor = {
     "Edit": "http://www.activestate.com/komodo-edit/license-agreement",
     "IDE": "http://www.activestate.com/komodo-ide/license-agreement"
}

class GenPadError(Exception):
    pass



#---- main functionality

def genpad(output_dir=None):
    DEBUG = False
    if output_dir is None:
        output_dir = dirname(__file__)
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
    elif len(ver_info) > 3 and ver_info[3] in ('b', 'c'):
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
    pad_basename = "komodo_%s_%s.xml" % (
        bkconfig.productType, bkconfig.buildPlatform.replace('-', '_'))
    pretty_platname = g_pretty_platname_from_platname[platname]
    pad_info = {
        "$PAD_PROGRAM_NAME": "Komodo %s (%s)" % (
            bkconfig.prettyProductType, pretty_platname),
        "$PAD_VERSION": bkconfig.komodoVersion,
        "$PAD_MAJOR_VERSION": bkconfig.komodoShortVersion.split(".")[0],
        "$PAD_RELEASE_YEAR": today.year,
        "$PAD_RELEASE_MONTH": "%02d" % today.month,
        "$PAD_RELEASE_DAY": "%02d" % today.day,
        "$PAD_RELEASE_STATUS": release_status,
        "$PAD_OS_SUPPORT": os_support,
        "$PAD_SYSREQ": g_sysreqs_from_os[pi.os],
        "$PAD_SIMPLE_PLATFORM_NAME": g_simple_platform_name_from_os[pi.os],
        "$PAD_SIZE_BYTES": size_bytes,
        "$PAD_SIZE_K": int(float(size_bytes) / 1024.0),
        "$PAD_SIZE_MB": "%.1f" % (float(size_bytes) / 1024.0 / 1024.0),
        "$PAD_RELEASES_VER": short_ver,
        "$PAD_INSTALLER_PKG_NAME": basename(bkconfig.komodoInstallerPackage),
        "$PAD_PAD_BASENAME": pad_basename,
        "$PAD_SCREENSHOT_BASENAME": "komodo_%s_%s.png" % (bkconfig.productType, pi.os),
        "$PAD_ICON_BASENAME": "komodo_orb_32.png",
        "$PAD_EULA": g_EUAL_link_from_editor.get(bkconfig.prettyProductType)
    }

    # Preprocess the template.
    template_path = join(dirname(__file__), "komodo_pad.p.xml")
    output_path = join(output_dir, pad_basename)
    log.info("genpad `%s'", output_path)
    output_file = codecs.open(output_path, 'w', "utf-8")
    preprocess.preprocess(template_path, outfile=output_file,
                          defines=pad_info, substitute=True)
    output_file.close()
    
    # Sanity check that add "$PAD_*" vars were handled.
    content = codecs.open(output_path, 'r', "utf-8").read()
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
        quality = {'alpha': 'a', 'beta': 'b', 'rc': 'c', 'devel': 'd'}[quality_name]
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

def main(argv):
    usage = """usage: %prog [OPTIONS]
     
    NOTE: Many config settings are within this file.  Make sure to review the
    source for potential updates needed."""
    version = "%prog "+__version__
    parser = optparse.OptionParser(usage=usage,
        version=version, description=__doc__)
    parser.add_option("-d", "--output-dir",
                      help="output dir for generate PAD file")
    parser.add_option("-L", "--license-text-path",
                      help="path to License text to use *DEPRECATED*")
    opts, args = parser.parse_args()
    if(opts.license_text_path):
        log.warn("'-L' option deprecated.  Update scripts to not use it.\
                 That option is being ignored.")
    if args:
        raise GenPadError("no args at accepted by genpad")
    return genpad(output_dir=opts.output_dir)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit( main(sys.argv) )