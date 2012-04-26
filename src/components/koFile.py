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

# An implementation of a file object for Mozilla/xpcom.
#
# Contributors:
# * Mark Hammond
# * Ken Simpson
# * Paul Prescod.

# XXX - ToDo - we should turn the internal Python exception
# to xpcom exceptions.  However, having Python print a traceback
# is currently pretty useful, as xpcom doesnt support rich errors.
# (note we could probably find reasonable xpcom error codes,
# but the text message from the error is very useful.)

import os
import tempfile
import logging
from xpcom import file, components, COMException, ServerException, server

# needed for ftpfile
import urlparse, urllib, re
import ftplib, StringIO, string
import time, strptime


log = logging.getLogger("koFile")


def apply_raising_com(fn, args):
        try:
                return apply(fn, args)
        except COMException, why:
                log.debug("koFile has XPCOM exception %s: re-raising", why)
                raise ServerException(why.errno)

# A synchronous "file object" used to open a URI.
class URIFile(file.URIFile):
        _com_interfaces_ = [components.interfaces.koIURIFile]
        _reg_desc_ = "Komodo URI File"
        _reg_contractid_ = "@activestate.com/koURIFile;1"
        _reg_clsid_ = "{332BE465-8120-43a8-8C32-02FD9F24F7B0}"
        def initURI(self, uri, mode):
            # Our Python implementation accepts either type.
            return self.init(uri, mode)

        def init(*args):
                import warnings
                warnings.warn("'koURIFile' is deprecated, use koIFileEx instead.",
                              DeprecationWarning)
                return apply_raising_com(file.URIFile.init, args)

        def get_file(self): # readonly "file" property
                return self.fileIO.file
        # Funnily enough, we inherit the rest of the methods we need, 
        # all with the correct signatures :-)

        def puts(self, string):
                self.write(string)

class LocalFile(file.LocalFile):
        _com_interfaces_ = [components.interfaces.koILocalFile]
        _reg_desc_ = "Komodo Local File"
        _reg_contractid_ = "@activestate.com/koLocalFile;1"
        _reg_clsid_ = "{9C1A72FB-002F-43de-9E45-BD8C23C07076}"

        def init(*args):
                import warnings
                warnings.warn("'koILocalFile' is deprecated, use koIFileEx instead.",
                              DeprecationWarning)
                return apply_raising_com(file.LocalFile.init, args)

        def get_file(self): # readonly "file" property
                return self.fileIO.file
        # Funnily enough, we inherit all the methods we need, 
        # all with the correct signatures :-)
        
        def puts(self, string):
                self.write(string)

       
# Temp File support

tempFileNameMap = {}
def RememberTempFile(fname):
        tempFileNameMap[fname] = 1

def DeleteTempFile(fname, remove_fname = 1):
        if os.path.isfile(fname):
                #log.debug("TempFile: Removing '%s'", fname)
                error_message = "no error available"
                try:
                        os.unlink(fname)
                except OSError, error_message:
                        pass
                if os.path.exists(fname):
                        msg = "TempFile: File still exists after deleting '%s' - '%s'" % (fname,error_message)
                        if remove_fname:
                                msg += " - flagging for cleanup at shutdown"
                        log.warn(msg)
                        remove_fname = 0
        if remove_fname:
                try:
                        del tempFileNameMap[fname]
                except KeyError:
                        log.debug("TempFile: '%s' is not in the map of temp filenames", fname)

def DeleteAllTempFiles():
        for fname in tempFileNameMap.keys():
                DeleteTempFile(fname, 0)

# A temp file.  Is deleted when the last reference is removed
# NOT when the file is closed.
class TempFile(LocalFile):
        _com_interfaces_ = [components.interfaces.koILocalFile]
        _reg_desc_ = None
        _reg_contractid_ = None
        _reg_clsid_ = None
        def __del__(self):
                fname = None
                if self.fileIO is not None and self.fileIO.file is not None:
                        fname = self.fileIO.file.path
                LocalFile.__del__(self)
                self.fileIO = None
                if fname is not None:
                        DeleteTempFile(fname)

class TempFileFactory:
        _com_interfaces_ = [components.interfaces.koITempFileFactory]
        _reg_desc_ = "Komodo TempFile factory"
        _reg_contractid_ = "@activestate.com/koTempFileFactory;1"
        _reg_clsid_ = "{e69ac472-29d7-4799-93e3-5d635d0691aa}"
        def __init__(self):
                import warnings
                warnings.warn("'koITempFileFactory' is deprecated, use koIFileService instead.",
                              DeprecationWarning)
                # Add a shutdown observer, so when xpcom shuts down we can destroy any remaining files.
                svc = components.classes["@mozilla.org/observer-service;1"].getService(components.interfaces.nsIObserverService)

                # Observers will be QI'd for a weak-reference, so we must keep the
                # observer alive ourself, and must keep the COM object alive,
                # _not_ just the Python instance!!!
                self._shutdownObserver = server.WrapObject(_TempFileShutdownObserver(), components.interfaces.nsIObserver)
                svc.addObserver(self._shutdownObserver, "xpcom-shutdown", 0)

        def observe(self, service, topic, extra):
                DeleteAllTempFiles()
                svc = components.classes["@mozilla.org/observer-service;1"].getService(components.interfaces.nsIObserverService)
                svc.removeObserver(self._shutdownObserver, "xpcom-shutdown")

        def MakeTempName(self, suffix):
                ret = tempfile.mktemp(suffix)
                RememberTempFile(ret)
                return ret

        def MakeTempFile(self, suffix, mode):
                fname = self.MakeTempName(suffix)
                RememberTempFile(fname)
                return TempFile(fname, mode)

        def MakeTempFileInDir(self, dir, suffix, mode):
                oldtmp = tempfile.tempdir
                tempfile.tempdir = dir
                fname = self.MakeTempName(suffix)
                tempfile.tempdir = oldtmp
                RememberTempFile(fname)
                return TempFile(fname, mode)

# A helper to cleanup our namespace as xpcom shuts down.
class _TempFileShutdownObserver:
        _com_interfaces_ = components.interfaces.nsIObserver
        def observe(self, service, topic, extra):
                DeleteAllTempFiles()

##########################################################
##
## Test Code
##
## Who says we can't have test code in a component?  Not me!
##
##########################################################
def _DoTestRead(file, expected):
    # read in a couple of chunks, just to test that.
    got = file.read(3)
    got = got + file.read(300)
    got = got + file.read(0)
    got = got + file.read(-1)
    if got != expected:
        raise RuntimeError, "Reading '%s' failed - got %d bytes, but expected %d bytes" % (file, len(got), len(expected))

def _TestLocalFile():
    fname = tempfile.mktemp()
    data = "Hello from Python"
    f = open(fname,"w")
    try:
        f.write(data)
        f.close()
        test_file = components.classes[LocalFile._reg_contractid_].createInstance(LocalFile._com_interfaces_[0])
        test_file.init(fname, "r")
        got = test_file.read(-1)
        if got != data:
            print "Read the wrong data back - %r" % (got,)
        else:
            print "Read the correct data."
        test_file.close()
        # Try reading in chunks.
        test_file = components.classes[LocalFile._reg_contractid_].createInstance(LocalFile._com_interfaces_[0])
        test_file.init(fname, "r")
        got = test_file.read(10) + test_file.read(-1)
        if got != data:
            print "Chunks the wrong data back - %r" % (got,)
        else:
            print "Chunks read the correct data."
        test_file.close()
    finally:
        try:
            os.unlink(fname)
        except OSError, details:
            print "Error removing temp test file:", details

filename_to_check_after_shutdown = None

def _TestTempFile():
        factory = components.classes[TempFileFactory._reg_contractid_].getService(TempFileFactory._com_interfaces_[0])
        test_file = factory.MakeTempFile("pyxpcomtest", "w")
        test_file_name = test_file.file.path
        print "Test file name is ", test_file_name
        test_data = "Hello\nfrom\r\npython"
        test_file.write(test_data)
        if not os.path.isfile(test_file_name):
                raise RuntimeError, "Our temp file appears to not exist"
        test_file.flush()
        got = open(test_file_name,"rb").read()
        if got != test_data:
                raise RuntimeError, "Our test data wasnt there: %r" % (got,)
        test_file.close()
        if not os.path.isfile(test_file_name):
                raise RuntimeError, "Our temp file appears to not exist after a close"
        test_file = None
        if os.path.isfile(test_file_name):
                raise RuntimeError, "Our temp file appears to still exist after removing its last reference"

        test_file = factory.MakeTempFile("pyxpcomtest", "w")
        test_file_name = test_file.file.path
        test_file.write(test_data)
        test_file.flush()
        hold_file = open(test_file_name,"rb")
        test_file = None
        if not os.path.isfile(test_file_name):
                raise RuntimeError, "Our temp file that we didn't want deleted, was!"
        global filename_to_check_after_shutdown
        filename_to_check_after_shutdown = test_file_name
        hold_file.close()

        print "Temp file tests worked"

def _TestAll():
    # A mini test suite.
    # Get a test file, and convert it to a file:// URI.
    # check what we read is the same as when
    # we read this file "normally"
    fname = components.__file__
    if fname[-1] in "cCoO": # fix .pyc/.pyo
            fname = fname[:-1]
    expected = open(fname, "rb").read()
    # convert the fname to a URI.
    url = file.localPathToURI(fname)
    # First try passing a URL as a string.
    test_file = components.classes[URIFile._reg_contractid_].createInstance(URIFile._com_interfaces_[0])
    test_file.init( url.spec, "r")
    _DoTestRead( test_file, expected)
    print "Open as string test worked."
    # Now with a URL object.
    test_file = components.classes[URIFile._reg_contractid_].createInstance(URIFile._com_interfaces_[0])
    test_file.initURI( url, "r")
    _DoTestRead( test_file, expected)
    print "Open as URL test worked."

    # For the sake of testing, do our pointless, demo object!
    
    test_file = components.classes[LocalFile._reg_contractid_].createInstance(LocalFile._com_interfaces_[0])
    test_file.init(fname, "r")
    _DoTestRead( test_file, expected )
    print "Local file read test worked."

    # Now do the full test of our pointless, demo object!
    _TestLocalFile()
    # And our temp file
    _TestTempFile()

def _TestURI(url):
    test_file = URIFile(url)
    print "Opened file is", test_file
    got = test_file.read(-1)
    print "Read %d bytes of data from %r" % (len(got), url)
    test_file.close()

if __name__=='__main__':
    print "Performing self-test"
    _TestAll()
    
    if filename_to_check_after_shutdown is not None:
        assert os.path.exists(filename_to_check_after_shutdown)

    from xpcom import _xpcom
    _xpcom.NS_ShutdownXPCOM()

    if filename_to_check_after_shutdown is not None:
        if os.path.exists(filename_to_check_after_shutdown):
            raise RuntimeError, "The delete-temp-files-on-shutdown trick did not delete the temp file!"

    if _xpcom._GetInterfaceCount() or _xpcom._GetGatewayCount():
            print "Warning - exiting with", _xpcom._GetInterfaceCount(), "interfaces and", _xpcom._GetGatewayCount(), "gateways!!"
