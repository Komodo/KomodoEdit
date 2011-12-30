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

# A holder of remote file information, I.e. for ftp, sftp etc...
#
# Contributors:
# * Todd Whiteman

import os
import time
import stat
import re
import logging
from string import digits as string_digits
from string import ascii_lowercase

try:
    from xpcom import components
except ImportError:
    print "WARNING: koRemoteFileInfo: Could not import xpcom components!"
    # Setup a dummy class that gives us the xpcom like structure
    # This should only be used for command line tests.
    class components:
        class interfaces:
            koIRemoteFileInfo = ""

import strptime


# Regex parsers for processing directory listings
re_parse_unix_ftp_line     = re.compile(r'^.([+rwxXstugo-]*)\s+(.*?\s+.*?\s+.*?)\s*(\d*?)\s+(\w+)\s+(\d+)\s+([\d:]+)\s(.*)$')
re_parse_unix_ftp_line_alt = re.compile(r'^.([+rwxXstugo-]*)\s+(.*?\s+.*?\s+.*?)\s+(\d*?)(\s+)([\d-]+)\s+([\d:]+)\s(.*)$')
re_parse_dos_ftp_line      = re.compile(r'^(..-..-..\s+..:....)\s+(.*?)\s+(.*)$')

log = logging.getLogger('koRemoteFileInfo')
#log.setLevel(logging.DEBUG)

# koRemoteFileInfo will store information about a remote file/directory.
# This includes permissions, file type, size and path.
class koRemoteFileInfo:
    """Remote file information"""
    _com_interfaces_ = [components.interfaces.koIRemoteFileInfo]
    _reg_desc_ = "Komodo Remote File Info"
    _reg_contractid_ = "@activestate.com/koRemoteFileInfo;1"
    _reg_clsid_ = "{de59c592-44b5-44c6-aa15-b9c6059416be}"
    # d - if the entry is a directory
    # b - if the entry is a block type special file
    # c - if the entry is a character type special file
    # l - if the entry is a symbolic link
    # s - if the entry is a socket
    # - - if the entry is a plain file 
    _possible_first_chars_for_unix_listing = ("-", "d", "l", "s", "b", "c")
    _3char_month_names = ["jan","feb","mar","apr","may","jun",
                          "jul","aug","sep","oct","nov","dec"]
    # Encoding is used when encoding is not UTF8 compatible
    encoding = ''
    link_target = None

    def __init__(self):
        # Not all these may be set, depending upon the remote OS and it's
        # server implementation. They will be given defaults in these cases.
        self.log = log
        self.path     = ''      # Full path to the file
        self.filename = ''      # Just the name of the file without directory
        self.dirname  = ''      # The directory the file is help within
        self.st_size  = '0'
        self.st_uid   = ''
        self.st_gid   = ''
        self.st_mode  = 0L
        self.st_mtime = 0L
        self.children = []
        self.lastListedTime = 0
        self.originalIsSymlink = False
            # symlink mode bit gets cleared by _followSymlink

    # Boolean checker methods
    def isFile(self):
        return stat.S_ISREG(self.st_mode)
    def isDirectory(self):
        return stat.S_ISDIR(self.st_mode)
    def isSymlink(self):
        return stat.S_ISLNK(self.st_mode)

    # For read and write permissions we do not know which group the user belongs
    # to, so we combine all of the u/g/o permissions and if one of these are
    # read/writeable, then we assume the user has read/write permissions.
    # http://bugs.activestate.com/show_bug.cgi?id=76018
    ANY_READABLE  = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
    ANY_WRITEABLE = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    def isReadable(self):
        return (self.st_mode & self.ANY_READABLE)
    def isWriteable(self):
        return (self.st_mode & self.ANY_WRITEABLE)

    def isExecutable(self):
        return (self.st_mode & stat.S_IEXEC) == stat.S_IEXEC
    def isHidden(self): # Hmmm...
        # XXX - Whats hidden for, how is it used??
        return 0
    def needsDirectoryListing(self):
        # Must be a directory that has not had it's children set
        return (self.isDirectory() and not self.lastListedTime)

    # Getter methods
    def getFilepath(self):
        return self.path
    def getEncoding(self):
        return self.encoding
    def getFilename(self):
        return self.filename
    def getDirname(self):
        return self.dirname
    def getLinkTarget(self):
        return self.link_target
    def getFileSize(self):
        return self.st_size
    def getModifiedTime(self):
        return self.st_mtime
    def getChildren(self):
        return self.children
    def getTimeRefreshed(self):
        return self.lastListedTime

    # Setter methods
    def setChildren(self, children):
        self.children = children
        self.lastListedTime = time.time()
    def setLinkTarget(self, link_target):
        self.link_target = link_target
    def setMode(self, mode):
        self.st_mode = mode

    def _join_path(self, dirname, filename):
            if dirname and dirname[-1] == '/':
                return dirname + filename
            else:
                return dirname + '/' + filename

    # Internal for class usage
    def _setpathinfo(self, dirname, filename, link_target=None):
        # The basename of "/" is the empty string "" - which is not wanted.
        if filename != "/":
            filename = os.path.basename(filename)
        if filename not in ('', '/', '~', '~/', '.', './'):
            self.path = self._join_path(dirname, filename)
            self.dirname = dirname
        else:
            self.dirname = filename
            self.path = filename
        self.filename = filename
        if link_target:
            if link_target[0] in ('/', '~'):
                # Absolute path
                self.link_target = link_target
            else:
                # Relative path
                self.link_target = self._join_path(self.dirname, link_target)

    # Initializers
    # Init from file attributes, same as used by the stat and os modules
    def initFromStats(self, dirname, filename, size, uid, gid, mode, mtime):
        self._setpathinfo(dirname, filename)
        self.st_size  = size
        self.st_uid   = uid
        self.st_gid   = gid
        self.st_mode  = mode
        self.st_mtime = mtime
        #if self.log.level >= logging.DEBUG:
        #    self.log.debug("initFromStats: %s", str(self))
        self.log.debug("initFromStats: %s", self)

    # Init from raw ftp directory listing
    def initFromDirectoryListing(self, dirname, line):
        mode = 0
        isSymlink = False
        self.dirname = dirname
        link_target = None

        if not line:
            log.debug("initFromDirectoryListing: No line to process!")
            return False

        # Check the first character of the listing is a unix style
        if line[0] in self._possible_first_chars_for_unix_listing:

            # UNIX-style listing, without inum and without blocks */
            #   "-rw-r--r--   1 root     other        531 Jan 29 03:26 README" */
            #   "dr-xr-xr-x   2 root     other        512 Apr  8  1994 etc" */
            #   "dr-xr-xr-x   2 root     512 Apr  8  1994 etc" */
            #   "lrwxrwxrwx   1 root     other          7 Jan 25 00:17 bin -> usr/bin" */
            # Note that UNIX-style listings can use names that contain a space:
            #   "-rw-------  1 incognito.guy Domain Users 11420 2011-12-29 18:51 .bash_history"
            # Also produced by Microsoft's FTP servers for Windows: */
            #   "----------   1 owner    group         1803128 Jul 10 10:18 ls-lR.Z" */
            #   "d---------   1 owner    group               0 May  9 19:45 Softlib" */
            # Also WFTPD for MSDOS: */
            #   "-rwxrwxrwx   1 noone    nogroup      322 Aug 19  1996 message.ftp" */
            # Also NetWare: */
            #   "d [R----F--] supervisor            512       Jan 16 18:53    login" */
            #   "- [R----F--] rhesus             214059       Oct 20 15:27    cx.exe" */
            # Also NetPresenz and Rumpus on the Mac: */
            #   "-------r--         326  1391972  1392298 Nov 22  1995 MegaPhone.sit" */
            #   "drwxrwxr-x               folder        2 May 10  1996 network" */

            # We used to regex on the line, but that is too slow, now we just
            # use split() and do our best with that.
            fi = line.split(None, 7)
            if len(fi) == 7 and fi[1] == "folder":
                # NetPresenz and Rumpus folder format
                fi = fi[:1] + ["", ""] + fi[2:]

            # First char dictates the type of file
            if line[0] == "d":
                mode |= stat.S_IFDIR    # directory
            elif line[0] == "-":
                mode |= stat.S_IFREG    # regular file
            elif line[0] == "l":
                mode |= stat.S_IFLNK    # symlink
                isSymlink = True
            elif line[0] == "s":
                mode |= stat.S_IFSOCK    # socket
            elif line[0] == "b":
                mode |= stat.S_IFBLK    # block type (special file)
            elif line[0] == "c":
                mode |= stat.S_IFCHR    # character type (special file)
            else:
                mode |= stat.S_IFREG    # unknown
                #self.log.debug("THIS IS A SYMLINK!!!")
            # we unfortunately dont know if we are owner or group member, so guess again
            mode_str = fi[0]
            # Determine the file permissions, i.e. from the line "drwxr-xr-x"
            if mode_str[1:2] == "r": mode |= stat.S_IRUSR
            if mode_str[2:3] == "w": mode |= stat.S_IWUSR
            if mode_str[3:4] == "x": mode |= stat.S_IXUSR
            elif mode_str[3:4] == "s": mode |= (stat.S_IXUSR | stat.S_ISUID)
            elif mode_str[3:4] == "S": mode |= stat.S_ISUID
            if mode_str[4:5] == "r": mode |= stat.S_IRGRP
            if mode_str[5:6] == "w": mode |= stat.S_IWGRP
            if mode_str[6:7] == "x": mode |= stat.S_IXGRP
            elif mode_str[6:7] == "s": mode |= (stat.S_IXGRP | stat.S_ISGID)
            elif mode_str[6:7] == "S": mode |= stat.S_ISGID
            if mode_str[7:8] == "r": mode |= stat.S_IROTH
            if mode_str[8:9] == "w": mode |= stat.S_IWOTH
            if mode_str[9:10] == "x": mode |= stat.S_IXOTH
            elif mode_str[9:10] == "t": mode |= (stat.S_IXOTH | stat.S_ISVTX)
            elif mode_str[9:10] == "T": mode |= stat.S_ISVTX

            # Deal with spaces in the user or group names - bug .
            if fi[4] and fi[4][0].lower() in ascii_lowercase and \
               fi[5] and fi[5][0] in string_digits and \
               fi[7] and fi[7][0] in string_digits and \
               " " in fi[7] and \
               fi[3] and fi[3][0].lower() in ascii_lowercase and \
               fi[2] and fi[2][0].lower() in ascii_lowercase:
                while len(fi) >= 8:
                    fi[3] += fi.pop(5)
                    fi = fi[:6] + fi[6].split(None, 1)
                    if fi[5] and fi[5][0] in string_digits:
                        break
                    
            if fi[4].lower() in self._3char_month_names:
                # Not enough fields, pad it out.
                fi.insert(1, "")
            if fi[4]: self.st_size = fi[4] # File size

            # Work out the date
            try:
                # Date is in fi[5], check it's format. I.e
                #   "Nov 30"
                #   "2005-11-30"
                #   "26 fev"
                # to see if we have a time, or a year?
                guessedYear = False
                if fi[5] and (fi[5][0] not in string_digits or
                              (len(fi[6]) == 3 and fi[6][0] not in string_digits)):
                    if " " in fi[7] and fi[7][0] in string_digits:
                        # Requires the filename field to be split up:
                        fi = fi[:1] + fi[2:7] + fi[7].split(None, 1)
                    if len(fi) == 9:
                        fi.pop(1)
                    month,day,year = fi[4:7]

                    # Some locales swap the day and the month, i.e. french:
                    #   "26 fev 22:00", bug 88866.
                    if month and month[0] in string_digits and \
                       day and day not in string_digits:
                        day, month = month, day

                    if year.find(":") > -1:
                        hour = year
                        # fix time to be 5 digit always
                        year = "%d"%(time.gmtime(time.time())[0])
                        guessedYear = True
                    else:
                        hour = "00:00"

                    if len(day) < 2: day = "0"+day
                    if len(hour) < 5: hour = "0"+hour
                    date = "%s %s %s %s" % (month, day, year, hour)
                    try:
                        # Note: This can fail due to locale differences between
                        #       the client and server, as time.strptime uses the
                        #       locale for converting the fields. If this does
                        #       fail, we give it one other chance using default
                        #       English as the locale setting. See bug:
                        # http://bugs.activestate.com/show_bug.cgi?id=62638
                        t = time.strptime(date, '%b %d %Y %H:%M')
                    except Exception, e:     # Error parsing the date field
                        # Try using internal strptime, with ENGLISH setting
                        t = strptime.strptime(date, '%b %d %Y %H:%M')
                else:
                    sp = fi[5].split('-', 2)
                    if len(sp) == 3:
                        # 2005-11-30 format
                        year, month, day = sp
                        hour = fi[6]
                        date = "%s %s %s %s" % (year, month, day, hour)
                        t = time.strptime(date, '%Y %m %d %H:%M')
                    else:
                        raise Exception("Uknown date")

                self.st_mtime = time.mktime(t)
                if guessedYear:
                    # Bug 81475.
                    # If the time is more than a day ahead, set it back one
                    # year. For example, we recieved: "Dec 31 23:29", but
                    # if today's date is "March 18 2009", then the year should
                    # actually be 2008, otherwise the date is in the future...
                    # A date too far ahead is defined as two days greater than
                    # the current local machine time (> 99% correct).
                    if self.st_mtime >= time.time() + (2 * 60 * 60 * 24):
                        t = list(t)
                        t[0] -= 1
                        self.st_mtime = time.mktime(t)

            except Exception, e:     # Error parsing the date field
                #print "\n%s" % e
                self.log.warn("Unknown date in line: '%s'" % (line))
                self.st_mtime = 0   # Unknown date, 1970 it is!

            if isSymlink:
                filename, link_target = fi[7].split(" -> ")
                #self.log.debug("Symlink %s -> %s", filename, link_target)
            else:
                filename = fi[7]

        else: # msdos style lines
            fig = re_parse_dos_ftp_line.search(line)
            # Examples:
            #   "03-07-06  11:39AM            598917120 photos.tar"
            #   "07-03-06  10:19AM       <DIR>          home"
            if not fig:
                log.debug("initFromDirectoryListing: Regex does not match for the given input: '%s'", line)
                return False
            fi = fig.groups()
            # we simply don't know, so say yes!

            mode |= stat.S_IREAD
            mode |= stat.S_IWRITE
            mode |= stat.S_IEXEC
            # mode |= stat.S_IFDIR    # directory
            mode |= stat.S_IFREG    # regular file
            # mode |= stat.S_IFLNK    # symlink
            
            if str(fi[1][:5]) == '<DIR>':
                # this is a directory
                mode |= stat.S_IFDIR    # directory
                mode -= stat.S_IFREG    # regular file
                self.st_size = '0'
            else:
                self.st_size = fi[1]

            try:
                #t = time.strptime(fi[0],'%m-%d-%y  %I:%M%p')
                try:
                    # Note: This can fail due to locale differences between
                    #       the client and server, as time.strptime uses the
                    #       locale for converting the fields. If this does
                    #       fail, we give it one other chance using default
                    #       English as the locale setting. See bug:
                    # http://bugs.activestate.com/show_bug.cgi?id=62638
                    t = time.strptime(fi[0],'%m-%d-%y  %I:%M%p')
                except Exception, e:     # Error parsing the date field
                    # Try using internal strptime, with ENGLISH setting
                    t = strptime.strptime(fi[0],'%m-%d-%y  %I:%M%p')
                #print "date trans: ",repr(t)
                self.st_time = time.mktime(t)
            except Exception, e:     # Error parsing the date field
                #print "\n%s" % e
                self.log.warn("Unknown date in line: '%s'" % (line))
                self.st_mtime = 0   # Unknown date, 1970 it is!

            filename = fi[2]
        #print "filename:", filename
        self.st_mode = mode
        # Set the full path
        # XXX - Windows/DOS filenames break ??
        self._setpathinfo(dirname, filename, link_target)
        #self.log.debug("initFromDirectoryListing: %s", self)
        return True

    # Readonly attributes
    def get_size(self):
        return self.st_size
    def get_mode(self):
        return self.st_mode
    def get_uid(self):
        return self.st_uid
    def get_gid(self):
        return self.st_gid
    def get_mtime(self):
        return self.st_mtime

    def __str__(self):
        s = ""
        if self.isDirectory():
            s += "D"
        if self.isFile():
            s += "F"
        if self.isReadable():
            s += "r"
        if self.isWriteable():
            s += "w"
        if self.isSymlink():
            return "%s (link -> %s) m:%s sz:%r c:%r %s fp:'%s'" % (self.filename, self.link_target, s, self.st_size, len(self.children), time.asctime(time.localtime(self.st_mtime)), self.path)
        else:
            return "%s m:%s sz:%r c:%r %s fp:'%s'" % (self.filename, s, self.st_size, len(self.children), time.asctime(time.localtime(self.st_mtime)), self.path)

    def __repr__(self):
        return str(self)
