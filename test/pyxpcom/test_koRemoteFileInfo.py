# Copyright (c) 2009-2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

##
# Test the koIRemoteFileInfo class.
#

import time
import unittest

from xpcom import components

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

