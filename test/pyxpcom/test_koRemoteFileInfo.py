# -*- coding: utf-8 -*-

# Copyright (c) 2009-2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

##
# Test the koIRemoteFileInfo class.
#

import time
import unittest

from xpcom import components
from testlib import tag

# Test function
class remoteInfoTests(unittest.TestCase):

    def _makeKoRemoteFileInfo(self):
        rf = components.classes['@activestate.com/koRemoteFileInfo;1'].\
                    createInstance(components.interfaces.koIRemoteFileInfo)
        return rf

    def test_list_parsing(self):
    # Test other listing formats to ensure they get parsed
        lists = [
                'drwxr-xr-x   18 179      666          4096 Oct 10 15:38 Python-2.3.4',
                '-rw-r--r--    1 501      501       8502738 Oct 10 15:31 Python-2.3.4.tgz',
                'srwxrwxr-x    1 500      500             0 Sep 15 22:31 MQSeries.1147',
                '-rw-r--r--  1 nobody  nogroup   179302 Nov 15 15:52 pdf',
                '-rw-r--r--  1 nobody  nogroup      555 Nov  7 14:26 pdf.txt',
                "-rw-r--r--   1 root     other        531 Jan 29 03:26 README",
                "dr-xr-xr-x   2 root     other        512 Apr  8 1994  etc",
                "dr-xr-xr-x   2 root     other        512 Apr  8  1994 lib",
                "lrwxrwxrwx   1 root     other          7 Jan 25 00:17 bin -> usr/bin",
                "----------   1 owner    group         1803128 Jul 10 10:18 ls-lR.Z",
                "d---------   1 owner    group               0 May  9 19:45 Softlib",
                "-rwxrwxrwx   1 noone    nogroup      322 Aug 19  1996 message.ftp",
                # Some windows listings
                "03-07-06  11:39AM            598917120 photos.tar",
                "07-03-06  10:19AM       <DIR>          home",
                "lrwxrwxrwx   1 root  root    26 2006-07-21 22:30 vmlinuz -> boot/vmlinuz-2.6.15-26-386",
                ]
        for l in lists:
            fileinfo = self._makeKoRemoteFileInfo()
            result = fileinfo.initFromDirectoryListing("testingdir", l)
            self.failIf(result != True, "Failed to parse: %r" % (l, ))

    def test_unix_format(self):
        # Unix file listing
        l = '-rw-r--r--    1 501      501       8502738 Dec 31 23:59 Python-2.3.4.tgz'
        fileinfo = self._makeKoRemoteFileInfo()
        gm_now = time.gmtime()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", l) != True,
                    "Could not parse directory listing: %r" % (l, ))
        self.failIf(fileinfo.getFilename() != 'Python-2.3.4.tgz',
                    "Incorrect filename: %r != 'Python-2.3.4.tgz'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.getDirname() != "testingdir",
                    "Incorrect directory name: %r != 'testingdir'" % (fileinfo.getDirname(),))
        self.failIf(fileinfo.getFileSize() != '8502738',
                    "Incorrect file size: %r != '8502738'" % (fileinfo.getFileSize(),))
        self.failIf(fileinfo.isDirectory() != False,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(),))
        self.failIf(fileinfo.isExecutable() != False,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(),))
        self.failIf(fileinfo.isFile() != True,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(),))
        self.failIf(not fileinfo.isReadable(),
                    "Incorrect isReadable: '%r'" % (fileinfo.isReadable(),))
        self.failIf(fileinfo.isSymlink() != False,
                    "Incorrect isSymlink: '%r'" % (fileinfo.isSymlink(),))
        self.failIf(not fileinfo.isWriteable(),
                    "Incorrect isWriteable: '%r'" % (fileinfo.isWriteable(),))
        self.failIf(fileinfo.isHidden() != False,
                    "Incorrect isHidden: '%r'" % (fileinfo.isHidden(),))
        self.failIf((gm_now[1] <= 11 or gm_now[2] <= 29) and \
                     fileinfo.getModifiedTime() > time.time(),
                    "The time was parsed as sometime in the future: %s" % (time.ctime(fileinfo.getModifiedTime()), ))

    def test_windows_format(self):
        # Windows file listing
        l = "07-03-06  10:19AM       <DIR>          home"
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", l) != True,
                    "Could not parse directory listing: %r" % (l, ))
        self.failIf(fileinfo.getFilename() != 'home',
                    "Incorrect filename: %r != 'home'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.getDirname() != "testingdir",
                    "Incorrect directory name: %r != testingdir" % (fileinfo.getDirname(), ))
        self.failIf(fileinfo.isDirectory() != True,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(), ))
        self.failIf(fileinfo.isExecutable() != True,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(), ))
        self.failIf(fileinfo.isFile() != False,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(), ))
        self.failIf(not fileinfo.isReadable(),
                    "Incorrect isReadable: '%r'" % (fileinfo.isReadable(), ))
        self.failIf(fileinfo.isSymlink() != False,
                    "Incorrect isSymlink: '%r'" % (fileinfo.isSymlink(), ))
        self.failIf(not fileinfo.isWriteable(),
                    "Incorrect isWriteable: '%r'" % (fileinfo.isWriteable(), ))
        self.failIf(fileinfo.isHidden() != False,
                    "Incorrect isHidden: '%r'" % (fileinfo.isHidden(), ))

    def test_symlink_handling(self):
        # Symlinks
        l = 'lrwxrwxrwx  1 toddw toddw        8 2006-07-25 11:23 link.txt -> todd.txt'
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("/tmp", l) != True,
                    "Could not parse directory listing: %r" % (l, ))
        self.failIf(fileinfo.getFilename() != 'link.txt',
                    "Incorrect filename: %r != 'link.txt'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.isSymlink() != True,
                    "Incorrect symlink info: '%s'" % (fileinfo.isSymlink(), ))
        self.failIf(fileinfo.getLinkTarget() != '/tmp/todd.txt',
                    "Incorrect symlink target: %r != '/tmp/todd.txt'" % (fileinfo.getLinkTarget(), ))

    def test_rumpus_format(self):
        # Rumpus file listing
        file_listing   = '-rw-r--r--        0           0        0 Sep 24 16:48 myfile.txt'
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", file_listing) != True,
                    "Could not parse directory listing: %r" % (file_listing, ))
        self.failIf(fileinfo.getFilename() != 'myfile.txt',
                    "Incorrect filename: %r != 'myfile.txt'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.getFileSize() != '0',
                    "Incorrect file size: %r != '0'" % (fileinfo.getFileSize(),))
        self.failIf(fileinfo.isDirectory() != False,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(),))
        self.failIf(fileinfo.isExecutable() != False,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(),))
        self.failIf(fileinfo.isFile() != True,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(),))

        folder_listing = 'drwxr-xr-x               folder        0 Sep 24 16:46 foo'
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", folder_listing) != True,
                    "Could not parse directory listing: %r" % (folder_listing, ))
        self.failIf(fileinfo.getFilename() != 'foo',
                    "Incorrect filename: %r != 'foo'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.getFileSize() != '0',
                    "Incorrect file size: %r != '0'" % (fileinfo.getFileSize(),))
        self.failIf(fileinfo.isDirectory() != True,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(),))
        self.failIf(fileinfo.isExecutable() != True,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(),))
        self.failIf(fileinfo.isFile() != False,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(),))

    @tag("bug88866")
    def test_ruski_format(self):
        # Russian file listing
        folder_listing   = u'drwxrwxr-x  2 username username      4096 Дек  5  2009 doxygen'
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", folder_listing) != True,
                    "Could not parse directory listing: %r" % (folder_listing, ))
        self.failIf(fileinfo.getFilename() != 'doxygen',
                    "Incorrect filename: %r != 'doxygen'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.isDirectory() != True,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(),))
        self.failIf(fileinfo.isExecutable() != True,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(),))
        self.failIf(fileinfo.isFile() != False,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(),))

        file_listing   = u'-rw-rw-r--  1 username username       990 Авг 19  2009 failed.gif'
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", file_listing) != True,
                    "Could not parse directory listing: %r" % (file_listing, ))
        self.failIf(fileinfo.getFilename() != 'failed.gif',
                    "Incorrect filename: %r != 'failed.gif'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.getFileSize() != '990',
                    "Incorrect file size: %r != '990'" % (fileinfo.getFileSize(),))
        self.failIf(fileinfo.isDirectory() != False,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(),))
        self.failIf(fileinfo.isExecutable() != False,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(),))
        self.failIf(fileinfo.isFile() != True,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(),))

        file_listing   = '-rw-rw-r--  1 username username      3314 Мар  1  2010 icon16x16.png'
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", file_listing) != True,
                    "Could not parse directory listing: %r" % (file_listing, ))
        self.failIf(fileinfo.getFilename() != 'icon16x16.png',
                    "Incorrect filename: %r != 'icon16x16.png'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.getFileSize() != '3314',
                    "Incorrect file size: %r != '3314'" % (fileinfo.getFileSize(),))
        self.failIf(fileinfo.isDirectory() != False,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(),))
        self.failIf(fileinfo.isExecutable() != False,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(),))
        self.failIf(fileinfo.isFile() != True,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(),))


    @tag("bug88866")
    def test_french_format(self):
        # French file listing
        folder_listing   = u'drwxr-xr-x   3 root root  4096 26 fév 22:00 boot'
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", folder_listing) != True,
                    "Could not parse directory listing: %r" % (folder_listing, ))
        self.failIf(fileinfo.getFilename() != 'boot',
                    "Incorrect filename: %r != 'boot'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.isDirectory() != True,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(),))
        self.failIf(fileinfo.isExecutable() != True,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(),))
        self.failIf(fileinfo.isFile() != False,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(),))

        symlink_listing   = 'lrwxrwxrwx   1 root root    25 17 sep  2009 vmlinuz.old -> boot/vmlinuz-2.6.26-2-686'
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", symlink_listing) != True,
                    "Could not parse symlink listing: %r" % (symlink_listing, ))
        self.failIf(fileinfo.getFilename() != 'vmlinuz.old',
                    "Incorrect filename: %r != 'vmlinuz.old'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.isDirectory() != False,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(),))
        self.failIf(fileinfo.isExecutable() != True,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(),))
        self.failIf(fileinfo.isFile() != False,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(),))

    @tag("bug91990")
    def test_space_in_group_name(self):
        file_listing   = '-rw-------  1 incognito.guy Domain Users 11420 2011-12-29 18:51 .bash_history'
        fileinfo = self._makeKoRemoteFileInfo()
        self.failIf(fileinfo.initFromDirectoryListing("testingdir", file_listing) != True,
                    "Could not parse file listing: %r" % (file_listing, ))
        self.failIf(fileinfo.getFilename() != '.bash_history',
                    "Incorrect filename: %r != '.bash_history'" % (fileinfo.getFilename(), ))
        self.failIf(fileinfo.isDirectory() != False,
                    "Incorrect isDirectory: '%r'" % (fileinfo.isDirectory(),))
        self.failIf(fileinfo.isExecutable() != False,
                    "Incorrect isExecutable: '%r'" % (fileinfo.isExecutable(),))
        self.failIf(fileinfo.isFile() != True,
                    "Incorrect isFile: '%r'" % (fileinfo.isFile(),))

    @tag("bug82484")
    def test_remote_file_large_timestamps(self):
        fileinfo = self._makeKoRemoteFileInfo()
        fileinfo.initFromStats("/foo", "bar.txt", "100", "1", "1", 1, 4294952895L)
