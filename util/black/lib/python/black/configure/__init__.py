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

# Black "configure" command support.
#
# One of the std Black commands is "configure" which typically
# processes configure options and generated configuration file(s)
# specifying certain data appropriate for the specific project
# and user configuration choices. Think "autoconf" not written in
# m4 and with more config file output formats: C header file, 
# NT batch file, Bourne shell script, Python module, Perl module.
# 

import os, sys, re, types, getopt
import stat
from UserDict import UserDict
if sys.platform.startswith('win'):
    import _winreg
import black
import itertools

try:
    basestring
except NameError:
    basestring = (str, unicode)



#---- exceptions

class ConfigureError(black.BlackError):
    pass



#---- global variables

verbosity = 0           # <0==quiet, 0==normal, >0==versbose
out = sys.stdout        # can be overridden

items = None            # the global dictionary of configuration items


#---- configuration item class heirarchy
# Item                  a thing that needs to get done to configure a project
# |-> Datum             a piece of information
# | `-> BooleanDatum    a boolean piece of information
# |-> SetEnvVar         set an environment variable
# | `-> SetPathEnvVar   set a path-like (i.e. a list) environ variable
# `-> RunEnvScript      run a given batch or shell script (Note: the 'run'
#                       is not done at "configure"-time but when the
#                       environment is setup from the resulting environment
#                       setup file (i.e. batch or shell script))
#

class Item:
    """A thing that needs to get done for configuration of a project."""

    # Serialization of configuration vars is sorted by
    # (<serialization ordinal>, <variable name>).
    serializationOrdinal = 100

    def __init__(self, name, desc=None, serializeAs=[],
                 acceptedOptions=None, optionHelp=None):
        if desc is None:
            desc = name
        self.name = name        # identifier for this datum
        self.desc = desc        # readable description of datum
        self.serializeAs = serializeAs # names of config files types to
                                # serialize to (e.g. "perl", "env")
        # "acceptedOptions", if not None, is a 2-tuple giving the
        # short and long getopt specs that this Item object cares about
        #  e.g.   ("v", [])  or ("v", ["verbose"]) or ("f:", ["makefile="])
        self.acceptedOptions = acceptedOptions
        # the list of user-specified options masked by this object's
        # "acceptedOptions" is appended to "chosenOptions" before
        # either Determine() or Get() is called on the object
        self.chosenOptions = []
        # this is an optional string which is used to describe the options
        # that this item accepts
        if optionHelp:
            self.optionHelp = optionHelp
        elif self.acceptedOptions:
            options = []
            for shortOpt in _ParseShortOptionString(self.acceptedOptions[0]):
                if shortOpt.endswith(":"):
                    options.append("-%s<arg>" % shortOpt[:-1])
                else:
                    options.append("-%s" % shortOpt)
            for longOpt in self.acceptedOptions[1]:
                if longOpt.endswith("="):
                    options.append("--%s=<arg>" % longOpt[:-1])
                else:
                    options.append("--%s" % longOpt)
            self.optionHelp = "        %s\n" % (", ".join(options))
        # this is set to true by the Determine() method after
        # self.value has be determined and set
        self.determined = 0

    def Determine(self):
        """Determine, given choices, if and how to get the thing done.
        
        Set "self.applicable" to true iff this thing needs to get done.
        Set "self.determined" when iff it is known how to do this thing.
        Raise "ConfigureError" if cannot determine and must.
        Put all information required for serialization in "self.value".
        Return "self.applicable".
        """
        # Create a common skeleton and describe pieces (internal methods)
        # that sub classes have to fill out:
        #   _
        try:
            return self.applicable
        except AttributeError:
            self._Determine_WriteInit()
            self._Determine_Do()
            if self.applicable:
                self._Determine_Sufficient()
            self._Determine_WriteFini()
            return self.applicable

    def Get(self):
        """Return the information require to serialize this thing.
        
        Try to Determine if not already determined.
        Return None if this thing is not applicable.
        """
        if not self.determined:
            self.Determine()
        if not self.applicable:
            return None
        else:
            return self.value

    def Serialize(self, streams):
        """Serialize how to do this thing to the appropriate config streams.
        
        "appropriate" is defined by the self.serializeAs array which gives
        keys to the "streams" dictionary. Do not attempt to serialize if
        this thing is not applicable.
        """
        if self.applicable:
            for type_ in self.serializeAs:
                if type_ == "python":
                    self._Serialize_AsPython(streams["python"])
                elif type_ == "perl":
                    self._Serialize_AsPerl(streams["perl"])
                elif type_ == "cheader":
                    self._Serialize_AsCHeader(streams["cheader"])
                elif type_ == "env":
                    if "bash" in streams:
                        self._Serialize_AsBash(streams["bash"])
                    if "batch" in streams:
                        self._Serialize_AsBatch(streams["batch"])
                else:
                    raise ConfigureError("Don't know how to serialize thing "\
                        "%s to a '%s' stream.\n" %\
                        (self.name, type_))

    # To be useful this class will have to be subclassed. To do that only
    # the following methods should have to be subclassed. At minimum only
    # _Determine_Do() and one of the _Serialize_As*() methods should have
    # to be subclassed. _Determine_Do() must set self.applicable,
    # self.determined, and possibly self.value as required in the Determine()
    # doc string.
    def _Determine_WriteInit(self):
        out.startItem()
        out.write("determining %s..." % self.desc)
    def _Determine_Do(self):
        self.applicable = None
        self.determined = 1
    def _Determine_Sufficient(self):
        """return iff self.value is sufficient/acceptable"""
        return 1
    def _Determine_WriteFini(self):
        if self.applicable:
            out.write("<applicable>\n")
        else:
            out.write("<not applicable>\n")
        out.endItem()

    def _Serialize_AsPython(self, stream):
        raise ConfigureError("Don't know how to serialize thing %s=%s as "\
            "Python.\n" % (self.name, repr(self.value)))
    def _Serialize_AsPerl(self, stream):
        raise ConfigureError("Don't know how to serialize thing %s=%s as "\
            "Perl.\n" % (self.name, repr(self.value)))
    def _Serialize_AsCHeader(self, stream):
        raise ConfigureError("Don't know how to serialize thing %s=%s as "\
            "C.\n" % (self.name, repr(self.value)))
    def _Serialize_AsBatch(self, stream):
        raise ConfigureError("Don't know how to serialize thing %s=%s as "\
            "NT batch commands.\n" % (self.name, repr(self.value)))
    def _Serialize_AsBash(self, stream):
        raise ConfigureError("Don't know how to serialize thing %s=%s as "\
            "Bash commands.\n" % (self.name, repr(self.value)))


class Datum(Item):
    def __init__(self, name, desc=None, serializeAs=["perl", "python"],
                 value=None, acceptedOptions=None, optionHelp=None):
        if desc is None:
            desc = name
        Item.__init__(self, name, desc=desc, serializeAs=serializeAs,
            acceptedOptions=acceptedOptions, optionHelp=optionHelp)
        # A simple datum can be initialize with a non-None value.
        self.value = value
        if self.value is not None:
            self.applicable = 1
            self.determined = 1

    def _Determine_WriteFini(self):
        if not self.applicable:
            out.write("<not applicable>\n")
        elif self.value is not None:
            if str(self.value) == "":
                out.write("<empty string>\n")
            else:
                out.write(str(self.value) + "\n")
        else:
            out.write("<could not determine>\n")
        out.endItem()

    def _Serialize_AsPython(self, stream):
        if self.value is None:
            pass
        elif isinstance(self.value, (basestring, int, bool, list, tuple, dict)):
            stream.write('%s = %s\n' % (self.name, repr(self.value)))
        else:
            stream.write('%s = %s\n' % (self.name, repr(str(self.value))))

    def _Serialize_AsPerl(self, stream):
        if self.value is None:
            pass
        elif isinstance(self.value, str):
            stream.write('$%s = %s;\n' % (self.name, repr(self.value)))
            stream.scalarExports.append(self.name)
        elif isinstance(self.value, unicode):
            try:
                stream.write('$%s = %s;\n' % (self.name, repr(str(self.value))))
            except UnicodeError, ex:
                raise ConfigureError("can't serialize '%s' unicode datum "
                                     "to Perl because can't convert it to "
                                     "a string: %s" % (self.name, ex))
            stream.scalarExports.append(self.name)
        elif isinstance(self.value, bool):
            stream.write('$%s = %s;\n' % (self.name, int(self.value)))
            stream.scalarExports.append(self.name)
        elif isinstance(self.value, int):
            stream.write('$%s = %s;\n' % (self.name, self.value))
            stream.scalarExports.append(self.name)
        elif isinstance(self.value, dict):
            # write it as:  %name = (key0,val0,key1,val1,...);
            merge = itertools.chain(*map(list, self.value.items()))
            stream.write('%%%s = %s;\n' % (self.name, tuple(merge)))
            stream.hashExports.append(self.name)
        elif isinstance(self.value, (list, tuple)):
            stream.write('@%s = %s;\n' % (self.name, tuple(self.value)))
            stream.arrayExports.append(self.name)
        else:
            raise ConfigureError("Don't know how to serialize datum %s of "\
                "type %s as Perl code.\n" % (self.name, type(self.value)))

    def _Serialize_AsCHeader(self, stream):
        if self.value is None:
            pass
        elif isinstance(self.value, str):
            stream.write('#define %s "%s"\n' % (self.name, self.value))
        elif isinstance(self.value, (int, long)):
            stream.write('#define %s %d\n' % (self.name, self.value))
        else:
            raise ConfigureError("Don't know how to serialize datum %s of "\
                "type %s as C preprocessor code.\n" %\
                (self.name, type(self.value)))

    def _Serialize_AsBatch(self, stream):
        if self.value is None:
            pass
        elif isinstance(self.value, str):
            stream.write('set %s=%s\n' % (self.name, self.value))
        elif isinstance(self.value, int):
            stream.write('set %s=%d\n' % (self.name, self.value))
        else:
            raise ConfigureError("Don't know how to serialize datum %s of "\
                "type %s as Batch file commands.\n" %\
                (self.name, type(self.value)))

    def _Serialize_AsBash(self, stream):
        if self.value is None:
            pass
        elif isinstance(self.value, str):
            value = self.value
            if sys.platform.startswith("win"):
                value = value.replace(os.sep, "/")
            stream.write('export %s=%s\n' % (self.name, value))
        elif isinstance(self.value, int):
            stream.write('export %s=%d\n' % (self.name, self.value))
        else:
            raise ConfigureError("Don't know how to serialize datum %s of "\
                "type %s as Bash script commands.\n" %\
                (self.name, type(self.value)))


class BooleanDatum(Datum):
    def _Determine_WriteInit(self):
        out.startItem()
        out.write("determining if %s..." % self.desc)

    def _Determine_WriteFini(self):
        if not self.applicable:
            out.write("<not applicable>\n")
        elif self.value is None:
            out.write("<could not determine>\n")
        elif not self.value:
            out.write("no\n")
        else:
            out.write("yes\n")
        out.endItem()


class SetEnvVar(Item):
    """Set an environment variable."""
    def __init__(self, name, desc=None, serializeAs=["env"],
                 acceptedOptions=None, optionHelp=None):
        if desc is None:
            desc = "%s environment variable" % name
        Item.__init__(self, name, desc=desc, serializeAs=serializeAs,
            acceptedOptions=acceptedOptions, optionHelp=optionHelp)

    def _Determine_WriteFini(self):
        if not self.applicable:
            out.write("<not applicable>\n")
        elif not self.determined:
            out.write("<could not determine>\n")
        elif self.value is None:
            out.write("<unset>\n")
        else:
            out.write(str(self.value) + "\n")
        out.endItem()

    def _Serialize_AsPython(self, stream):
        stream.write("import os")
        if self.value is None or isinstance(self.value, basestring):
            stream.write("os.environ[%s] = %s\n" %\
               (repr(self.name), repr(self.value)))
        else:
            raise ConfigureError("Don't know how to serialize setting "\
                "environment variable %s of type %s as Python code.\n" %\
                (self.name, type(self.value)))

    def _Serialize_AsPerl(self, stream):
        if self.value is None:
            stream.write('$ENV{%s} = "";\n' % repr(self.name))
        elif isinstance(self.value, str):
            stream.write('$ENV{%s} = %s;\n' %\
                (repr(self.name), repr(self.value)))
        elif isinstance(self.value, int):
            stream.write('$ENV{%s} = %d;\n' % (repr(self.name), self.value))
        else:
            raise ConfigureError("Don't know how to serialize setting "\
                "environment variable %s of type %s as Perl code.\n" %\
                (self.name, type(self.value)))

    def _Serialize_AsBatch(self, stream):
        if self.value is None:
            stream.write('set %s=\n' % self.name)
        elif isinstance(self.value, (str, int)):
            stream.write('set %s=%s\n' % (self.name, self.value))
        elif isinstance(self.value, (list, tuple)):
            stream.write('set %s=%s\n' %\
                (self.name, os.pathsep.join(self.value)))
        else:
            raise ConfigureError("Don't know how to serialize setting "\
                "environment variable %s of type %s as Batch file "\
                "commands.\n" % (self.name, type(self.value)))

    def _Serialize_AsBash(self, stream):
        if self.value is None:
            stream.write('unset %s\n' % self.name)
        elif isinstance(self.value, str):
            value = self.value
            if sys.platform.startswith("win"):
                value = value.replace(os.sep, "/")
            stream.write('export %s=%s\n' % (self.name, value))
        elif isinstance(self.value, int):
            stream.write('export %s=%s\n' % (self.name, self.value))
        elif isinstance(self.value, (list, tuple)):
            value = self.value
            pathsep = os.pathsep
            if sys.platform.startswith("win"):
                for i, v in enumerate(value):
                    if isinstance(v, str):
                        value[i] = v.replace("\\", "\\\\")
                pathsep = "\\;" # escape for bash
            stream.write('export %s=%s\n' %\
                (self.name, pathsep.join(value)))
        else:
            raise ConfigureError("Don't know how to serialize setting "\
                "environment variable %s of type %s as Bash script "\
                "commands.\n" % (self.name, type(self.value)))


class RunEnvScript(Item):
    """Run a batch file or source a bash script (as appropriate)"""
    def __init__(self, name, desc=None, serializeAs=["env"],
                 acceptedOptions=None, optionHelp=None):
        Item.__init__(self, name, desc=desc, serializeAs=serializeAs,
                      acceptedOptions=acceptedOptions, optionHelp=optionHelp)

    def _Serialize_AsBatch(self, stream):
        if self.value:
            stream.write('call "%s" >nul\n' % self.value)

    def _Serialize_AsBash(self, stream):
        if self.value:
            if sys.platform.startswith("win"):
                return # don't run batch files in msys
            stream.write('source %s\n' % self.value)


class SetPathEnvVar(SetEnvVar):
    def __init__(self, name, desc=None, serializeAs=["env"],
                 acceptedOptions=None, optionHelp=None, exts=[]):
        SetEnvVar.__init__(self, name, desc=desc, serializeAs=serializeAs,
                           acceptedOptions=acceptedOptions,
                           optionHelp=optionHelp)
        self.exts = exts

    def Contains(self, pathName):
        """return true iff the given path is on the path list"""
        if not self.determined:
            self.Determine()
        pathName = os.path.normcase(os.path.normpath(pathName))
        for pathElem in self.value:
            pathElem = os.path.normcase(os.path.normpath(pathElem))
            if pathName == pathElem:
                return 1
        else:
            return 0


#---- Configuration items dictionary-like singleton
# This data structure is created during a "Configure()" and allows
# configuration items to access other configuration items as necessary.

class Items(UserDict):
    """Basically just a dictionary of configuration items (each of which
    is an instance of an "Item")."""
    
    def __init__(self, rawItems):
        """Canonicalize a dictionary of configuration items.

        Values in a configuration item dictionary are, canonically, an object
        subclassed from black.configure.Item. However, shortcuts are allowed
        for specification. For example, a Blackfile could simple set a string
        value to create a configuration datum that is always applicable, has
        no related configuration option, and whose value is that string.
        """
        UserDict.__init__(self)
    
        for name, item in rawItems.items():
            if item is None:
                continue
            elif isinstance(item, (int, long, float, str, tuple, list, dict)):
                # this is a simple Datum()
                self.data[name] = Datum(name, value=item)
            elif type(item) == types.InstanceType:
                # this had better be an instance subclassed from class Item
                if isinstance(item, Item):
                    self.data[name] = item
                else:
                    raise ConfigureError("The configuration item '%s' does "\
                        "not derive from class %s.\n" % (name, Item))
            else:
                raise ConfigureError("Don't know how to massage a "\
                    "configuration item of type %s: %s" % (type(item), item))


#---- Config streams:
# Write-only file-like objects that produce configuration streams for various
# languages.
#

class ConfigStream:
    def __init__(self, filename):
        self.filename = filename
        self.stream = open(self.filename, "w")
    def write(self, s):
        self.stream.write(s)
    def close(self):
        self.stream.close()
        out.write("'%s' created\n" % self.filename)


class PythonConfigStream(ConfigStream):
    def __init__(self, configFileBase):
        suffix = ".py"
        ConfigStream.__init__(self, configFileBase + suffix)
        self.stream.write("""#!/usr/bin/env python
#
# *** WARNING ***
# This file was autogenerated by Black's configuration mechanism.
# Any edit you make wil be lost when this project is next configured

""")

    def close(self):
        # Add a mainline to the Python config file for querying the config.
        self.stream.write("""

#---- mainline
# Usage:
#   python bkconfig.py SUBSTRING...
# Prints the value of all config variables matching each substring.
#
def _main():
    import sys
    from pprint import pprint

    m = sys.modules[__name__]
    var_names = [k for k in m.__dict__.keys() if not k[0]=='_']
    matches = {} # <var-name> -> (<var-value>, <is-exact-match>)
    for substring in sys.argv[1:]:
        substring_lower = substring.lower()
        for var_name in var_names:
            if substring == var_name:
                matches[var_name] = (getattr(m, var_name), True)
            elif substring_lower in var_name.lower():
                matches[var_name] = (getattr(m, var_name), False)

    if len(matches) == 1 and matches.values()[0][1]:
        # If there is only one result and it was named exactly, then
        # don't give the prefix. This enables doing things like:
        #   cd `./bkconfig.py mozBin`
        print matches.values()[0][0]
    else:
        for name, (value, is_exact_match) in sorted(matches.items()):
            print "%s: %s" % (name, value)

if __name__ == "__main__":
    _main()
""")

        ConfigStream.close(self)

        # `chmod +x $self.filename` so can just do 
        # `./bkconfig.py SUBSTRING...`
        mode = stat.S_IMODE(os.stat(self.filename).st_mode)
        os.chmod(self.filename, mode | 0100)
    


class PerlConfigStream(ConfigStream):
    def __init__(self, configFileBase):
        suffix = ".pm"
        ConfigStream.__init__(self, configFileBase + suffix)
        self.stream.write("""
# ***** This file was autogenerated by Black's configuration mechanism.
# Any edit you make wil be lost when this project is next configured

package bkconfig;
require Exporter;
@ISA = qw(Exporter);

""")
        # For a serialized Perl variable to be exported from the created
        # module the configuration item must append the variable name
        # to the appropriate one of the following lists
        self.scalarExports = []
        self.arrayExports = []
        self.hashExports = []

    def close(self):
        self.stream.write("\n@EXPORT = qw (")
        for varName in self.scalarExports:
            self.stream.write(" $" + varName)
        for varName in self.arrayExports:
            self.stream.write(" @" + varName)
        for varName in self.hashExports:
            self.stream.write(" %" + varName)
        self.stream.write(" );\n")
        ConfigStream.close(self)
        

class EnvironConfigStream(ConfigStream):
    def __init__(self, configFileBase, type=None):
        if type is None:
            if sys.platform.startswith("win"):
                type = "batch"
            else:
                type = "bash"
        if type == "batch":
            suffix = ".bat"
            header = """@echo off
rem ***** This file was autogenerated by Black's configuration mechanism.
rem Any edit you make wil be lost when this project is next configured

"""
        else:
            suffix = ".sh"
            header = """
# ***** This file was autogenerated by Black's configuration mechanism.
# Any edit you make wil be lost when this project is next configured

"""

        ConfigStream.__init__(self, configFileBase + suffix)
        self.stream.write(header)



#---- other support routines

def _ParseShortOptionString(s):
    """Return of list of getopt short option specifiers from a joined list."""
    shortOpts = []
    for char in s:
        if char == ":":
            try:
                shortOpts[-1] += ":"
            except IndexError:
                raise ConfigureError("Short option string '%s' starts with "\
                    "a colon. This is an illegal getopt format." % s)
        else:
            shortOpts.append(char)
    return shortOpts



#---- public inteface

def ImportProjectConfig(blackFileName, blackFile):
    """Import the project configuration Python module.
    
    The project configuration files are presumed to live in the
    same directory as the project blackfile. The configuration
    Python module is presumed to be called "bkconfig". (XXX This
    will (eventually) be made overridable via a entry in the blackfile.)
    """
    import imp
    dirName = os.path.dirname(blackFileName)
    moduleName = "bkconfig"
    file, pathname, description = imp.find_module(moduleName, [dirName])
    return imp.load_module(moduleName, file, pathname, description)


def GetOptionMaps(items):
    # determine the allowable options (ensuring no conflicts)
    shortMap = {}  # map short and long options
    longMap = {}   #  to list of items that care about them
    for name, item in items.items():
        if item.acceptedOptions:
            shortString, longOpts = item.acceptedOptions
            # abort if there are any conflicts (i.e. an option that one
            # item thinks should take an arg and one that does not)
            for shortOpt in _ParseShortOptionString(shortString):
                if shortOpt.endswith(":"):
                    conflictingShort = shortOpt[0:-1]
                else:
                    conflictingShort = shortOpt + ":"
                if shortMap.has_key(conflictingShort):
                    raise ConfigureError("Short option string '%s' for "\
                        "item '%s' conflicts with short option '%s' from "\
                        "item(s) %s\n" % (shortOpt, item.name,\
                        conflictingShort,\
                        [item.name for item in shortMap[conflictingShort]]))
                elif shortMap.has_key(shortOpt):
                    shortMap[shortOpt].append(item)
                else:
                    shortMap[shortOpt] = [item]
            for longOpt in longOpts:
                if longOpt.endswith("="):
                    conflictingLong = longOpt[0:-1]
                else:
                    conflictingLong = longOpt + "="
                if longMap.has_key(conflictingLong):
                    raise ConfigureError("Long option string '%s' for "\
                        "item '%s' conflicts with long option '%s' from "\
                        "item(s) %s\n" % (longOpt, item.name, conflictingLong,\
                        [item.name for item in longMap[conflictingLong]]))
                elif longMap.has_key(longOpt):
                    longMap[longOpt].append(item)
                else:
                    longMap[longOpt] = [item]

    return (shortMap, longMap)


def Configure(options, blackFileName, blackFile):
    global items    # made global so that configuration items
                    # can access others during their own processing
    # "massage" the user-defined list of configuration items
    # and add some Black standard items
    items = Items(blackFile.configuration)
    items["blackFileName"] = Datum("blackFileName",
                                   desc="the project Blackfile name",
                                   value=blackFileName)
    import black
    items["blackVersion"] = Datum("blackVersion",
        desc="the version of Black with which this project was configured",
        value=black.GetVersionTuple())
    items["blackConfigureOptions"] = Datum("blackConfigureOptions",
        desc="the configure options specified for this project configuration",
        value=options)

    # determine the allowable options (ensuring no conflicts)
    shortMap, longMap = GetOptionMaps(items)

    # process the options list to get the users choices and let
    # the configuration items that care know about these choices
    try:
        optlist, args = getopt.getopt(options, "".join(shortMap.keys()),
                                      longMap.keys())
    except getopt.GetoptError, msg:
        raise ConfigureError(msg)
    for opt,optarg in optlist:
        if opt.startswith("--"):
            if longMap.has_key(opt[2:]):
                itemsThatCare = longMap[ opt[2:] ]
            else:
                itemsThatCare = longMap[ opt[2:]+"=" ]
        else:
            if shortMap.has_key(opt[1:]):
                itemsThatCare = shortMap[ opt[1:] ]
            else:
                itemsThatCare = shortMap[ opt[1:]+":" ]
        for item in itemsThatCare:
            item.chosenOptions.append( (opt, optarg) )
            
    # determine the value of each item
    for item in items.values():
        item.Determine()

    # serialize the configured values (add a configuration item for
    # the environment setup script name)
    configFileBase = os.path.join(os.path.dirname(blackFileName), "bkconfig")
    streams = {}
    streams["bash"] = EnvironConfigStream(configFileBase, "bash")
    items["envScriptName"] = Datum("envScriptName",
        desc="the project environment setup script name",
        value=streams["bash"].filename)
    items["envScriptName"].Determine()
    if sys.platform.startswith("win"):
        streams["batch"] = EnvironConfigStream(configFileBase, "batch")
        items["envScriptName"] = Datum("envScriptName",
            desc="the project environment setup script name",
            value=streams["batch"].filename)
        items["envScriptName"].Determine()
    streams["perl"] = PerlConfigStream(configFileBase)
    streams["python"] = PythonConfigStream(configFileBase)
    sorteditems = items.items()
    sorteditems.sort(key=lambda i: (i[1].serializationOrdinal, i[0]))
    for name, item in sorteditems:
        item.Serialize(streams)
    for stream in streams.values():
        stream.close()


