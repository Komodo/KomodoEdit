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

################################################################################
#               Testing for remote connections and remote files
################################################################################

import os
import time
import logging
import socket
import select
import unittest
import threading

from xpcom import components, COMException

# Details for the testing host
# Leave password as None and it will try to use an agent
# Leave password as '' and it will prompt for the password
test_hosts = [
  # [ 'protocols',         'hostname',                port,   'username', 'password', 'path',                   'privatekey'],
    [('ftp','ftps','sftp','scp'), 'toddw',            0,      'test',     'testuser', '/home/test',             ''],
    [('sftp','scp'),       'commodore',               0,      'toddw',    None,       '/home/toddw',            ''],
    [('sftp','scp'),       'anole',                   0,      'toddw',    None,       '/Users/toddw',           ''],
    [('sftp','scp'),       'kukri',                   0,      'toddw',    None,       '/export/home/toddw',     ''],
    [('ftp', 'sftp','scp'),'asaixv5152',              0,      'toddw',    None,       '/home/toddw',            ''],
    [('sftp','scp'),       'vsbuild2004',             1022,   'toddw',    '',         '/cygdrive/c/home/toddw', ''],
]
procotcols, hostname, port, username, password, home_dir, privatekey = test_hosts[0]
passive = False

filedata = """
        # Creating an actual Komodo file object to be used by buffer
        #file = components.classes["@activestate.com/koFileEx;1"].\ 
        #             createInstance(components.interfaces.koIFileEx)
        #file.URI = koremoteUri
        #file.open(mode)
        
        # Creating an actual connection for specific protocol, port etc...
        #RFService = components.classes["@activestate.com/koRemoteConnectionService;1"].\
        #            getService(components.interfaces.koIRemoteConnectionService)
        ## Path is optional here, as is password (it will prompt) and port (uses default one)
        #connection = RFService.getConnection(protocol, server, port, username, password, path)
        ## Use a koremote uri
        #connection = RFService.getConnectionUsingUri(koremoteUri)
"""
createdDirs = []
createdFiles = []

# Generic test class, used by ftp, sftp, scp
class TestConnection(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self._hostname = hostname
        self._port = port
        self._username = username
        self._password = password
        self._home_dir = home_dir
        self._privatekey = privatekey

    def setUp(self):
        """Called before every test"""
        self._connection = RFService.getConnection2(self._protocol, self._hostname, self._port, self._username, self._password, '', passive, self._privatekey)
        #self._connection.log.addHandler(logging.StreamHandler())
        #import koFTP
        #self._connection = koFTP.koFTPConnection()
        self._dirPath = home_dir + "/unittest_%s" % (self._protocol)
        self._filePath = self._dirPath + "/unittest_%s.txt" % (self._protocol)

    def test01_connection_attributes(self):
        """test 01: Checking connection attributes"""
        try:
            self.assertEqual(self._protocol, self._connection.protocol)
            self.assertEqual(self._hostname, self._connection.server)
            self.assertEqual(self._username, self._connection.username)
            #self.assertEqual(self._password, self._connection.password)
            # HACK: This is the first test run, so removing any old
            #       test directories. Requires ssh with the agent key
            #       setup correctly (i.e. when "password is None").
            if self._password is None:
                ssh_command = "ssh %s@%s rm -rf %s" % (self._username, self._hostname, self._dirPath)
                print ssh_command
                p = os.popen(ssh_command)
                p.read()
                p.close()
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test05_homeDirectory(self):
        """test 05: Checking home directory"""
        try:
            self.assertEqual(self._home_dir, self._connection.getHomeDirectory(), "Home directory is not correct '%s' != '%s'." % (self._home_dir, self._connection.getHomeDirectory()))
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test10_createDirectory(self):
        """test 10: Creating a remote directory"""
        try:
            self._connection.createDirectory(self._dirPath, 0755)
            global createdDirs
            createdDirs.append(self._dirPath)
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test15_parentPath(self):
        """test 15: Checking parent path (dependants: 10)"""
        try:
            self.assertEqual(self._home_dir, self._connection.getParentPath(self._dirPath), "Parent path is not correct '%s' != '%s'." % (self._home_dir, self._connection.getParentPath(self._dirPath)))
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test18_listDirectory(self):
        """test 18: Checking list of directory (dependants: 10)"""
        try:
            self.assert_(self._connection.list(self._dirPath, 1) is not None, "Directory listing does not work")
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test20_writeFile(self):
        """test 20: Writing a file on remote server (dependants: 10)"""
        try:
            self._connection.writeFile(self._filePath, filedata)
            global createdFiles
            createdFiles.append(self._filePath)
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test22_readFile(self):
        """test 22: Reading the written file (dependants: 10, 20)"""
        try:
            self.assertEqual(filedata, self._connection.readFile(self._filePath), "File created does not match the file that was read")
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test30_rfinfo(self):
        """test 30: Directory and file remote file info (dependants: 10, 20, 22)"""
        try:
            dir_rfinfo = self._connection.list(self._dirPath, 1)# Refresh
            # check the values of the dir_rfinfo
            self.assertEqual(dir_rfinfo.getFilename(), os.path.basename(self._dirPath), "List directory not the same as the created directory.")
            self.assertEqual(dir_rfinfo.getFilepath(), self._dirPath, "List dirpath not the same as the created dirpath.")
            self.assert_(dir_rfinfo.isDirectory(), "Directory is not representing as a directory.")
            self.assertFalse(dir_rfinfo.isFile(), "Directory is incorrectly representing as a file.")
            self.assertFalse(dir_rfinfo.isSymlink(), "Directory is incorrectly representing as a symlink.")
            self.assertFalse(dir_rfinfo.originalIsSymlink, "Directory is incorrectly representing as a symlink ('at origin' revision).")
            self.assertEqual(dir_rfinfo.getFilename(), os.path.basename(self._dirPath), "List dirname not the same as the created dirname.")
            self.assert_(dir_rfinfo.isReadable(), "Directory is not readable.")
            self.assert_(dir_rfinfo.isWriteable(), "Directory is not writeable.")
            # check the child elements of dirinfo
            childEntries = dir_rfinfo.getChildren()
            self.assert_(len(childEntries) == 1, "Directory listing failed, invalid number of directory entries.")
            file_rfinfo = self._connection.list(self._filePath, 1)  # Refresh
            # make sure the directory child is the same as that which comes from the file listing
            self.assertEqual(str(file_rfinfo), str(childEntries[0]), "List filename not the same as the directory listed filename.")
            # check the values of the file_rfinfo
            self.assertEqual(file_rfinfo.getFilename(), os.path.basename(self._filePath), "List filename not the same as the created filename.")
            self.assertEqual(file_rfinfo.getFilepath(), self._filePath, "List filepath not the same as the created filepath.")
            self.assert_(file_rfinfo.isFile(), "File is not representing as a file.")
            self.assertFalse(file_rfinfo.isDirectory(), "File is incorrectly representing as a directory.")
            self.assertFalse(file_rfinfo.isSymlink(), "File is incorrectly representing as a symlink.")
            self.assertFalse(file_rfinfo.originalIsSymlink, "File is incorrectly representing as a symlink. ('at origin' revision")
            self.assertEqual(file_rfinfo.getFilename(), os.path.basename(self._filePath), "List filename not the same as the created filename.")
            self.assert_(file_rfinfo.isReadable(), "File is not readable.")
            self.assert_(file_rfinfo.isWriteable(), "File is not writeable.")
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test35_chmod(self):
        """test 35: chmod operations (dependants: 30)"""
        try:
            dir_rfinfo = self._connection.list(self._dirPath, 0)# No refresh
            orig_dir_mode = dir_rfinfo.mode
            self._connection.chmod(self._dirPath, 0700)
            self.assertEqual(dir_rfinfo.mode, 0700, "Chmod failed on directory")
            dir_rfinfo = self._connection.list(self._dirPath, 1) # Refresh
            self.assertEqual(dir_rfinfo.mode, 0700, "Chmod failed on directory, the refresh produced a different result")
            self._connection.chmod(self._dirPath, orig_dir_mode)

            file_rfinfo = self._connection.list(self._filePath, 0)  # No refresh
            orig_file_mode = file_rfinfo.mode
            self._connection.chmod(self._filePath, 0600)
            self.assertEqual(file_rfinfo.mode, 0600, "Chmod failed on file")
            dir_rfinfo = self._connection.list(self._dirPath, 1) # Refresh
            self.assertEqual(file_rfinfo.mode, 0600, "Chmod failed on file, the refresh produced a different result")
            self._connection.chmod(self._dirPath, orig_file_mode)

        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test40_specialCharactersInDirectoryName(self):
        """test 40: Test special characters in directory name (dependants: 10)"""
        global createdDirs
        # Directories
        try:
            for dirnameToTest in ("spaces in dirname", '"double_quoted"', "'single_quoted'", "quote'in_me"):
                newDirPath = "%s/%s" % (self._dirPath, dirnameToTest)
                self._connection.createDirectory(newDirPath, 0755)
                createdDirs.append(newDirPath)
                dir_rfinfo = self._connection.list(newDirPath, 1)
                self.assert_(dir_rfinfo is not None, "Cannot get listing of directory: '%s'" % (dirnameToTest))
                self.assertEqual(dir_rfinfo.getFilename(), dirnameToTest)
            # File name with spaces in it
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test45_specialCharactersInFileName(self):
        """test 45: Test special characters in file name(dependants: 10)"""
        global createdFiles
        # Directories
        try:
            for filenameToTest in ("spaces in dirname.txt", '"double_quoted.abc"', "'single_quoted.tmp'", "quote'in_me.kom"):
                newFilePath = "%s/%s" % (self._dirPath, filenameToTest)
                self._connection.writeFile(newFilePath, filedata)
                createdFiles.append(newFilePath)
                #time.sleep(1)
                file_rfinfo = self._connection.list(newFilePath, 1)
                self.assert_(file_rfinfo is not None, "Cannot get listing of filename: '%s'" % (filenameToTest))
                self.assertEqual(file_rfinfo.getFilename(), filenameToTest)
                self.assertEqual(filedata, self._connection.readFile(newFilePath), "File created does not match the file that was read")
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test50_renameDirectory(self):
        """test 50: Renaming directory (dependants: 10)"""
        newdirPath = self._dirPath + ".tmp"
        try:
            self._connection.rename(self._dirPath, newdirPath)
            # No refresh, should not be cached, as rename removes an item from the cache
            dir_rfinfo = self._connection.list(self._dirPath, 0)
            self.assert_(dir_rfinfo is None, "Rename is not removing the old directory name from the cache.")
            # No refresh, should not be cached, as rename removes an item from the cache
            dir_rfinfo = self._connection.list(newdirPath, 0)
            self.assert_(dir_rfinfo is not None, "Cannot get listing of renamed directory")
            self.assert_(dir_rfinfo.needsDirectoryListing(), "A non-refreshed list of renamed directory should still need it's contents to be listed")
            # Refresh, this should get the directory contents
            dir_rfinfo = self._connection.list(newdirPath, 1)
            self.assert_(dir_rfinfo is not None, "Cannot get listing of renamed directory")
            self.assertFalse(dir_rfinfo.needsDirectoryListing(), "A refreshed list of renamed directory should not need it's contents to be listed")
            # Finally rename the directory back to it's original name
            self._connection.rename(newdirPath, self._dirPath)
            dir_rfinfo = self._connection.list(self._dirPath, 0)
            self.assert_(dir_rfinfo is not None, "Cannot get listing of renamed original directory")
            self.assert_(dir_rfinfo.getFilepath() == self._dirPath, "Directory incorrect after renamed back to original")
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    def test51_renameFile(self):
        """test 51: Renaming file (dependants: 10, 20)"""
        try:
            newfilePath = self._filePath + ".tmp"
            self._connection.rename(self._filePath, newfilePath)
            # No refresh, should not be cached, as rename removes an item from the cache
            file_rfinfo = self._connection.list(self._filePath, 0)
            self.assert_(file_rfinfo is None, "Rename is not removing the old file name from the cache.")
            file_rfinfo = self._connection.list(newfilePath, 0)
            self.assert_(file_rfinfo is not None, "Cannot get listing of renamed file")
            # Finally rename the file back to it's original name
            self._connection.rename(newfilePath, self._filePath)
            file_rfinfo = self._connection.list(self._filePath, 0)
            self.assert_(file_rfinfo is not None, "Cannot get listing of renamed original file")
            self.assert_(file_rfinfo.getFilepath() == self._filePath, "Filename incorrect after renamed back to original")
        except COMException, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))

    # Cleanup tests
    def test90_removeFile(self):
        """test 90: Removing files (dependants: 10, 20)"""
        global createdFiles
        createdFiles.reverse()   # Work back from newest created
        try:
            try:
                for filePath in createdFiles:
                    self._connection.removeFile(filePath)
                    file_rfinfo = self._connection.list(filePath, 0)
                    self.assert_(file_rfinfo is None, "File still exists or is still cached")
            except COMException, ex:
                lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                               .getService(components.interfaces.koILastErrorService)
                self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))
        finally:
            createdFiles = []

    def test91_removeDirectory(self):
        """test 91: Removing directories (dependants: 10)"""
        global createdDirs
        createdDirs.reverse()   # Work back from newest created
        try:
            try:
                for dirPath in createdDirs:
                    self._connection.removeDirectory(dirPath)
                    dir_rfinfo = self._connection.list(dirPath, 0)
                    self.assert_(dir_rfinfo is None, "Directory still exists or is still cached")
            except COMException, ex:
                lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                               .getService(components.interfaces.koILastErrorService)
                self.fail("COMException raised: %s" % (lastErrorSvc.getLastErrorMessage()))
        finally:
            createdDirs = []

RFService = components.classes["@activestate.com/koRemoteConnectionService;1"].\
            getService(components.interfaces.koIRemoteConnectionService)


class BadServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = "localhost"
        self.s.bind((self.host, 0))
        self.port = self.s.getsockname()[1]
        self.s.listen(1)
        self.s.setblocking(0)
        self.isRunning = False

    def run(self):
        self.isRunning = True
        l = [self.s]
        while self.isRunning:
            r, w, x = select.select(l, l, l, 0.5)
            if r or w:
                try:
                    c,a = self.s.accept()
                except:
                    break
            elif x:
                # Some type of exception
                break
        self.s.close()

    def stop(self):
        self.isRunning = False

class TestMiscellaneous(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)

    def test_incorrect_port(self):
        badserver = BadServer()
        badserver.start()
        expected_error_message = "not a recognized SSH server."
        try:
            try:
                protocol = "sftp"
                host = badserver.host
                port = badserver.port
                username = "test"
                password = "test"
                c = RFService.getConnection(protocol, host, port,
                                            username, password, '', '')
            except COMException, ex:
                lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                               .getService(components.interfaces.koILastErrorService)
                last_error = lastErrorSvc.getLastErrorMessage()
                self.assertTrue(last_error.find(expected_error_message) >= 0)
            else:
                self.fail("No exception was raised!")
        finally:
            badserver.stop()


class TestFTPConnection(TestConnection):
    def setUp(self):
        self._protocol = 'ftp'
        TestConnection.setUp(self)

class TestFTPSConnection(TestConnection):
    def setUp(self):
        self._protocol = 'ftps'
        TestConnection.setUp(self)

class TestSFTPConnection(TestConnection):
    def setUp(self):
        self._protocol = 'sftp'
        TestConnection.setUp(self)

class TestSCPConnection(TestConnection):
    def setUp(self):
        self._protocol = 'scp'
        TestConnection.setUp(self)

#---- mainline

def _suite():
    suites = []
    if 'ftp' in procotcols: suites.append( unittest.makeSuite(TestFTPConnection) )
    if 'ftps' in procotcols: suites.append( unittest.makeSuite(TestFTPSConnection) )
    if 'sftp' in procotcols: suites.append( unittest.makeSuite(TestSFTPConnection) )
    if 'scp' in procotcols: suites.append( unittest.makeSuite(TestSCPConnection) )
    return unittest.TestSuite(suites)

# Test function
def _test():
    global procotcols, hostname, port, username, password, home_dir

    #suite = []
    runner = unittest.TextTestRunner(verbosity=2)
    # Run specific host tests
    for test_host in test_hosts:
    #for test_host in test_hosts[2:3]:
        procotcols, hostname, port, username, password, home_dir = test_host
        print "*** Testing procotcols %s on server %s@%s" % (procotcols, username, hostname)
        runner.run(_suite())

    # Run miscellaneous tests
    runner.run(unittest.makeSuite(TestMiscellaneous))

def setupDummyLogger():
    log = logging.getLogger("")
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(name)s: %(message)s')
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    log.addHandler(console)
    log.setLevel(logging.DEBUG)

# When run from command line
if __name__ == '__main__':
    setupDummyLogger()
    for test_host in test_hosts:
        protocols, hostname, port, username, password, home_dir = test_host
        if not password and ('ftp' in protocols or password is not None):
            import getpass
            password = getpass.getpass("Password for %s@%s: " % (username, hostname))
            test_host[4] = password
    _test()

# disable running tests when using the app-wide test harness
def test_cases():
    return []
