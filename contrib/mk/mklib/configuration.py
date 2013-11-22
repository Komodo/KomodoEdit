# Copyright (c) 2005-2007 ActiveState Software Ltd.

"""Configuration support for Makefile.py's."""

import sys
import os
from os.path import isfile, basename, splitext, join, dirname, normpath, \
                    exists, abspath
from pprint import pprint
import imp
import types

from mklib.common import *


class ConfigurationType(type):
    def __init__(cls, name, bases, dct):
        super(ConfigurationType, cls).__init__(name, bases, dct)
        if dct["__module__"] != "mklib.configuration":
            # Register this on the Makefile.
            frame = sys._getframe(1)
            makefile = frame.f_globals["_mk_makefile_"]
            makefile.define_configuration(cls, name, bases, dct)
            log_makefile_defn("Configuration", name, frame)


class Configuration(object):
    """A basic configuration object.
    
    This lightly wraps a config.py module typically created with a
    `configure.py' script (using the associate `configurelib' utility).

    Usage in a Makefile.py
    ----------------------

        from mklib import Configuration
        class cfg(Configuration):
            pass

    This will expect a `config.py' file next to `Makefile.py' that will
    be imported and provided to each Task instance as `self.cfg'. (Note
    that the Task attribute will be `self.cfg' whatever the name of the
    defined Configuration class.)
    
        class cfg(Configuration):
            prefix = "foo"

    This will expecte a `fooconfig.py' file instead of `config.py'.
    Projects are encouraged to use a short prefix for config modules to
    avoid possible Python module name collisions.

    If there is no Configuration class definition in a `Makefile.py'
    then `self.cfg' on Tasks will be None.
    """
    __metaclass__ = ConfigurationType
    _path = None
    prefix = None
    dir = os.curdir  # Can be set to, say, '..' to pick up config.py up on dir.

    def __init__(self, makefile, config_file_path_override=None):
        self.makefile = makefile
        if config_file_path_override:
            self._path = config_file_path_override
        else:
            prefix = self.prefix or ''
            self._path = normpath(join(makefile.dir, self.dir,
                                       prefix + "config.py"))
        self._reload()

    def __repr__(self):
        return "<Configuration '%s'>" % self._path

    def as_dict(self):
        """Return a dict of config vars.
        
        This skips internal symbols (those starting with '_') and
        instance methods. It will *get* all properties.
        """
        d = dict((k,v) for k,v in self._mod.__dict__.items()
                 # Skip internal symbols of the module.
                 if not k.startswith('_'))
        # Also get all properties and public attributes (but not
        # methods).
        for attrname in dir(self):
            if attrname.startswith('_'): continue
            try:
                attrtype = type(getattr(self.__class__, attrname))
            except AttributeError:
                # This must be an instance attribute.
                d[attrname] = getattr(self, attrname)
            else:
                if attrtype != types.UnboundMethodType:
                    # Skip instance methods.
                    d[attrname] = getattr(self, attrname)
        return d

    def as_simple_obj(self):
        """Return a simple StaticConfiguration instance with all config vars.

        This essentially "freezes" the set of config vars (some of which
        might normally be determined dynamically via properties).  This
        can be useful to pass the configuration to a tool that needs all
        the values statically (e.g. patchtree.py).
        """
        return StaticConfiguration(**self.as_dict())

    def _reload(self):
        log.debug("reading `%s'", self._path)
        name = splitext(basename(self._path))[0]
        conf_pyc = splitext(self._path)[0] + ".pyc"
        if isfile(conf_pyc):
            # If the .py is newer than the .pyc, the .pyc sometimes (always?)
            # gets imported instead, causing problems.
            os.remove(conf_pyc)
        try:
            cfg_dir = dirname(abspath(self._path))
            file, path, desc = imp.find_module(name, [cfg_dir])
            curr_dir = os.getcwd()
            if curr_dir != cfg_dir:
                os.chdir(cfg_dir)
            try:
                self._mod = imp.load_module(name, file, path, desc)
            finally:
                if curr_dir != cfg_dir:
                    os.chdir(curr_dir)
        except ImportError, ex:
            if not exists(self._path):
                details = "`%s' does not exist" % self._path
                if exists(join(dirname(self._path), "configure.py")):
                    details += " (perhaps you need to run './configure.py' first)"
            else:
                details = str(ex)
            raise MkError("could not import config file '%s': %s"
                          % (self._path, details))

    def __getattr__(self, name):
        if not hasattr(self._mod, name):
            raise AttributeError("configuration has no attribute '%s'" % name)
        return getattr(self._mod, name)


class StaticConfiguration(object):
    """A static "frozen" configuration.
    
    From Configuration.as_simple_obj().
    """
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)



