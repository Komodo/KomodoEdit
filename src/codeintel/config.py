# (Mostly) hardcoded codeintel/... build configuration.

import sys
from os.path import expanduser, exists, join, isfile, isdir, dirname, \
                    abspath, normpath
from glob import glob

import which
from platinfo import PlatInfo


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

PYTHON_SCHEME = "first-on-path"   # "komodo" or "first-on-path"
if PYTHON_SCHEME == "first-on-path":
    python = which.which("python") # Python installation to use.
elif PYTHON_SCHEME == "komodo":
    #import p4lib, platinfo
    #p4 = p4lib.P4()
    #where = p4.where("//depot/main/Apps/Mozilla-devel/prebuilt/README.txt")
    #prebuilt_path = dirname(where[0]["localFile"])
    #platname = platinfo.platname("os", "libcpp", "arch")
    #python = join(prebuilt_path, platinfo.platname(), "release", "python")
    #if sys.platform == "win32":
    #    python = join(python, "python.exe")
    #elif sys.platform == "darwin":
    #    python = glob(join(python, "Python.framework", "Versions", "*",
    #                       "bin", "python"))[0]
    #else:
    #    python = join(python, "bin", "python")
    raise ConfigError(r"""You need to hardcode something like this:
    python = r"C:\trentm\as\Mozilla-devel\prebuilt\win32-x86\release\python\python.exe"
as appropriate for your system in config.py.""")


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



