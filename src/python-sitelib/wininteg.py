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

"""
    Python interface to integrating an app with Microsoft Windows.

    Current it provides a command line and module integrate to add an
    remove file associations.
"""
# Dev Notes:
# - On Win9x QueryValueEx returns the empty string for a non-existant
#   default key value. On non-Win9x an EnvironmentError is raised. Care has
#   been made in the code to handle this API semantic difference.
#
#TODO:
#   - Use the ASSOC and FTYPE command line utils instead of all this
#     registry entry mucking, if possible! Do these commands exist even
#     on Win9x machine? I wonder.
#   - Perhaps reduce "add_assoc" to "register_type" (which includes a
#     default icon) and "add_assoc". Then "add_assoc" fails if there is
#     no type registered.
#   - Add interface for adding a shortcut on the desktop.
#   - Add interface for adding a shortcut on the quick launch bar.
#   - Test suite! There are subtle _winreg API differences on Win9x
#     which should be tested.

import os
import sys
import cmd
import pprint
import getopt
import logging
import itertools
if sys.platform.startswith("win"):
    import _winreg



#---- exceptions

class WinIntegError(Exception):
    pass



#---- globals

_version_ = (0, 2, 1)
log = logging.getLogger("wininteg")


#---- internal support routines

def _splitall(path):
    """Split the given path into all its directory parts and return the list
    of those parts (see Python Cookbook recipe for test suite.)
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


class _ListCmd(cmd.Cmd):
    """Pass arglists instead of command strings to commands.

    Modify the std Cmd class to pass arg lists instead of command lines.
    This seems more appropriate for integration with sys.argv which handles
    the proper parsing of the command line arguments (particularly handling
    of quoting of args with spaces).
    """
    name = "_ListCmd"
    
    def cmdloop(self, intro=None):
        raise NotImplementedError

    def onecmd(self, argv):
        # Differences from Cmd
        #   - use an argv, rather than a command string
        #   - don't specially handle the '?' redirect to 'help'
        #   - don't allow the '!' shell out
        if not argv:
            return self.emptyline()
        self.lastcmd = argv
        cmdName = argv[0]
        try:
            func = getattr(self, 'do_' + cmdName)
        except AttributeError:
            return self.default(argv)
        try:
            return func(argv)
        except TypeError, ex:
            log.error("%s: %s", cmdName, ex)
            log.error("try '%s help %s'", self.name, cmdName)
            if 1:   # for debugging
                print
                import traceback
                traceback.print_exception(*sys.exc_info())

    def default(self, args):
        log.error("unknown syntax: '%s'", " ".join(args))
        return 1

    def _do_one_help(self, arg):
        try:
            # If help_<arg1>() exists, then call it.
            func = getattr(self, 'help_' + arg)
        except AttributeError:
            try:
                doc = getattr(self, 'do_' + arg).__doc__
            except AttributeError:
                doc = None
            if doc: # *do* have help, print that
                sys.stdout.write(doc + '\n')
                sys.stdout.flush()
            else:
                log.error("no help for '%s'", arg)
        else:
            return func()

    # Technically this improved do_help() does not fit into _ListCmd, and
    # something like this would be more appropriate:
    #    def do_help(self, argv):
    #        cmd.Cmd.do_help(self, ' '.join(argv[1:]))
    # but I don't want to make another class for it.
    def do_help(self, argv):
        if argv[1:]:
            for arg in argv[1:]:
                retval = self._do_one_help(arg)
                if retval:
                    return retval
        else:
            doc = self.__class__.__doc__  # try class docstring
            if doc:
                sys.stdout.write(doc + '\n')
                sys.stdout.flush()
            elif __doc__:  # else try module docstring
                sys.stdout.write(__doc__)
                sys.stdout.flush()

    def emptyline(self):
        # Differences from Cmd
        #   - Don't repeat the last command for an emptyline.
        pass


def _parseFirstArg(cmd):
    cmd = cmd.strip()
    if cmd.startswith('"'):
        # The .replace() is to ensure it does not mistakenly find the
        # second '"' in, say (escaped quote):
        #           "C:\foo\"bar" arg1 arg2
        idx = cmd.replace('\\"', 'XX').find('"', 1)
        if idx == -1:
            raise WinIntegError("Malformed command: %r" % cmd)
        first, rest = cmd[1:idx], cmd[idx+1:]
        rest = rest.lstrip()
    else:
        if ' ' in cmd:
            first, rest = cmd.split(' ', 1)
        else:
            first, rest = cmd, ""
    return first


def _getTypeName(ext):
    """Calculate a reasonable Windows "type name" for the given extension."""
    assert ext[0] == '.', "Extension is invalid: '%s'" % ext

    # First try some common/generally accepted type name mappings.
    commonTypeMappings = {
        '.pl': 'Perl',
        '.py': 'Python.File',
        '.js': 'JSFile',
        '.xml': 'XMLFile',
        '.xsl': 'XSLFile',
        '.xslt': 'XSLTFile',
        '.pm': 'Perl.Module',
        '.t': 'Perl.TestScript',
        #XXX This is the name that ActiveTcl/TclPro uses for the .tcl file
        #    association. We choose to use its name as well.
        '.tcl': 'ActiveTclScript',
        '.php': 'PHPFile',
        '.plx': 'PlxFile',
        '.wsdl': 'WSDLFile',
    }
    typeName = commonTypeMappings.get(ext, None)

    # Fallback: the name will be "FOOFile" for an extension ".foo".
    if typeName is None:
        typeName = ext[1:].upper() + "File"

    return typeName

def _getTypeNameFromRegistry(ext, root=None):
    """Read the type name from the registry
    @param ext {unicode} The extension; must start with a leading period
    @param root {HKEY} The root tree to use; if unspecified, HKCR is used.
        (i.e. the merged tree)
    @returns {unicode} The type name, or None if not found
    """
    log.debug("_getTypeNameFromRegistry: getting '%s'", ext)
    assert ext[0] == '.', "Extension is invalid: '%s'" % ext
    import _winreg

    if root is None:
        root = _winreg.HKEY_CLASSES_ROOT
    elif root in (_winreg.HKEY_LOCAL_MACHINE, _winreg.HKEY_CURRENT_USER):
        # use the Software\Classes subkey
        root = _winreg.OpenKey(root, r"Software\Classes")

    try:
        extKey = _winreg.OpenKey(root, ext)
    except WindowsError:
        log.debug("Failed to open '%s'", ext)
        return None

    log.debug("Opened key '%s'", ext)

    # Get the type name from this key.
    try:
        typeName, typeNameType = _safeQueryValueEx(extKey, "")
    except WindowsError:
        return None

    return typeName

def _safeQueryValueEx(key, name):
    """Try to work around some issues with string length and NULL terminators
    in string registry entries.
    
    For example, sometimes (don't know how to reproduce those circumstances
    yet -- see Komodo bug 33333) a QueryValueEx will return a string with a
    number of '\x00' null characters. This method strips those.
    
    XXX See the not about the different behaviour of QueryValueEx on Win9x
        versus WinNT for null values. Perhaps this method could abstract
        that.
    """
    value, valueType = _winreg.QueryValueEx(key, name)
    if valueType in (_winreg.REG_SZ, _winreg.REG_MULTI_SZ, _winreg.REG_EXPAND_SZ):
        value = value.strip('\x00')
    return (value, valueType)

def _deleteKeyIfEmpty(root, keyName, rootDesc="..."):
    """Delete the given registry key, and any ancestor keys up to the root, if
    they are empty (have no subkeys or values).

    @param root {HKEY} The ancestor which should not be deleted
    @param keyName {unicode} The name of the subkey to delete if empty
    @param rootDesc {unicode} A string describing the root (for logging)
    @returns {int} The number of keys deleted
    """
    import _winreg
    count = 0
    log.debug(r"_deleteKeyIfEmpty: deleting %s\%s", rootDesc, keyName)
    while keyName:
        with _winreg.OpenKey(root, keyName) as key:
            try:
                _winreg.EnumValue(key, 0)
            except WindowsError:
                pass
            else:
                log.debug("_deleteKeyIfEmpty: %s has values", keyName)
                return count # not empty
            try:
                _winreg.EnumKey(key, 0)
            except WindowsError:
                pass
            else:
                log.debug("_deleteKeyIfEmpty: %s has subkeys", keyName)
                return count # not empty
        _winreg.DeleteKey(root, keyName)
        count += 1
        log.info(r"deleted '%s\%s' key", rootDesc, keyName)
        keyName = "\\".join(keyName.split("\\")[:-1])
        # try again with the parent
    return count


#---- public module interface

def getHKLMRegistryValue(keyName, valueName):
    """Return a (<value>, <valueType>) tuple for the given registry value.

    An EnvironmentError is raised if the value does not exist.
    (Note: On Win9x the empty string may be returned for non-existant values
    instead of raising an environment error.)
    """
    log.debug("getHKLMRegistryValue(keyName=%r, valueName=%r)", keyName,
              valueName)
    import _winreg
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, keyName)
    return _safeQueryValueEx(key, valueName)


def setHKLMRegistryValue(keyName, valueName, valueType, value):
    """Set the given value in the registry.

    An EnvironmentError is raised if unsuccessful.
    """
    log.debug("setHKLMRegistryValue(keyName=%r, valueName=%r, valueType=%r, "\
              "value=%r)", keyName, valueName, valueType, value)
    import _winreg
    # Open the key for writing.
    try:
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, keyName,
                              0, _winreg.KEY_SET_VALUE)
    except EnvironmentError, ex:
        # Either do not have permissions or we must create the keys
        # leading up to this key. Presume that latter, if the former
        # then it will fall out in the subsequent calls.
        parts = _splitall(keyName)
        for i in range(len(parts)):
            partKeyName = os.path.join(*parts[:i+1])
            partKey = _winreg.CreateKey(_winreg.HKEY_LOCAL_MACHINE,
                                        partKeyName)
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, keyName,
                              0, _winreg.KEY_SET_VALUE)
        
    # Write the given value.
    _winreg.SetValueEx(key, valueName, 0, valueType, value)


def getFileAssociation(ext):
    """Return the register filetype and an order list of associated actions.
    
        "ext" is the extension to lookup. It must include the leading '.'.
    
    Returns the following:
        (<filetype>, <filetype display name>, <ordered list of actions>)
    where the list of actions is intended to be ordered as they would be
    in the Windows Explorer context menu for a file with that extension.

    Each action is a tuple,
        (<action name>, <action display string>, <command line>)

    If the file type is not found, raises WinIntegError
    """
    log.debug("getFileAssociation(ext=%r)", ext)
    import _winreg

    #---- 1. Find the type name from the extension.
    typeName = _getTypeNameFromRegistry(ext)
    if typeName is None:
        raise WinIntegError("unrecognize extension: '%s'" % ext)

    # Get the type display name from the type key (it is the default value).
    displayName = None
    try:
        with _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, typeName) as typeKey:
            displayName = _safeQueryValueEx(typeKey, "")[0]
    except WindowsError, ex:
        pass

    #---- 2. Get the current actions associated with this file type.
    # Get a list of all the current actions. E.g. for this layout:
    #   HKEY_CLASSES_ROOT
    #       Python.File
    #           shell
    #               Edit        -> (value not set)
    #               Edit2       -> "&Edit with Komodo"
    #               open        -> (value not set)
    # the actions are:
    #   [("Edit", "&Edit"), ("Edit2", "&Edit with Komodo"),
    #    ("open", "&Open")]
    # Implicit naming rules:
    # - "open" and "print" get capitalized, others do not seems to (including
    #   "edit").
    # - the first letter is made the accesskey with a '&'-prefix
    actionNames = []
    try:
        shellKey = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT,
                                   "%s\\shell" % typeName)
        for index in itertools.count():
            try:
                actionName = _winreg.EnumKey(shellKey, index)
                try:
                    with _winreg.OpenKey(shellKey, actionName) as actionKey:
                        actionDisplayName = _safeQueryValueEx(actionKey, None)[0]
                except WindowsError, ex:
                    if ex.winerror != 2: # ERROR_FILE_NOT_FOUND
                        raise
                    actionDisplayName = None
                if not actionDisplayName:
                    if actionName.lower() == "open":
                        actionDisplayName = "&Open"
                    else:
                        actionDisplayName = "&"+actionName
                actionNames.append( (actionName, actionDisplayName) )
            except WindowsError:
                break
    except WindowsError:
        pass

    log.debug("action names for '%s': %s", typeName, actionNames)
    actions = []
    for actionName, actionDisplayName in actionNames:
        command = None
        try:
            commandKey = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT,
                                         "%s\\shell\\%s\\command"
                                         % (typeName, actionName))
        except WindowsError, ex:
            pass
        else:
            try:
                command, commandType = _safeQueryValueEx(commandKey, "")
            except WindowsError:
                pass
        actions.append( (actionName, actionDisplayName, command) )

    #---- 3. Sort the actions as does Windows Explorer 
    # This seems to use the following rules:
    # - If there is an "opennew", then that is first and all others are
    #   after in alphabetical order.
    # - Else if there is an "open", then that is first and all others are
    #   after in alphabetical order.
    name2action = {}
    for action in actions:
        name2action[action[0].lower()] = action
    if "opennew" in name2action:
        default = name2action["opennew"]
        del name2action["opennew"]
    elif "open" in name2action:
        default = name2action["open"]
        del name2action["open"]
    else:
        default = None
    actions = [name2action[k] for k in sorted(name2action.keys())]
    if default: actions.insert(0, default)

    return (typeName, displayName, actions)


def checkFileAssociation(ext, action, exe):
    """Check that the given association is setup as expected.

    "ext" is the extention (it must include the leading dot).
    "action" is the association action to check.
    "exe" is the expected associated executable.

    This can raise an WindowsError if unsuccessful.
    """
    log.debug("checkFileAssociation(ext=%r, action=%r, exe=%r)",
              ext, action, exe)
    import _winreg

    #---- Find the type name from the extension.
    try:
        [typeName, typeDisplayName, actions] = getFileAssociation(ext)
    except WinIntegError:
        return "'%s' extension is not registered with system" % ext

    #---- Abort check if there is no matching action.
    for actionName, actionDisplayName, command in actions:
        log.debug("actionDisplayName: %r actionName: %r action: %r",
                  actionDisplayName, actionName, action)
        if (actionDisplayName.lower() == action.lower()
            or actionName.lower() == action.lower()):
            break
    else:
        actionsSummary = ', '.join(a[1] or a[0] for a in actions)
        return "no '%s' action is associated with %s/%s "\
               "(existing actions are: %s)"\
               % (action, ext, typeName, actionsSummary)

    #---- Check that actual command matches expectation.
    if ' ' in exe:
        expectedCommands = ['"%s" "%%1" %%*' % exe]
    else:
        expectedCommands = ['%s "%%1" %%*' % exe,
                            '"%s" "%%1" %%*' % exe] # allow redundant quotes
    for expectedCommand in expectedCommands:
        if expectedCommand == command:
            return None
    else:
        return ("current '%s' command for %s/%s doesn't match "
                "expectation:\n\tcurrent:  %s\n\texpected: %s"
                % (actionDisplayName, ext, typeName, command,
                   expectedCommands[0]))


def addFileAssociation(ext, action, exe, fallbackTypeName=None):
    """Add a file association from the given extension to the given
    executable.

    "ext" is the extention (it must include the leading dot).
    "action" is the association action to make.
    "exe" is the executable to which to associate.
    "fallbackTypeName" is a file type name to use ONLY IF a type name
        does not already exist for the given extension.

    This can raise an EnvironmentError if unsuccessful. (XXX Can this be
    limited to a WindowsError?)
    """
    log.debug("addFileAssociation(ext=%r, action=%r, exe=%r, "\
              "fallbackTypeName=%r)", ext, action, exe, fallbackTypeName)
    import _winreg
    userClasses = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"Software\Classes")

    #---- 1. Find the type name from the extension.
    typeName = _getTypeNameFromRegistry(ext)
    if typeName is None:
        typeName = fallbackTypeName or _getTypeName(ext)
        with _winreg.CreateKey(userClasses, ext) as extKey:
            # re-open the key with write access
            with _winreg.OpenKey(extKey, "", 0, _winreg.KEY_SET_VALUE) as extKey:
                _winreg.SetValueEx(extKey, "", 0, _winreg.REG_SZ, typeName)

    log.info("type name for '%s' is '%s'", ext, typeName)

    #---- 2. Get the current actions associated with this file type.
    # Get a list of all the current actions.
    try:
        currActions = getFileAssociation(ext)[2]
    except WinIntegError:
        currActions = []
    log.info("current actions for '%s': %s", typeName, currActions)

    #---- 3. Determine which subkey of HKCR\\$typeName\\shell to use for
    #        action.
    if ' ' in action: # e.g. "Edit with Komodo"
        # We might want to replace one of the existing actions if the
        # action names are the same.
        for currAction in currActions:
            if action       .replace('&', '').lower() ==\
               currAction[1].replace('&', '').lower():
                actionKeyName = currAction[0]
                break
        else:
            # Pick an action key name that does not conflict.
            currActionKeyNames = set(a[0].lower() for a in currActions)
            for i in [''] + range(2, 100):
                actionKeyName = action.split()[0] + str(i) # Edit1, Edit2, ...
                if actionKeyName.lower() not in currActionKeyNames:
                    break
            else:
                raise WinIntegError("Could not determine a non-conflicting "\
                                    "action key name for file type '%s' and "\
                                    "action '%s'." % (typeName, action))
        actionName = action
    else: # e.g. "Edit"
        actionKeyName = action
        actionName = None
    actionKeyPath = "%s\\shell\\%s" % (typeName, actionKeyName)
    log.info("creating '%s' action at key 'HKCR\\%s'",
             actionName or actionKeyName, actionKeyPath)

    #---- 4. Register the action.
    # First, set the action name if necessary (and ensure the action key
    # is created).
    actionKey = _winreg.CreateKey(userClasses,
                                  r"%s\shell\%s" % (typeName, actionKeyName))
    if actionName is not None:
        log.info("setting name for action key '%s' of file type '%s': '%s'",
                 actionKeyName, typeName, actionName)
        _winreg.SetValueEx(actionKey, "", 0, _winreg.REG_SZ, actionName)
    # Next, determine the command and create/update the "command" subkey.
    if ' ' in exe:
        command = '"%s" "%%1" %%*' % exe
    else:
        command = '%s "%%1" %%*' % exe
    with _winreg.CreateKey(actionKey, "command") as commandKey:
        log.info("setting command for '%s' action of '%s' file type: %r",
                 actionName or actionKeyName, typeName, command)
        _winreg.SetValueEx(commandKey, "", 0, _winreg.REG_EXPAND_SZ, command)


def removeFileAssociation(ext, action, exe, fromHKLM=False):
    """Remove the given file association PROVIDED the current state of
    the association points to the given executable.

    "ext" is the extention (it must include the leading dot).
    "action" is the association action to make.
    "exe" is the executable to which to associate.
    "fromHKLM", if set, causes the association to be removed from HKLM instead
        of HKCU; this may raise a WindowsError if permissions are denied

    This can raise an WindowsError if unsuccessful.

    Returns True if the association was removed; False if it there was no need
    to (not set, or set to a different executable).
    """
    log.debug("removeFileAssociation(ext=%r, action=%r, exe=%r, HKLM=%r)", ext,
              action, exe, fromHKLM)
    import _winreg
    if fromHKLM:
        HKCR = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"Software\Classes")
    else:
        HKCR = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"Software\Classes")

    #---- 1. Find the type name and associations from the extension.
    try:
        [typeName, typeDisplay, currActions] = getFileAssociation(ext)
    except WinIntegError:
        log.warn("extension '%s' is not registered, giving up", ext)
        return False

    log.info("type name for '%s' is '%s' actions: %r", ext, typeName, currActions)

    #---- 2. Determine which subkey of HKCR\\$typeName\\shell is relevant.
    actionKeyName = None
    actionData = None
    for currAction in currActions:
        if currAction[1]:
            if action       .replace('&', '').lower() ==\
               currAction[1].replace('&', '').lower():
                actionKeyName, actionDisplayName, command = currAction
                break
        else:
            if action       .replace('&', '').lower() ==\
               currAction[0].replace('&', '').lower():
                actionKeyName, actionDisplayName, command = currAction
                break
    else:
        log.warn("could not find relevant current action to remove: '%s'",
                 action)
        return False
    log.info("relevant current action: '%s' command: '%s'",
             actionKeyName, command)

    #---- 3. Abort if the current action is NOT to the given exe.
    commandExe = _parseFirstArg(command)
    if os.path.split(exe)[-1].lower() != os.path.split(commandExe)[-1].lower():
        log.warn("current association, %r, is not to the given exe, "\
                 "%r, aborting", commandExe, exe)
        return False

    #---- 4. Remove the action key.
    with _winreg.OpenKey(HKCR, r"%s\shell\%s\command" % (typeName, actionKeyName), 0, _winreg.KEY_SET_VALUE) as commandKey:
        _winreg.DeleteValue(commandKey, "")
    log.info("deleted default value for 'HKCR\\%s\\shell\\%s\\command'",
             typeName, actionKeyName)

    # Clean up an empty registry branch.
    try:
        subkey = r"%s\shell\%s\command" % (typeName, actionKeyName)
        # re-open HKCR with write access
        with _winreg.OpenKey(HKCR, "", 0, _winreg.KEY_SET_VALUE) as root:
            log.debug("re-opened root")
            numDeleted = _deleteKeyIfEmpty(root, subkey, rootDesc="HKCR")
            if numDeleted == 1:
                # perhaps there's a description in <type>\shell\<action>\(Default)
                subkey = r"%s\shell\%s" % (typeName, actionKeyName)
                def tryDeleteDefault():
                    with _winreg.OpenKey(HKCR, subkey, 0, _winreg.KEY_QUERY_VALUE | _winreg.KEY_SET_VALUE) as actionKey:
                        try:
                            _winreg.EnumKey(actionKey, 0)
                            return None # other subkeys exist, don't delete
                        except WindowsError:
                            pass
                        hasDefault = True
                        try:
                            # check if the default value exists (the user-visible description of the file type)
                            _winreg.QueryValueEx(actionKey, "")
                        except WindowsError:
                            # there's no default value
                            hasDefault = False
                        try:
                            _winreg.EnumValue(actionKey, 1 if hasDefault else 0)
                            return None # other values exist
                        except WindowsError:
                            pass
                        if hasDefault:
                            _winreg.DeleteValue(actionKey, "")
                    return _deleteKeyIfEmpty(root, subkey, rootDesc="HKCR")
                moreDeleted = tryDeleteDefault()
                if moreDeleted is not None:
                    numDeleted += moreDeleted
            log.debug("deleted %r keys", numDeleted)
            if numDeleted >= len(subkey.split("\\")):
                # the whole thing was deleted; clean up the extension tree as well
                with _winreg.OpenKey(root, ext, 0, _winreg.KEY_SET_VALUE) as extKey:
                    _winreg.DeleteValue(extKey, None)
                try:
                    _deleteKeyIfEmpty(root, ext, rootDesc="HKCR")
                except WindowsError, ex:
                    if ex.winerror != 2: # ERROR_FILE_NOT_FOUND
                        raise
                    log.debug("removeFileAssociation: Can't find %s", ext)
                    # ignore not found errors, the file extension part may have
                    # come from the HKLM version of HKCR
    except WindowsError, ex:
        if ex.winerror != 5: # ERROR_ACCESS_DENIED
            raise
        log.debug("removeFileAssociation: Access denied (%r)", ex)

    return True

#---- command line interface

class WinIntegShell(_ListCmd):
    """
    wininteg - a tool for integrating an app into Microsoft Window

    Usage:
        wininteg [<options>...] <command> [<args>...]

    Options:
        -h, --help      Print this help and exit.
        -V, --version   Print the version info and exit.
        -v, --verbose   More verbose output.

    Wininteg's usage is intended to feel like p4's command line
    interface.

    Getting Started:
        wininteg help                       print this help
        wininteg help <command>             help on a specific command

    Commands:
        get_assoc EXT                       list assocations for EXT
        add_assoc EXT ACTION APPPATH        add assocation for EXT
        check_assoc EXT ACTION APPPATH      check expected EXT assocation
        remove_assoc EXT ACTION APPPATH     remove specific assoc for EXT
    """
    name = "wininteg"

    def emptyline(self):
        self.do_help(["help"])

    def help_usage(self):
        sys.stdout.write(__doc__)
        sys.stdout.flush()

    def do_get_assoc(self, argv):
        """
    get_assoc -- Get the current file association.

    wininteg get_assoc [<options>...] <ext>

        <ext> is the extention (it must include the leading dot).

        This looks up and prints all associated actions and shell commands
        for the current extension.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "")
        except getopt.GetoptError, ex:
            log.error("get_assoc: %s", ex)
            log.error("get_assoc: try 'wininteg help get_assoc'")
            return 1

        # Process arguments.
        if len(args) != 1:
            log.error("get_assoc: incorrect number of arguments: %s", args)
            log.error("get_assoc: try 'wininteg help get_assoc'")
            return 1
        ext = args[0]

        try:
            type, name, actions = getFileAssociation(ext)
            print "File Type: %s (%s)" % (name, type)
            if actions:
                print "Actions:"
                for aName, aDisplayName, aCommand in actions:
                    print "    %s (%s)" % (aDisplayName, aName)
                    print "        %s" % aCommand
            else:
                print "Actions: <none>"
        except Exception, ex:
            log.error(str(ex))
            if log.isEnabledFor(logging.DEBUG):
                import traceback
                traceback.print_exception(*sys.exc_info())
            return 1


    def do_check_assoc(self, argv):
        """
    check_assoc -- Check that a file association is as expected

    wininteg check_assoc [<options>...] <ext> <action> <exe>

        <ext> is the extention (it must include the leading dot).
        <action> is the association action to check.
        <exe> is the expected associated executable.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "", [])
        except getopt.GetoptError, ex:
            log.error("add_assoc: %s", ex)
            log.error("add_assoc: try 'wininteg help check_assoc'")
            return 1

        # Process arguments.
        if len(args) != 3:
            log.error("check_assoc: incorrect number of arguments: %s", args)
            log.error("check_assoc: try 'wininteg help check_assoc'")
            return 1
        ext, action, exe = args

        try:
            msg = checkFileAssociation(ext, action, exe)
            if msg is not None:
                print msg
        except Exception, ex:
            log.error(str(ex))
            if log.isEnabledFor(logging.DEBUG):
                import traceback
                traceback.print_exception(*sys.exc_info())
            return 1


    def do_add_assoc(self, argv):
        """
    add_assoc -- Add a file association.

    wininteg add_assoc [<options>...] <ext> <action> <exe>

        <ext> is the extention (it must include the leading dot).
        <action> is the association action to make.
        <exe> is the executable to which to associate.

        Options:
            --type-name=<name>, -t <name>
                    Specify a _fallback_ type name for the given extension.

        An association is made for the given extension to the given executable.
        If the extension already has a register type name, then that
        name is used. You may provide a fallback type name to use, if it
        is needed, otherwise one will be created based on the extension.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "t:", ["type-name="])
        except getopt.GetoptError, ex:
            log.error("add_assoc: %s", ex)
            log.error("add_assoc: try 'wininteg help add_assoc'")
            return 1
        fallbackTypeName = None
        for opt, optarg in optlist:
            if opt in ("-t", "--type-name"):
                fallbackTypeName = optarg

        # Process arguments.
        if len(args) != 3:
            log.error("add_assoc: incorrect number of arguments: %s", args)
            log.error("add_assoc: try 'wininteg help add_assoc'")
            return 1
        ext, action, exe = args

        try:
            addFileAssociation(ext, action, exe, fallbackTypeName)
        except Exception, ex:
            log.error(str(ex))
            if log.isEnabledFor(logging.DEBUG):
                import traceback
                traceback.print_exception(*sys.exc_info())
            return 1


    def do_remove_assoc(self, argv):
        """
    remove_assoc -- Remove a file association.

    wininteg remove_assoc <ext> <action> <exe>

        <ext> is the extention (it must include the leading dot).
        <action> is the association action to remove.
        <exe> is the executable to which to associate.

        The given file association is removed, PROVIDED the currently
        registered command is for the given executable. If it is not
        then the association is left alone: we don't want to disrupt a
        file association to another app.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "")
        except getopt.GetoptError, ex:
            log.error("remove_assoc: %s", ex)
            log.error("remove_assoc: try 'wininteg help remove_assoc'")
            return 1

        # Process arguments.
        if len(args) != 3:
            log.error("remove_assoc: incorrect number of arguments: %s", args)
            log.error("remove_assoc: try 'wininteg help remove_assoc'")
            return 1
        ext, action, exe = args

        try:
            removeFileAssociation(ext, action, exe)
        except Exception, ex:
            log.error(str(ex))
            if log.isEnabledFor(logging.DEBUG):
                import traceback
                traceback.print_exception(*sys.exc_info())
            return 1


def _main(argv):
    logging.basicConfig()
    try:
        optlist, args = getopt.getopt(argv[1:], "hVv",
            ["help", "version", "verbose"])
    except getopt.GetoptError, msg:
        log.error("%s. Your invocation was: %s", msg, argv)
        log.error("Try 'wininteg --help'.")
        return 1
    for opt, optarg in optlist:
        if opt in ("-h", "--help"):
            sys.stdout.write(WinIntegShell.__doc__)
            return 0
        elif opt in ("-V", "--version"):
            print "wininteg %s" % '.'.join([str(i) for i in _version_])
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(Logger.DEBUG)

    shell = WinIntegShell()
    return shell.onecmd(args)


if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0])
    sys.exit( _main(sys.argv) )


