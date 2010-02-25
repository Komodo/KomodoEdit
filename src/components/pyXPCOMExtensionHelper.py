# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is the Python XPCOM extension.
#
# The Initial Developer of the Original Code is: Todd Whiteman.
# Portions created by the Initial Developer are Copyright (C) 2007
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Todd Whiteman <twhitema@gmail.com> (original author)  
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

#
# A component to help register all of the installed PyXPCOM extensions.
#

import sys

from xpcom import components, verbose, COMException

def register_self(klass, compMgr, location, registryLocation, componentType):
    # Hack used to register other extensions that rely on PyXPCOM.
    try:
        pyXPCOMExtensionHelper.initializePythonExtensions()
    except COMException:
        if verbose:
            print "Could not initalize the Python XPCOM extensions"
    from xpcom import _xpcom
    svc = _xpcom.GetServiceManager().getServiceByContractID("@mozilla.org/categorymanager;1", components.interfaces.nsICategoryManager)
    svc.addCategoryEntry("xpcom-startup",
                         pyXPCOMExtensionHelper._reg_component_type_,
                         pyXPCOMExtensionHelper._reg_contractid_,
                         1, 1)

class pyXPCOMExtensionHelper:

    _com_interfaces_ = [components.interfaces.nsIObserver,
                        components.interfaces.pyIXPCOMExtensionHelper]
    _reg_clsid_ = "{b51b28d4-ddcf-4cff-988e-32ab843dc0ed}"
    _reg_contractid_ = "@python.org/pyXPCOMExtensionHelper;1"
    _reg_desc_ = "PyXPCOM extensions initialzer helper"
    # Custom registration
    _reg_registrar_ = (register_self,None)
    _reg_component_type_ = "script/python"

    initialized_component_dirs = set()

    def getExtenionDirectories(cls):
        directorySvc =  components.classes["@mozilla.org/file/directory_service;1"].\
                            getService(components.interfaces.nsIProperties)
        enum = directorySvc.get("XREExtDL", components.interfaces.nsISimpleEnumerator)
        extensionDirs = []
        while enum.hasMoreElements():
            nsifile = enum.getNext().QueryInterface(components.interfaces.nsIFile)
            extensionDirs.append(nsifile)
        return extensionDirs
    getExtenionDirectories = classmethod(getExtenionDirectories)

    def getComponentDirectories(cls):
        componentDirs = []
        directorySvc =  components.classes["@mozilla.org/file/directory_service;1"].\
                            getService(components.interfaces.nsIProperties)
        # ComsD is the application components directory.
        componentDirs.append(directorySvc.get("ComsD", components.interfaces.nsIFile))
        # GRE component directory, often the same as ComsD.
        componentDirs.append(directorySvc.get("GreComsD", components.interfaces.nsIFile))
        # Additional components directories.
        enum = directorySvc.get("ComsDL", components.interfaces.nsISimpleEnumerator)
        while enum.hasMoreElements():
            nsifile = enum.getNext().QueryInterface(components.interfaces.nsIFile)
            componentDirs.append(nsifile)
        return componentDirs
    getComponentDirectories = classmethod(getComponentDirectories)

    ##
    # Listen for xpcom-startup and add the Python "pylib" directories for
    # all of the installed extensions.
    #
    def observe(self, subject, topic, data):
        if topic == "xpcom-startup":
            cls = self.__class__
            cls.addPylibPaths()

    ##
    # Initialize all python components in the extension.
    #
    def addPylibPaths(cls):
        """Add 'pylib' directies for the application and each extension to
        Python's sys.path."""

        from os.path import join, exists, dirname

        # Application directory.
        directorySvc =  components.classes["@mozilla.org/file/directory_service;1"].\
                            getService(components.interfaces.nsIProperties)
        comsD = directorySvc.get("ComsD", components.interfaces.nsIFile)
        if comsD:
            pylibPath = join(dirname(comsD.path), "pylib")
            if exists(pylibPath) and pylibPath not in sys.path:
                if verbose:
                    print "pyXPCOMExtensionHelper:: Adding pylib to sys.path:" \
                          " %r" % (pylibPath, )
                sys.path.append(pylibPath)

        # Extension directories.
        for extDir in cls.getExtenionDirectories():
            pylibPath = join(extDir.path, "pylib")
            if exists(pylibPath) and pylibPath not in sys.path:
                if verbose:
                    print "pyXPCOMExtensionHelper:: Adding pylib to sys.path:" \
                          " %r" % (pylibPath, )
                sys.path.append(pylibPath)
    addPylibPaths = classmethod(addPylibPaths)

    ##
    # Initialize all python components in the extension.
    #
    def initializeComponents(cls):
        """Register all python components in the extension."""

        try:
            pyloader = components.classes["moz.pyloader.1"].\
                            getService(components.interfaces.nsIComponentLoader)
        except COMException:
            # In Mozilla 1.9, this component was renamed.
            pyloader = components.classes["@mozilla.org/module-loader/python;1"].\
                            getService(components.interfaces.nsIComponentLoader)

        when = 0    # At startup.
        for compDir in cls.getComponentDirectories():
            # Check if we've already registered the extension.
            filepath = compDir.path
            if filepath in cls.initialized_component_dirs:
                continue
            cls.initialized_component_dirs.add(filepath)

            if compDir.exists():
                try:
                    if verbose:
                        print "pyXPCOMExtensionHelper:: Init components %r" % (
                                compDir.path, )
                    pyloader.autoRegisterComponents(when, compDir)
                except:
                    try:
                        print "pyXPCOMExtensionHelper:: Error initializing " \
                              "components in %r" % (compDir.path, )
                    except IOError:
                        pass    # Stdout not available
    initializeComponents = classmethod(initializeComponents)

    def initializePythonExtensions(cls):
        """Initialize other PyXPCOM extensions"""

        cls.addPylibPaths()
        cls.initializeComponents()
    initializePythonExtensions = classmethod(initializePythonExtensions)
