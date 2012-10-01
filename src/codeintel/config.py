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

# (Mostly) hardcoded codeintel/... build configuration.

import sys
from os.path import expanduser, exists, join, isfile, isdir, dirname, \
                    abspath, normpath
from glob import glob

import which
try:
    from platinfo import PlatInfo
except ImportError:
    # Fall back to using the platinfo in the "komodo-devel/util" directory.
    # Note: there is two possible scenarios - one when building Komodo, and the
    #       other for building directly in the "src/codeintel" tree.
    _alt_dirs = [join(dirname(dirname(dirname(abspath(__file__)))), "util"),
                 join(dirname(dirname(dirname(dirname(abspath(__file__))))), "util")]
    for _alt_dir in _alt_dirs:
        sys.path.insert(0, _alt_dir)
        try:
            from platinfo import PlatInfo
            break
        except:
            pass
        finally:
            sys.path = sys.path[1:]
    else:
        raise

#---- internal support stuff

class ConfigError(Exception):
    pass

def xpath(*parts):
    """Massage a Unix-like path into an appropriately native one."""
    if len(parts) == 1:
        path = parts[0]
    else:
        path = join(*parts)
    if sys.platform == "win32":
        path = path.replace('/', '\\')
    return normpath(expanduser(path))



#---- determine the configuration vars

platinfo = PlatInfo()
platname = platinfo.name()

sqlite_version = "3.2.7"

# Source repositories (for 3rd-party tarballs)
def gen_src_repositories():
    if sys.platform == "win32":
        yield r"\\crimper\apps\Komodo\support\codeintel"
    else:
        yield "/mnt/crimper.home/apps/Komodo/support/codeintel"
        yield "/mnt/crimper/apps/Komodo/support/codeintel"
        yield "/mnt/crimper/home/apps/Komodo/support/codeintel"
    yield xpath("~/data/bits")
    yield xpath(dirname(abspath(__file__))) # current dir
src_repositories = [r for r in gen_src_repositories() if isdir(r)]
if not src_repositories:
    raise ConfigError("could not find any source repositories (for "
                      "3rd-party tarballs): none of these exist: '%s'"
                      % "', '".join(list(gen_src_repositories())))

# Komodo source tree and the current Komodo config.
def get_komodo_src():
    # Are in the Komodo-devel tree? Look for Construct
    construct_candidates = [
        join(dirname(dirname(dirname(abspath(__file__)))), "Construct"),
        join(dirname(dirname(dirname(dirname(abspath(__file__))))), "Construct"),
    ]
    for construct in construct_candidates:
        if isfile(construct):
            return dirname(construct)
    trents_typicals = [expanduser("~/as/Komodo-devel"),
                       expanduser("~/as/main/Apps/Komodo-devel"),
                       expanduser("~/main/Apps/Komodo-devel")]
    for typical in trents_typicals:
        if isfile(join(typical, "Construct")):
            return typical
    raise ConfigError("could not find Komodo source tree: '%s'" % komodo_src)
komodo_src = get_komodo_src()

def get_komodo_cfg(komodo_src):
    import imp
    bkconfig_py = join(komodo_src, "bkconfig.py")
    if not exists(bkconfig_py):
        return None
    iinfo = imp.find_module("bkconfig", [komodo_src])
    cfg = imp.load_module("bkconfig", *iinfo)
    return cfg
komodo_cfg = get_komodo_cfg(komodo_src)


PYTHON_SCHEME = "komodo"   # "komodo" or "first-on-path"
if PYTHON_SCHEME == "first-on-path":
    python = which.which("python") # Python installation to use.
elif PYTHON_SCHEME == "komodo":
    python = komodo_cfg.siloedPython
