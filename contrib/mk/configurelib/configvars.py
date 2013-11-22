# Copyright (c) 2007 ActiveState Software Ltd.

#TODO: docstring

#TODO: pare down this import list
import os
import sys
from os.path import basename, join, splitext, exists
from glob import glob
import logging
import traceback
import optparse
import types
import re
import stat
from pprint import pprint

from configurelib.common import *


#---- configuration variable classes

class ConfigVar(object):
    """Base ConfigVar class. Typically all your config vars will use
    specialized subclasses of this. The main ConfigVar API is defined here.
    """
    name = None
    doc = None
    deps = None  # set, sequence or generator of config var dependencies
    value = None
    
    determined = False # set True by the driver after calling .determine()

    def __init__(self, name=None, doc=None):
        if name is not None:
            self.name = name
        if self.name is None:
            raise ConfigureError("no name for config var: %s"
                                 % self.__class__)
        if doc is None:
            doc = self.__class__.__doc__
        self.doc = doc

    def __repr__(self):
        return "<ConfigVar '%s'>" % self.name

    @property
    def description(self):
        """A short one-liner description of this config var."""
        if self.doc:
            return self.doc.splitlines(0)[0]
            #return "%s (%s)" % (self.doc.splitlines(0)[0], self.name)
        else:
            return self.name

    def add_options(self, optparser):
        """Add command-line configure options for this config var."""
        pass

    def determine(self, config_var_from_name, options):
        """Determine the value for this config var and set it to
        'self.value'.
        """

    def serialize(self, format, stream):
        """Serialize the current config var.
        
            "format" is a string indicating the output format.
                Currently supported formats:
                    Python      a variable in a Python module
            "stream" is the stream to which to write.
        """
        if format == "Python":
            stream.write("%s = %s\n" % (self.name, repr(self.value)))
        else:
            raise ConfigureError("unknown serialization format: %r" % format)


#TODO: drop per-plat support and dep on target_plat
#TODO: add a "PerPlatProfile" subclass with the target_plat dep
class Profile(ConfigVar):
    """configuration profile
    
    Adds a -p|--profile option to specify a configuration profile. The
    given 'profile_dirs' are searched for "*.profile" for available
    profiles. 

    This can help simplify configuration. E.g., "./configure.py -p full"
    could imply a large number of options.
    
    If you use this config var you must also use the TargetPlat config var
    -- which is used to support platform-specific options in the .profile
    file (see description of the format below).
    
    After being determined this config var has the following attributes:
        value           the profile name
        profile_path    path to the loaded profile file
        profile_args    command-line args loaded from the profile file


    Limitations
    -----------
    
    A profile file cannot specify the following options:
    - "--platform" because the "target_plat" config var is determined
      before the profile file is loaded (to filter plat-specific options)
    - "-p|--profile" because recursive profiles are not supported.


    Profile file format
    -------------------

    A profile file is a list of configure options (one per line)
    that is added to argv. E.g.:
    
        --python-src=2.5
        --with-bzip2
    
    Lines starting with '#' are ignore (comments). E.g.:
    
        # The default ActivePython 2.5 build profile.

    An option can be restricted to just a certain target platform name
    (the platform name is matched against the result of .name() from config
    var 'target_plat'). E.g.:
    
        solaris10-x86: --without-ssl
    """
    name = "profile"
    deps = ["target_plat"]
    # 'value' attribute is the profile *name*
    profile_path = None  # path to selected .profile file
    profile_args = None  # args from loaded .profile file

    def __init__(self, profile_dirs):
        ConfigVar.__init__(self)
        assert not isinstance(profile_dirs, basestring) # common mistake
        self.profile_dirs = profile_dirs
        self.profile_path_from_name = dict(   # the available profiles
            (splitext(basename(f))[0], f)
            for d in profile_dirs
            for f in glob(join(d, "*.profile"))
        )

    def add_options(self, optparser):
        optparser.add_option("-p", "--profile",
            help="load one of the following configuration profiles (%s)"
                 % ', '.join(self.profile_path_from_name.keys()))

    def _load_profile(self, profile_path, platname):
        log.debug("loading profile '%s'", profile_path)
        args = []
        plat_line_pat = re.compile(r"^(\S+)\s*:\s*(.*?)$")
        for line in open(profile_path, 'r'):
            line = line.strip()
            if not line: continue
            if line[0] == "#": continue
            match = plat_line_pat.match(line)
            if match:  # <platname>: <args>
                if match.group(1) == platname:
                    for arg in match.group(2).split():
                        args.append(arg)
            else:      # <args>
                for arg in line.split():
                    args.append(arg)
        return args

    def determine(self, config_var_from_name, options):
        if options.profile is None:
            self.value = None
            return
        
        if options.profile in self.profile_path_from_name:
            self.profile_path = self.profile_path_from_name[options.profile]
            self.value = options.profile
        elif exists(options.profile):
            self.profile_path = options.profile
            self.value = splitext(basename(options.profile))[0]
        else:
            raise ConfigureError(
                "profile '%s' is not one of the available "
                "ones (%s), nor is it an existing path"
                % (options.profile,
                   ', '.join(self.profile_path_from_name.keys())))
        
        platname = config_var_from_name["target_plat"].value.name()
        self.profile_args = self._load_profile(self.profile_path, platname)



class WithOption(ConfigVar):
    """A boolean config var for a given feature name.
    
    The config var name will be "with_$feature" and "--with[out]-$feature"
    configure options are added.
    """
    def __init__(self, feature, default=None, doc=None):
        if doc is None:
            doc = "with %s" % feature
        self.code_safe_feature = feature.replace('-', '_')
        ConfigVar.__init__(self, "with_"+self.code_safe_feature, doc=doc)
        self.feature = feature
        self.default = default

    def add_options(self, optparser):
        optparser.add_option(
            "--with-"+self.feature, "--without-"+self.feature,
            dest=self.name, action="callback", nargs=0,
            callback=self._set_with_opt)
        
    def _set_with_opt(self, option, opt_str, value, optparser):
        if opt_str.startswith("--with-"):
            setattr(optparser.values, self.name, True)
        elif opt_str.startswith("--without-"):
            setattr(optparser.values, self.name, False)
        else:
            raise ConfigureError("unexpected option: %r" % opt_str)

    def determine(self, config_var_from_name, options):
        self.value = getattr(options, self.name, None)
        if self.value is None:
            self.value = self.default


class BuildPlat(ConfigVar):
    """A platinfo.PlatInfo instance for the current platform.
    By default this is named 'build_plat'.
    """
    def __init__(self, name="build_plat", doc="build platform",
                 platinfo_class=None):
        ConfigVar.__init__(self, name, doc)
        self.platinfo_class = platinfo_class

    def determine(self, config_var_from_name, options):
        import platinfo
        # First ver to support useful __repr__().
        assert platinfo.__version_info__ >= (0,6,0)
        platinfo_class = self.platinfo_class or platinfo.PlatInfo
        self.value = platinfo_class()

    def serialize(self, format, stream):
        import platinfo
        assert format == "Python"
        platinfo_class = self.platinfo_class or platinfo.PlatInfo
        module = platinfo_class.__module__
        if module != "__main__":
            stream.write("import %s\n" % module)
        stream.write("%s = %s\n" % (self.name, repr(self.value)))


class TargetPlat(BuildPlat):
    """Like the "BuildPlat" config var, but offers a --platform option.
    Useful to support cross-building.
    """
    def __init__(self, name="target_plat", doc="target platform",
                 platinfo_class=None):
        BuildPlat.__init__(self, name, doc, platinfo_class)

    def add_options(self, optparser):
        optparser.add_option("--platform",
            help="specify a target platform other than current, "
                 "e.g., cross-building or compatibility builds")

    def determine(self, config_var_from_name, options):
        import platinfo
        # First ver to support useful __repr__().
        assert platinfo.__version_info__ >= (0,6,0)

        platinfo_class = self.platinfo_class or platinfo.PlatInfo
        if options.platform is None:
            self.value = platinfo_class()
        else:
            self.value = platinfo_class.from_name(options.platform)



#---- internal support stuff

#TODO: not used?
#def _load_profile(option, opt_str, value, optparser, profile_path_from_name):
#    """Handle the -p|--profile option.
#    
#    Read the named profile file and add the options in that file to the
#    option parser.
#    """
#    if value in profile_path_from_name:
#        profile_path = profile_path_from_name[value]
#    elif exists(value):
#        profile_path = value
#    else:
#        raise ConfigureError("profile '%s' is not one of the available "
#                             "ones (%s), nor is it an existing path"
#                             % (value,
#                                ', '.join(profile_path_from_name.keys())))
#
#    log.debug("loading config profile '%s'", profile_path)
#    profile_args = []
#    for line in open(profile_path, 'r'):
#        line = line.strip()
#        if not line: continue
#        for arg in line.split():
#            profile_args.append(arg)
#
#    optparser.rargs[0:0] = profile_args


