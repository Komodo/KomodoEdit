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

r"""regmozbuild -- a registry of local Mozilla builds

Back in the day a Mozilla build was all relative paths. You could zip up
relevant parts of a build, crack is somewhere else and use that for
building Komodo. Around about 2005: no longer. The build system is
littered with absolute paths, and I suspect it would be a LOT of work to
get a build tree to be relocatable again. This may be related to the
MOZ_OBJDIR stuff. Therefore, for Komodo-Mozilla builds we need some
other build solution.

The Solution:
On each build machine a registry of mozilla builds is maintained.  The
Komodo build system can then use this registry to pick an appropriate
mozilla build. This module provides the interface to this registry.
"""

__version_info__ = (0, 2, 1)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import join, exists, abspath, dirname, normcase
import sys
import optparse
import logging
import imp
import re
import shutil
from glob import glob

sys.path.insert(0, join(dirname(dirname(dirname(abspath(__file__)))), "util"))
try:
    import applib
finally:
    del sys.path[0]



#---- exceptions and globals

class Error(Exception):
    pass

log = logging.getLogger("regmozbuild")
log.setLevel(logging.INFO)



#---- public API

def register_build(config_path):
    """Register the completed mozilla build identified by the given
    config.py path.
    """
    registry = _MozBuildRegistry()
    registry.register(config_path)

def unregister_build(build_num, reason=''):
    """Unregister the given mozilla build.

        "build_num" is the number assigned for this build by this
            registry.
        "reason" (optional) is a message indicating why it is being
            unregistered (used for logging only).

    XXX Need way to list the current build numbers and/or way to
        unregister by config path and/or obj dir.
    """
    registry = _MozBuildRegistry()
    registry.unregister(config_path, reason)

def find_latest_build(**conditions):
    """Return the path to the latest registered mozilla build matching
    the given conditions.

    Valid conditions are any of the Mozilla-devel config variables.
    Typical ones are:
        buildType       release|debug
        komodoVersion   "X.Y"
        blessed         True|False (i.e. was this build blessed for
                        Komodo production builds)
    
    "Latest" sorting is determined by the 'changenum' config var.
    """
    registry = _MozBuildRegistry()
    config = registry.find_latest(**conditions)
    if not config:
        pretty_conds = ', '.join(["%s=%s" % i for i in conditions.items()])
        raise Error("could not find a Mozilla build matching: %s"
                    % pretty_conds)
    return join(config.buildDir, _srcTreeName_from_config(config),
                "mozilla", config.mozObjDir)

def find_latest_mozilla_config(**conditions):
    """Return the config for the latest registered mozilla build matching
    the given conditions.

    Valid conditions are any of the Mozilla-devel config variables.
    Typical ones are:
        buildType       release|debug
        komodoVersion   "X.Y"
        blessed         True|False (i.e. was this build blessed for
                        Komodo production builds)
        buildDir        The directory path to the mozilla build.
        srcTreeName     The name of the src tree directory
    
    "Latest" sorting is determined by the 'changenum' config var.
    """
    registry = _MozBuildRegistry()
    config = registry.find_latest(**conditions)
    if not config:
        pretty_conds = ', '.join(["%s=%s" % i for i in conditions.items()])
        raise Error("could not find a Mozilla build matching: %s"
                    % pretty_conds)
    return config

def unregister_zombie_builds():
    """Remove all "zombie" mozilla builds from the registry.

    Zombie builds are those that are registered but no longer exist (the
    build directory has been removed).
    """
    registry = _MozBuildRegistry()
    registry.unregister_zombies()


#---- internal support stuff

def _srcTreeName_from_config(config):
    """The 'buildName' mozilla configuration item was recently changed
    to 'srcTreeName'. For a period we must support both names.
    """
    if hasattr(config, "srcTreeName"):
        return config.srcTreeName
    else:
        return config.buildName

class _MozBuildRegistry:
    def __init__(self):
        self.app_data_dir = applib.user_data_dir("openkomodo-dev",
                                                 "ActiveState")
        if not exists(self.app_data_dir):
            log.debug("mkdir `%s'", self.app_data_dir)
            os.makedirs(self.app_data_dir)

        self.num_builds = self._get_num_builds()
        self.configs = self._load_configs() # build_num -> config module

    def _load_configs(self):
        configs = {}
        for config_path in glob(join(self.app_data_dir, "config-*.py")):
            build_num = int(re.search(r"config-(\d+)\.py", config_path)
                            .group(1))
            try:
                f = open(config_path)
                try:
                    config = imp.load_source(
                        "_mozbuild_config_%d_" % build_num, config_path, f)
                finally:
                    f.close()
            except (EnvironmentError, ImportError), ex:
                log.warn("could not import registered `%s': skipping",
                         config_path)
            else:
                configs[build_num] = config
        return configs

    def _get_num_builds(self):
        """Get the number of builds that are (or have been) in the
        registry.

        This count primarily serves to provide a unique build id to each
        registered moz build.
        """
        num_builds_path = join(self.app_data_dir, "num_builds.txt")
        if not exists(num_builds_path):
            f = open(num_builds_path, 'w')
            try:
                f.write('0\n')
            finally:
                f.close()
            num_builds = 0
        else:
            f = open(num_builds_path, 'r')
            try:
                num_builds = int(f.read().strip())
            finally:
                f.close()
        return num_builds

    def _set_num_builds(self, num_builds):
        num_builds_path = join(self.app_data_dir, "num_builds.txt")
        f = open(num_builds_path, 'w')
        try:
            f.write(str(num_builds) + '\n')
        except:
            f.close()

    def find_latest(self, **conditions):
        """Return the config for the latest registered build matching
        the given conditions. Otherwise it returns None.

        Valid conditions are any of the Mozilla-devel config variables.
        Typical ones are:
            buildType       release|debug
            komodoVersion   "X.Y"
            blessed         True|False (i.e. was this build blessed for
                            Komodo production builds)

        "Latest" sorting is determined by the 'changenum' config var.
        """
        sorted_configs = [v for k, v in 
                          sorted(self.configs.items(), reverse=True)]
        for config in sorted_configs:
            for attr, value in conditions.items():
                if value is None: continue
                try:
                    if sys.platform.startswith("win") and attr == "buildDir":
                        # on Windows, paths are not case sensitive...
                        if normcase(getattr(config, attr)) != normcase(value):
                            break
                    elif getattr(config, attr) != value:
                        break
                except AttributeError, ex:
                    # This attr is a likely a new configuration items
                    # since this mozbuild config was registered.
                    break
            else:
                return config

    def register(self, config_path):
        # Ensure that this config path represents an existing build.
        try:
            f = open(config_path)
            try:
                new_config = imp.load_source("_mozbuild_config_",
                                             config_path, f)
            finally:
                f.close()
        except (EnvironmentError, ImportError), ex:
            raise Error("cannot register moz build: %s", ex)
        new_moz_obj_dir = join(new_config.buildDir,
                               _srcTreeName_from_config(new_config),
                               "mozilla", new_config.mozObjDir)
        if not exists(new_moz_obj_dir):
            raise Error("cannot register moz build: MOZ_OBJDIR `%s' does "
                        "not exist", new_moz_obj_dir)

        # See if this replaces an existing registration.
        build_nums_to_unregister = []
        for build_num, config in self.configs.items():
            moz_obj_dir = join(config.buildDir,
                               _srcTreeName_from_config(config),
                               "mozilla", config.mozObjDir)
            if moz_obj_dir == new_moz_obj_dir:
                build_nums_to_unregister.append(build_num)

        # Register it.
        new_build_num = self.num_builds + 1
        log.info("register moz build %d: `%s'", new_build_num,
                 new_moz_obj_dir)
        new_config_path = join(self.app_data_dir,
                               "config-%d.py" % new_build_num)
        shutil.copy(config_path, new_config_path)
        f = open(new_config_path)
        try:
            new_config = imp.load_source(
                "_mozbuild_config_%d_" % new_build_num, new_config_path, f)
        finally:
            f.close()
        self.configs[new_build_num] = new_config
        self._set_num_builds(new_build_num)

        # Unregister replaced configs.
        for build_num in build_nums_to_unregister:
            self.unregister(build_num, "replaced by build %d" % new_build_num)

    def unregister(self, build_num, reason=""):
        """Unregister the moz build with the given build_num."""
        log.info("unregister moz build %d: %s", build_num, reason)
        config_path = self.configs[build_num].__file__
        if config_path.endswith(".pyc") or config_path.endswith(".pyo"):
            config_path = config_path[:-1]
        for path in [config_path] + glob(config_path+"?"):
            log.debug("rm `%s'", path)
            os.remove(path)
        del self.configs[build_num]

    def unregister_zombies(self):
        """Unregister zombie builds (those whose builddir is gone)."""
        from pprint import pprint
        pprint(self.configs)
        for build_num, config in self.configs.items():
            obj_dir_path = join(config.buildDir, 
                                _srcTreeName_from_config(config),
                                "mozilla", config.mozObjDir)
            if not exists(obj_dir_path):
                self.unregister(build_num,
                    "zombie (`%s' does not exist)" % obj_dir_path)


#---- mainline

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

def main(argv=sys.argv):
    usage = "usage: %prog <path/to/config.py>"
    version = "%prog "+__version__
    parser = optparse.OptionParser(prog="regmozbuild", usage=usage,
        version=version, description=__doc__,
        formatter=_NoReflowFormatter())
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.set_defaults(log_level=logging.INFO)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    assert len(args) == 1
    config_path = args[0]
    register_build(config_path)


if __name__ == "__main__":
    logging.basicConfig()
    sys.exit( main(sys.argv) )


