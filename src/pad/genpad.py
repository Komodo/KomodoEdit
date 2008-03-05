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

g_pad_file_prefix_from_product_type = {
    "ide": "komodo_ide",
    "edit": "komodo_edit",
}


class GenPadError(Exception):
    pass



#---- main functionality

def genpad():
    top_dir = _get_top_dir()
    sys.path.insert(0, top_dir)
    sys.path.insert(0, join(top_dir, "util"))
    import preprocess
    import bkconfig
    
    # Gather PAD info.
    today = datetime.date.today()
    # release status: Major Update, Minor Update, New Release, Beta, Alpha, Media Only.
    release_status = "XXX"
    platname = bkconfig.buildPlatform
    if platname.startswith("win"):
        os_support = "Windows2000,WinXP,Windows Vista Starter,Windows Vista Home Basic,Windows Vista Home Premium,Windows Vista Business,Windows Vista Enterprise,Windows Vista Ultimate,Windows Vista Home Basic x64,Windows Vista Home Premium x64,Windows Vista Business x64,Windows Vista Enterprise x64,Windows Vista Ultimate x64"
    elif platname.startswith("macosx"):
        os_support = "Mac OS X,Mac OS X 10.3,Mac OS X 10.4,Mac OS X 10.5"
    elif platname.startswith("linux"):
        os_support = "Linux"
    else:
        raise GenPadError("what is appropriate PAD <Program_OS_Support> "
                          "for %r (see http://www.asp-shareware.org/pad/specs.php)"
                          % platname)
    
    pad_info = {
        "$PAD_PROGRAM_NAME": "Komodo %s" % bkconfig.prettyProductType,
        "$PAD_VERSION": bkconfig.komodoShortVersion,
        "$PAD_RELEASE_YEAR": today.year,
        "$PAD_RELEASE_MONTH": today.month,
        "$PAD_RELEASE_DAY": today.day,
        #"$PAD_RELEASE_STATUS": release_status,
        "$PAD_OS_SUPPORT": os_support,
    }
    pprint(pad_info)

    # Preprocess the template.
    template_path = join(dirname(__file__), "komodo_prod_plat.p.xml")
    prefix = g_pad_file_prefix_from_product_type[bkconfig.productType]
    plat = bkconfig.buildPlatform.replace('-', '_')
    output_path = join(dirname(__file__), "%s_%s.xml" % (prefix, plat))
    log.info("genpad `%s'", output_path)
    preprocess.preprocess(template_path, outfile=output_path,
                          defines=pad_info, substitute=True)
    
    # Sanity check that add "$PAD_*" vars were handled.
    num_hits = 0
    content = open(output_path, 'r').read()
    if "$PAD" in content:
        pad_pat = re.compile(r"\$PAD_\w+\b")
        for hit in pad_pat.findall(content):
            num_hits += 1
            log.error("'%s' from template not replaced", hit)
    
    return num_hits
    

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



#---- mainline

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit( genpad() )
