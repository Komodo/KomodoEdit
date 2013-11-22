#!/usr/bin/env python

import os
from os.path import dirname, abspath, expanduser, join
import re
import sys
import logging
from glob import glob

try:
    from configurelib import main, ConfigVar, ConfigureError, Profile
except ImportError:
    # `mk' supports an option to help find the configurelib package.
    configurelib_path = os.popen("mk --configurelib-path").read().strip()
    sys.path.insert(0, configurelib_path)
    from configurelib import main, ConfigVar, ConfigureError, Profile
    del configurelib_path

sys.path.insert(0, "support")
import buildutils
del sys.path[0]


log = logging.getLogger("configure")



#---- config vars

class ObjDir(ConfigVar):
    name = "obj_dir"

    def add_options(self, optparser):
        optparser.add_option("--obj-dir",
            help="dir in which to put build products (default is generally "
                 "reasonable)")

    def determine(self, config_var_from_name, options):
        if options.obj_dir:
            self.value = options.obj_dir
        else:
            self.value = join("build", "release")

class Version(ConfigVar):
    name = "version"

    def add_options(self, optparser):
        optparser.add_option("-V", dest="version",
            help="Komodo version string (e.g. 4.2.0a1, 1.0a1). By default "
                 "VERSION file is used.")

    def determine(self, config_var_from_name, options):
        if options.version:
            self.value = options.version
        else:
            ver_path = join(dirname(__file__), "VERSION")
            self.value = open(ver_path).read().strip()
        #XXX validate and normalize this

class VersionInfo(ConfigVar):
    name = "version_info"
    deps = ["version"]

    def determine(self, config_var_from_name, options):
        version = config_var_from_name["version"].value
        self.value = buildutils.split_short_ver(version, intify=True, pad_zeros=3)


config_vars = [
    ObjDir(),
    Version(),
    VersionInfo(),
]


#---- mainline

if __name__ == "__main__":
    main(config_vars, default_config_file_path="koconfig.py",
         project_name="komodo")

