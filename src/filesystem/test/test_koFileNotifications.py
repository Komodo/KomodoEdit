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

# Standalone testing of file notification system.
#   - Tests os file notifications if available on this platform
#   - Tests the fallback polling service, available on all platforms
#
# Contributors:
# * Todd Whiteman

import os
import sys
import stat
import time
import random
import logging
import tempfile
import shutil
import threading
import unittest

try:
    from osFileNotificationUtils import *
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from osFileNotificationUtils import *


log = None
POLL_PERIOD = 0.3

TYPE_POLLING = 1
TYPE_OS_NOTIFICATIONS = 2

notifications_type = TYPE_OS_NOTIFICATIONS

#############################################################
#                   Test  utilities                         #
#############################################################

# Return a logger that will output to the console
def test_setupDummyLogger(name):
    log = logging.getLogger(name)
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(name)s: %(message)s')
    console.setFormatter(formatter)
    #console.setLevel(loglevel)
    log.addHandler(console)
    return log

#
# Create a number of temporary directories and files.
#
def _get_temporary_dirs_for_testing(maintempdir, num_dirs=1, files_per_dir=0):
    tmpdirs = {}
    for i in range(num_dirs):
        tmpdirname = os.path.realpath(tempfile.mkdtemp(dir=maintempdir))
        tmpfiles = {}
        for i in range(files_per_dir):
            fd, tmpfilename = tempfile.mkstemp(dir=tmpdirname)
            os.write(fd, "Hello\n")
            os.close(fd)
            tmpfiles[os.path.realpath(tmpfilename)] = 1
        tmpdirs[tmpdirname] = tmpfiles
    return tmpdirs

class _test_koIFileNotificationObserver:
    # Implements koIFileNotificationObserver
    def __init__(self, fws):
        self.__fws = fws
        self.__event = threading.Event()
        self.notifications = {}
        self.lock = threading.Lock()

    def fileNotification(self, path, flags):
        #self.lock.acquire()
        #try:
            log.debug("Received file notification (%x) on path: %s", flags, path)
            existing_changes = self.notifications.get(path, 0)
            flags |= existing_changes
            self.notifications[path] = flags
            self.set()
        #finally:
        #    self.lock.release()

    def set(self):
        # Lock already acquired
        self.__event.set()

    def wait(self):
        # We wait a little bit more than POLL_PERIOD to give the service
        # time to process all of it's events
        self.__event.wait(POLL_PERIOD + 0.1)
        self.__fws.waitTillFinishedRun()

    def clear(self):
        #self.lock.acquire()
        #try:
            self.notifications = {}
            self.__event.clear()
        #finally:
        #    self.lock.release()

    def wasNotifiedOn(self, path, notify_change):
        #self.lock.acquire()
        #try:
            path = pathToUri(path)
            change = self.notifications.get(path, 0)
            if change:
                #print "path: %s" % path
                #print "wasNotifiedOn: change: %x, notify_change:%x" % (change, notify_change)
                log.debug("wasNotifiedOn: change: %x", change)
                #print "notify_change & change: %r" % ((notify_change & change) > 0)
                return ((notify_change & change) > 0)
            return False
        #finally:
        #    self.lock.release()

    def __str__(self):
        msg = [ "_test_koIFileNotificationObserver notifications\n" ]
        for path, change in self.notifications.items():
            msg.append("  change: %x, path: %s\n" % (change, path))
        return ''.join(msg)

    def dump(self, only_this_path=None):
        if len(self.notifications) > 0:
            log.debug("_test_koIFileNotificationObserver notifications")
        for path, change in self.notifications.items():
            if not only_this_path or path == only_this_path:
                log.debug("  change: %x, path: %s", change, path)

def _get_testing_file_watcher_service(test_name, log_level):
    global log
    global POLL_PERIOD
    global notifications_type
    if not log:
        log = test_setupDummyLogger(test_name)
    log.setLevel(log_level)

    # Determine which platform to use for OS level file notifications
    if notifications_type == TYPE_POLLING:
        import osFilePollingNotifier
        log.info("Setting up file polling service")
        osFilePollingNotifier.POLL_PERIOD = POLL_PERIOD
        #POLL_PERIOD = osFilePollingNotifier.POLL_PERIOD
        FWS = osFilePollingNotifier.osFilePollingNotifier
    else:
        try:
            from watchdogFileNotifications import WatchdogFileNotificationService as FWS
        except ImportError:
            # Find the locations.
            dn = os.path.dirname
            parentdir = dn(dn(os.path.abspath(__file__)))
            contribdir = os.path.join(dn(dn(parentdir)), "contrib")
            sys.path.append(os.path.join(contribdir, "pathtools"))
            sys.path.append(os.path.join(contribdir, "watchdog", "src"))
            from watchdogFileNotifications import WatchdogFileNotificationService as FWS

    if notifications_type == TYPE_POLLING:
        osFilePollingNotifier.log = log
    fws = FWS()
    fws.startNotificationService()
    time.sleep(1)   # Give the thread time to start up
    return fws


#############################################################
#                   Test edge cases                         #
#############################################################

#
# test_file_notification_on_read()
#   - file exists, ensure no notifications if we just open file for reading
#
class test_monitoring_files(unittest.TestCase):
    def setUp(self):
        self.maintempdir = tempfile.mkdtemp(".FNS", "koFNSDirectory")
        self.fws = _get_testing_file_watcher_service("fws_tests", logging.WARN)
        self.file_observer = _test_koIFileNotificationObserver(self.fws)
        self.tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=1, files_per_dir=4)
        self.action_list = {}
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir].keys()
            self.action_list[tmpdir] = {}
            self.action_list.get(tmpdir)[ tmpfiles[0] ] = FS_FILE_MODIFIED
            self.action_list.get(tmpdir)[ tmpfiles[1] ] = FS_FILE_DELETED
            self.action_list.get(tmpdir)[ tmpfiles[2] ] = FS_FILE_CREATED
            self.action_list.get(tmpdir)[ tmpfiles[3] ] = FS_NOTIFY_ALL
            # Watch our four files in different ways
            for filename, watch_flags in self.action_list[tmpdir].items():
                assert self.fws.addObserver( self.file_observer, filename, WATCH_FILE, watch_flags ) == True
        # Give chance for observers to initialize
        time.sleep(POLL_PERIOD + 0.2)

    def tearDown(self):
        self.fws.stopNotificationService()
        shutil.rmtree(self.maintempdir, ignore_errors=True)

    def test_file_notification_on_read(self):
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir]
            # Open for reading, should not have any affect
            for filename in tmpfiles:
                file(filename, "r").read()

        self.file_observer.wait()
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir]
            for filename, watch_flags in self.action_list[tmpdir].items():
                assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )

            # cleanup
            for filename in tmpfiles:
                self.fws.removeObserver( self.file_observer, filename )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_file_notification_on_write()
    #   - file exists, ensure notification received when modified
    #
    def test_file_notification_on_write(self):
        #log.setLevel(logging.DEBUG)
        log.debug("\n\n\n\n\n\ntest_file_notification_on_write\n\n\n\n\n\n")
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir]
            # Modify them all
            for filename in tmpfiles:
                file(filename, "w").write("File updated now!\n")
    
        self.file_observer.wait()
        time.sleep(POLL_PERIOD + 0.2)
        log.debug("\n\n\n\n\n\n")
        log.debug("%s", self.file_observer)
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir]
            for filename, watch_flags in self.action_list[tmpdir].items():
                log.debug("Checking watch_flags: %x on %s", watch_flags, filename)
                if watch_flags & FS_FILE_MODIFIED:
                    assert( self.file_observer.wasNotifiedOn(filename, FS_FILE_MODIFIED) )
                else:
                    # Others should not be notified
                    assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )
    
            # cleanup
            for filename in tmpfiles:
                self.fws.removeObserver( self.file_observer, filename )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now
    
    #
    # test_file_notification_on_delete()
    #   - file exists, ensure notification received when file deleted
    #
    def test_file_notification_on_delete(self):
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir]
            # Remove them all
            for filename in tmpfiles:
                os.unlink(filename)

        self.file_observer.wait()
        time.sleep(POLL_PERIOD + 0.2)
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir]
            for filename, watch_flags in self.action_list[tmpdir].items():
                if watch_flags & FS_FILE_DELETED:
                    assert( self.file_observer.wasNotifiedOn(filename, FS_FILE_DELETED) )
                else:
                    # Others should not be notified
                    assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )

            # cleanup
            for filename in tmpfiles:
                self.fws.removeObserver( self.file_observer, filename )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_file_notification_on_create()
    #   - file exists, ensure notification received when file is created
    #
    #def test_file_notification_on_create(self):
    #    # Cannot currently watch a non-created file
    #    pass
        ## Delete them all first
        #for tmpdir in self.tmpdirs:
        #    tmpfiles = self.tmpdirs[tmpdir]
        #    for filename in tmpfiles:
        #        # This removes our watcher
        #        os.unlink(filename)
        #self.file_observer.wait()
        #self.file_observer.clear()
        #
        #for tmpdir in self.tmpdirs:
        #    tmpfiles = self.tmpdirs[tmpdir]
        #    # Create them all
        #    log.debug("TEST notification received on create")
        #    for filename in tmpfiles:
        #        file(filename, "w").close()
        #    self.file_observer.wait()
        #    for filename, watch_flags in self.action_list[tmpdir].items():
        #        if watch_flags & FS_FILE_CREATED:
        #            assert( self.file_observer.wasNotifiedOn(filename, FS_FILE_CREATED) )
        #        else:
        #            # Others should not be notified
        #            assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )
        #    self.file_observer.clear()
        #    # Wait a few seconds to make sure we don't get extra notifications
        #    time.sleep(1)
        #    for filename, watch_flags in self.action_list[tmpdir].items():
        #        assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )        
        #
        #    # cleanup
        #    for filename in tmpfiles:
        #        self.fws.removeObserver( self.file_observer, filename )
        #assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_file_notification_on_move()
    #   - file exists, ensure notification received when file is moved
    #
    def test_file_notification_on_move(self):
        #log.setLevel(logging.DEBUG)
        log.debug("\n\n\n\n\n\ntest_file_notification_on_move\n\n\n\n\n\n")
        for tmpdir in self.tmpdirs:
            #print "tmpdir: ", tmpdir
            #print "before:"
            #print os.popen("ls -la %s" % (tmpdir)).read()
            tmpfiles = self.tmpdirs[tmpdir]
            # Move them all (counts as deletion)
            log.debug("TEST notification received on move")
            for filename, watch_flags in self.action_list[tmpdir].items():
                os.rename(filename, filename + ".moved")
            #print "after:"
            #print os.popen("ls -la %s" % (tmpdir)).read()

        self.file_observer.wait()
        time.sleep(POLL_PERIOD + 0.2)
        log.debug("\n\n\n\n\n\n")
        log.debug("%s", self.file_observer)
        for tmpdir in self.tmpdirs:
            for filename, watch_flags in self.action_list[tmpdir].items():
                #print "watch_flags:", watch_flags
                mv_filename = filename + ".moved"
                log.debug("Check watch_flags: %x, %s", watch_flags, mv_filename)
                #print "mv_filename:", mv_filename
                assert( self.file_observer.wasNotifiedOn(filename, FS_FILE_DELETED) == ((watch_flags & FS_FILE_DELETED) > 0) )

        time.sleep(POLL_PERIOD + 0.2)
        # Moved (deleted), so should ont be monitoring anything now
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    ##
    ## test_file_notification_on_create()
    ##   - file exists, ensure notification received when modified
    ##
    #def test_file_notification_on_create(self):
    #    self.file_observer, self.tmpdirs, self.action_list[tmpdir] = _setup_test_case(self)
    #    # These should work fine
    #    for tmpdir in self.tmpdirs:
    #        tmpfiles = self.tmpdirs[tmpdir]
    #        # Create them all
    #        log.debug("TEST notification received on re-create")
    #        for filename in tmpfiles:
    #            file(filename, "w").write("Howdy doody!")
    #        self.file_observer.wait()
    #        for filename, watch_flags in self.action_list[tmpdir].items():
    #            if watch_flags & FS_FILE_CREATED:
    #                assert( self.file_observer.wasNotifiedOn(filename, FS_FILE_CREATED) )
    #            else:
    #                # Others should not be notified
    #                assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )
    #        self.file_observer.clear()
    #        # Wait a few seconds to make sure we don't get extra notifications
    #        time.sleep(1)
    #        for filename, watch_flags in self.action_list[tmpdir].items():
    #            assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )        
    #
    #        # cleanup
    #        for filename in tmpfiles:
    #            fws.removeObserver( self.file_observer, filename )
    #    assert(fws.number_of_observed_locations == 0)   # Should not be watching anything now
    #
    #
    # test_file_notification_on_chmod()
    #   - file exists, ensure notification received when attributes change
    #
    def test_file_notification_on_chmod(self):
        if sys.platform.startswith("win"):
            # Readonly
            chmod_value = 0
        else:
            chmod_value = 0400
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir]
            # Make readonly
            for filename in tmpfiles:
                os.chmod(filename, chmod_value)

        self.file_observer.wait()
        time.sleep(POLL_PERIOD + 0.2)
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir]
            for filename, watch_flags in self.action_list[tmpdir].items():
                if watch_flags & FS_FILE_MODIFIED:
                    assert( self.file_observer.wasNotifiedOn(filename, FS_FILE_MODIFIED) )
                else:
                    # Others should not be notified
                    assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )

            # cleanup
            for filename in tmpfiles:
                self.fws.removeObserver( self.file_observer, filename )
                if sys.platform.startswith("win"):
                    # Make sure it's writeable, so we can remove it later on
                    os.chmod(filename, stat.S_IWRITE)
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_file_notification_on_chown()
    #   - file exists, ensure notification received when ownership changes
    #
    def test_file_notification_on_chown(self):
        if 0 and hasattr(os, "getuid"):
            for tmpdir in self.tmpdirs:
                tmpfiles = self.tmpdirs[tmpdir]
                # Change ownership (chown)
                # XXX - Removed for now
                groups = os.getgroups()
                chowned = False
                for filename, watch_flags in self.action_list[tmpdir].items():
                    s = os.stat(filename)
                    for gid in os.getgroups():
                        if gid != s.st_gid:
                            break
                    else:
                        log.warn("Could not find alternative group for chown test")
                        break
                    # Change the group ownership
                    os.chown(filename, -1, gid)
                    chowned = True
                if chowned:
                    self.file_observer.wait()
                    for filename, watch_flags in self.action_list[tmpdir].items():
                        if watch_flags & FS_FILE_MODIFIED:
                            assert( self.file_observer.wasNotifiedOn(filename, FS_FILE_MODIFIED) )
                        else:
                            # Others should not be notified
                            assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )
                    self.file_observer.clear()
                    # Wait a few seconds to make sure we don't get extra notifications
                    time.sleep(2)
                    for filename, watch_flags in self.action_list[tmpdir].items():
                        assert( not self.file_observer.wasNotifiedOn(filename, FS_NOTIFY_ALL) )        

                for filename in tmpfiles:
                    self.fws.removeObserver( self.file_observer, filename )
            assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    #   deleteObserver()   - file being watched is changed, but the observer is deleted
    #                      - expected: is okay, we don't care
    def test_deletedObserver_fileChanged(self):
        # We are watching the files, now delete the observer
        del self.file_observer
        time.sleep(POLL_PERIOD + 0.2)
        for tmpdir in self.tmpdirs:
            tmpfiles = self.tmpdirs[tmpdir]
            # Modify them all
            for filename in tmpfiles:
                file(filename, "w").write("File updated now!\n")

        # no notifications should have been raised
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now


class test_monitoring_files_edge_cases(unittest.TestCase):
    def setUp(self):
        self.maintempdir = tempfile.mkdtemp(".FNS", "koFNSDirectory")
        self.fws = _get_testing_file_watcher_service("fws_tests", logging.WARN)
        time.sleep(POLL_PERIOD + 0.2)

    def tearDown(self):
        self.fws.stopNotificationService()
        shutil.rmtree(self.maintempdir, ignore_errors=True)

    #
    # test_observer_removed_when_path_deleted:
    #   - observed file is deleted
    #   - expected: FS_FILE_DELETED notification received
    #   - expected: no observers left
    def test_observer_removed_when_path_deleted(self):
        observer = _test_koIFileNotificationObserver(self.fws)
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now
        # Try with a watched file
        fd, tmpfilename = tempfile.mkstemp(dir=self.maintempdir)
        os.close(fd)    # Close it, otherwise we cannot remove it (windows)
        assert self.fws.addObserver( observer, tmpfilename, WATCH_FILE, FS_NOTIFY_ALL ) == True
        assert(self.fws.number_of_observed_locations == 1)   # Should be watching this file
        #time.sleep(POLL_PERIOD + 0.2)
        log.debug("Removing path: '%s'", tmpfilename)
        os.unlink(tmpfilename)
        observer.wait()
        assert(observer.wasNotifiedOn(tmpfilename, FS_FILE_DELETED))
        time.sleep(POLL_PERIOD + 0.2)
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now
        # Try with a watched directory
        observer = _test_koIFileNotificationObserver(self.fws)
        tmpdirname = tempfile.mkdtemp(dir=self.maintempdir)
        assert self.fws.addObserver( observer, tmpdirname, WATCH_DIR_RECURSIVE, FS_NOTIFY_ALL ) == True
        assert(self.fws.number_of_observed_locations == 1)   # Should be watching this dir
        os.rmdir(tmpdirname)
        observer.wait()
        assert(observer.wasNotifiedOn(tmpdirname, FS_DIR_DELETED))
        time.sleep(POLL_PERIOD + 0.2)
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now
    
    #
    #   addObserver()   - file does not exist but directory does
    #                   - expected: is okay, we watch it anyway
    def test_addObserver_notExistingFile(self):
        observer = _test_koIFileNotificationObserver(self.fws)
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now
        non_existing_filename = os.path.abspath(".") + os.sep + "_fws_not_exist_file.tmp"
        assert self.fws.addObserver( observer, non_existing_filename, WATCH_FILE, FS_NOTIFY_ALL ) == True
        assert(self.fws.number_of_observed_locations == 1)   # Should be watching this file
        self.fws.removeObserver( observer, non_existing_filename )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    #   addObserver() - file's directory does exist
    #                   - expected: error logged, we cannot watch it
    #                   - no exception raised through koIFileNotificationService
    #                   - watchFile() returns False
    # XXX - Removed, should be handled by the fileNotificationService now
    #def test_addObserver_notExistingDirectory(self):
    #    observer = _test_koIFileNotificationObserver(self.fws)
    #    non_existing_filename = os.path.abspath(".") + os.sep + "_non_existing_directory.fws" + os.sep + "_fws_not_exist_file.tmp"
    #    assert self.fws.addObserver( observer, non_existing_filename, WATCH_FILE, FS_NOTIFY_ALL ) == False
    #    assert(self.fws.number_of_observed_locations == 0)   # Should not be watching this file
    #    self.fws.removeObserver( observer, non_existing_filename )
    #    assert(self.fws.number_of_observed_locations == 0)   # Should not be watching this file

    #
    #   removeObserver()   - file not being watched
    #                      - expected: is okay, we don't care
    def test_removeObserver_fileNotWatched(self):
        observer = _test_koIFileNotificationObserver(self.fws)
        non_existing_filename = os.path.abspath(".") + os.sep + "_fws_not_watched_file.tmp"
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything
        self.fws.removeObserver( observer, non_existing_filename )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now


#
# Simple monitoring tests done on a directory level
#
class test_monitoring_directory(unittest.TestCase):
    def setUp(self):
        self.maintempdir   = tempfile.mkdtemp(".FNS", "koFNSDirectory")
        self.fws           = _get_testing_file_watcher_service("fws_tests", logging.WARN)
        self.tmpdirs       = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=8, files_per_dir=3)
        self.dir_observers = {}
        self.action_list   = {}

        action = FS_FILE_CREATED
        for tmpdir in self.tmpdirs:
            dirObserver = _test_koIFileNotificationObserver(self.fws)
            self.dir_observers[tmpdir] = dirObserver
            self.action_list[tmpdir] = action
            assert self.fws.addObserver( dirObserver, tmpdir, WATCH_DIR, action ) == True
            action *= 2
            if action >= FS_NOTIFY_ALL:
                action = FS_NOTIFY_ALL
            assert len(dirObserver.notifications) == 0
        # Give chance for observers to initialize
        time.sleep(POLL_PERIOD + 0.2)

    def tearDown(self):
        self.fws.stopNotificationService()
        shutil.rmtree(self.maintempdir, ignore_errors=True)

    def test_directory_file_notification_on_read(self):
        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            tmpfiles = self.tmpdirs[tmpdir]
            # Open for reading, should not have any affect
            for filename in tmpfiles:
                file(filename, "r").read()
            dirObserver.wait()
            assert len(dirObserver.notifications) == 0

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now


    #
    # test_directory_file_notification_on_write()
    #   - file exists, ensure notification received when modified
    #
    def test_directory_file_notification_on_write(self):
        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            tmpfiles = self.tmpdirs[tmpdir]
            # Modify them all
            for filename in tmpfiles:
                file(filename, "w").write("File updated now!\n")
            dirObserver.wait()
            for filename in tmpfiles:
                assert( dirObserver.wasNotifiedOn(filename, FS_FILE_MODIFIED) == ((watch_flags & FS_FILE_MODIFIED) > 0) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_directory_file_notification_on_delete()
    #   - file exists, ensure notification received when file deleted
    #
    def test_directory_file_notification_on_delete(self):
        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            tmpfiles = self.tmpdirs[tmpdir]
            # Remove them all
            for filename in tmpfiles:
                os.unlink(filename)
            dirObserver.wait()
            for filename in tmpfiles:
                assert( dirObserver.wasNotifiedOn(filename, FS_FILE_DELETED) == ((watch_flags & FS_FILE_DELETED) > 0) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )

            # There was bug in the poller here
            time.sleep(POLL_PERIOD + 0.2)

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_directory_file_notification_on_create()
    #   - file exists, ensure notification received when file is created
    #
    def test_directory_file_notification_on_create(self):
        created_files = {}
        for tmpdir in self.tmpdirs:
            # Create a file
            fd, filename = tempfile.mkstemp(dir=tmpdir)
            os.write(fd, "Hello\n")
            os.close(fd)
            created_files[tmpdir] = filename

        time.sleep(POLL_PERIOD + 0.2)
        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            filename = created_files[tmpdir]
            if sys.platform.startswith("win") and notifications_type == TYPE_OS_NOTIFICATIONS:
                # Windows, notifies creation with a create and a modify message
                if watch_flags == FS_FILE_MODIFIED:
                    assert( dirObserver.wasNotifiedOn(filename, FS_FILE_MODIFIED) )
                else:
                    assert( dirObserver.wasNotifiedOn(filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
            else:
                assert( dirObserver.wasNotifiedOn(filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
            #assert( dirObserver.wasNotifiedOn(filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_directory_file_notification_on_move()
    #   - file exists, ensure notification received when file is moved
    #
    def test_directory_file_notification_on_move(self):
        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            tmpfiles = self.tmpdirs[tmpdir]
            # Move them all (counts as deletion and creation)
            log.debug("TEST notification received on move")
            for filename in tmpfiles:
                os.rename(filename, filename + ".moved")
            dirObserver.wait()
            for filename in tmpfiles:
                mv_filename = filename + ".moved"
                assert( dirObserver.wasNotifiedOn(filename, FS_FILE_DELETED) == ((watch_flags & FS_FILE_DELETED) > 0) )
                if sys.platform.startswith("win") and notifications_type == TYPE_OS_NOTIFICATIONS:
                    # Windows, notifies on-move with a create and a modify message
                    if watch_flags == FS_FILE_MODIFIED:
                        assert( dirObserver.wasNotifiedOn(mv_filename, FS_FILE_MODIFIED) )
                    else:
                        assert( dirObserver.wasNotifiedOn(mv_filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
                else:
                    assert( dirObserver.wasNotifiedOn(mv_filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_directory_notification_on_create_directory()
    #   - dir exists, ensure notification received when new directory is created
    #
    def test_directory_notification_on_create_and_delete_directory(self):
        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            tmpfiles = self.tmpdirs[tmpdir]
            # Create a new dir
            sub_dir = tempfile.mkdtemp(dir=tmpdir)
            # Create a file in the new dir
            fd, filename = tempfile.mkstemp(dir=sub_dir)
            os.write(fd, "Hello\n")
            os.close(fd)
            dirObserver.wait()
            assert( dirObserver.wasNotifiedOn(sub_dir, FS_DIR_CREATED) == ((watch_flags & FS_DIR_CREATED) > 0) )
            # Should not get this notification, as we are not recursively checking
            assert( not dirObserver.wasNotifiedOn(filename, FS_NOTIFY_ALL) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            time.sleep(POLL_PERIOD + 0.2)
            dirObserver.clear()
            # Remove the new dir
            shutil.rmtree(sub_dir)
            dirObserver.wait()
            #print dirObserver
            #print "sub_dir:", sub_dir
            assert( dirObserver.wasNotifiedOn(sub_dir, FS_DIR_DELETED) == ((watch_flags & FS_DIR_DELETED) > 0) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now


#
# Simple monitoring tests done on a directory level, checking recursively
#
class test_monitoring_directories_recursively(unittest.TestCase):
    def setUp(self):
        self.maintempdir   = tempfile.mkdtemp(".FNS", "koFNSDirectory")
        self.fws           = _get_testing_file_watcher_service("fws_tests", logging.WARN)
        self.tmpdirs       = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=8, files_per_dir=3)
        self.sub_dirs      = {}
        self.dir_observers = {}
        self.action_list   = {}

        action = FS_FILE_CREATED
        for tmpdir in self.tmpdirs:
            dirObserver = _test_koIFileNotificationObserver(self.fws)
            self.dir_observers[tmpdir] = dirObserver
            self.action_list[tmpdir] = action
            self.sub_dirs[tmpdir] = _get_temporary_dirs_for_testing(tmpdir, num_dirs=2, files_per_dir=2)
            assert self.fws.addObserver( dirObserver, tmpdir, WATCH_DIR_RECURSIVE, action ) == True
            action *= 2
            if action >= FS_NOTIFY_ALL:
                action = FS_NOTIFY_ALL
            assert len(dirObserver.notifications) == 0
        # Give chance for observers to initialize
        time.sleep(POLL_PERIOD + 0.2)

    def tearDown(self):
        self.fws.stopNotificationService()
        shutil.rmtree(self.maintempdir, ignore_errors=True)

    #
    # test_recursive_directory_file_notification_on_write()
    #   - file exists, ensure notification received when modified
    #
    def test_recursive_directory_file_notification_on_write(self):
        for tmpdir in self.tmpdirs:
            sub_dirs = self.sub_dirs[tmpdir]
            # Modify them all
            for sub_dir in sub_dirs:
                tmpfiles = sub_dirs[sub_dir]
                for filename in tmpfiles:
                    file(filename, "w").write("File updated now!\n")

        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            sub_dirs = self.sub_dirs[tmpdir]
            #log.debug("DIRECTORY: watch_flags:%x, path: %s", watch_flags, tmpdir)
            dirObserver.wait()
            for sub_dir in sub_dirs:
                tmpfiles = sub_dirs[sub_dir]
                for filename in tmpfiles:
                    assert( dirObserver.wasNotifiedOn(filename, FS_FILE_MODIFIED) == ((watch_flags & FS_FILE_MODIFIED) > 0) )
                assert( dirObserver.wasNotifiedOn(sub_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_recursive_directory_file_notification_on_delete()
    #   - file exists, ensure notification received when file deleted
    #
    def test_recursive_directory_file_notification_on_delete(self):
        for tmpdir in self.tmpdirs:
            sub_dirs = self.sub_dirs[tmpdir]
            for sub_dir in sub_dirs:
                # Delete them all
                tmpfiles = sub_dirs[sub_dir]
                #print "tmpfiles:", tmpfiles
                for filename in tmpfiles:
                    #log.debug("Removing filename: %s", filename)
                    os.unlink(filename)

        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            sub_dirs = self.sub_dirs[tmpdir]
            #log.debug("DIRECTORY: watch_flags:%x, path: %s", watch_flags, tmpdir)
            dirObserver.wait()
            #print
            #print dirObserver
            for sub_dir in sub_dirs:
                # Delete them all
                tmpfiles = sub_dirs[sub_dir]
                for filename in tmpfiles:
                    #log.debug("Checking filename: %s", filename)
                    assert( dirObserver.wasNotifiedOn(filename, FS_FILE_DELETED) == ((watch_flags & FS_FILE_DELETED) > 0) )
                assert( dirObserver.wasNotifiedOn(sub_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_recursive_directory_file_notification_on_create()
    #   - file exists, ensure notification received when file is created
    #
    def test_recursive_directory_file_notification_on_create(self):
      #log.setLevel(logging.DEBUG)
      #try:
        created_files = {}
        for tmpdir in self.tmpdirs:
            sub_dirs = self.sub_dirs[tmpdir]
            for sub_dir in sub_dirs:
                created_files[sub_dir] = {}
                # Create a file
                fd, filename = tempfile.mkstemp(dir=sub_dir)
                os.write(fd, "Hello\n")
                os.close(fd)
                created_files[sub_dir][filename] = 1

        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            #log.debug("DIRECTORY: watch_flags:%x, path: %s", watch_flags, tmpdir)
            dirObserver.wait()
            #print
            #print dirObserver
            for sub_dir in self.sub_dirs[tmpdir]:
                for filename in created_files[sub_dir]:
                    #print "filename: ", filename
                    if sys.platform.startswith("win") and notifications_type == TYPE_OS_NOTIFICATIONS:
                        # Windows, notifies create with a create and a modify message
                        if watch_flags == FS_FILE_MODIFIED:
                            assert( dirObserver.wasNotifiedOn(filename, FS_FILE_MODIFIED) )
                        else:
                            assert( dirObserver.wasNotifiedOn(filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
                    else:
                        assert( dirObserver.wasNotifiedOn(filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
                    assert( dirObserver.wasNotifiedOn(sub_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now
      #finally:
      #  log.setLevel(logging.WARN)

    #
    # test_recursive_directory_file_notification_on_move()
    #   - file exists, ensure notification received when file is moved
    #
    def test_recursive_directory_file_notification_on_move(self):
        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            sub_dirs = self.sub_dirs[tmpdir]
            for sub_dir in sub_dirs:
                # Move them all
                tmpfiles = sub_dirs[sub_dir]
                for filename in tmpfiles:
                    os.rename(filename, filename + ".moved")

        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            sub_dirs = self.sub_dirs[tmpdir]
            #log.debug("DIRECTORY: watch_flags:%x, path: %s", watch_flags, tmpdir)
            dirObserver.wait()
            for sub_dir in sub_dirs:
                tmpfiles = sub_dirs[sub_dir]
                for filename in tmpfiles:
                    mv_filename = filename + ".moved"
                    assert( dirObserver.wasNotifiedOn(filename, FS_FILE_DELETED) == ((watch_flags & FS_FILE_DELETED) > 0) )
                    if sys.platform.startswith("win") and notifications_type == TYPE_OS_NOTIFICATIONS:
                        # Windows, notifies on-move with a create and a modify message
                        if watch_flags == FS_FILE_MODIFIED:
                            assert( dirObserver.wasNotifiedOn(mv_filename, FS_FILE_MODIFIED) )
                        else:
                            assert( dirObserver.wasNotifiedOn(mv_filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
                    else:
                        assert( dirObserver.wasNotifiedOn(mv_filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
                assert( dirObserver.wasNotifiedOn(sub_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_recursive_directory_notification_on_create_directory()
    #   - dir exists, ensure notification received when new directory is created
    #
    def test_recursive_directory_notification_on_create_and_delete_directory(self):
      #log.setLevel(logging.DEBUG)
      #try:
        for tmpdir in self.tmpdirs:
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            sub_dirs = self.sub_dirs[tmpdir]
            # Create new dir and file
            for sub_dir in sub_dirs:
                tmpfiles = sub_dirs[sub_dir]
                # Create a new dir
                new_dir = tempfile.mkdtemp(dir=sub_dir)
                # Create a file in the new dir
                fd, filename = tempfile.mkstemp(dir=new_dir)
                os.write(fd, "Hello\n")
                os.close(fd)
                dirObserver.wait()
                #print "\n"
                #print dirObserver
                #print "new_dir:", new_dir
                if sys.platform.startswith("win") and notifications_type == TYPE_OS_NOTIFICATIONS:
                    # Windows, notifies creation with a create and a modify message
                    if watch_flags == FS_DIR_MODIFIED:
                        assert( dirObserver.wasNotifiedOn(new_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
                    else:
                        assert( dirObserver.wasNotifiedOn(new_dir, FS_DIR_CREATED) == ((watch_flags & FS_DIR_CREATED) > 0) )
                    if watch_flags == FS_FILE_MODIFIED:
                        assert( dirObserver.wasNotifiedOn(filename, FS_FILE_MODIFIED) )
                    else:
                        assert( dirObserver.wasNotifiedOn(filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
                else:
                    assert( dirObserver.wasNotifiedOn(new_dir, FS_DIR_CREATED) == ((watch_flags & FS_DIR_CREATED) > 0) )
                    assert( dirObserver.wasNotifiedOn(filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
                assert( dirObserver.wasNotifiedOn(sub_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )

                time.sleep(POLL_PERIOD + 0.2)
                dirObserver.clear()
                # Remove the new dir
                shutil.rmtree(new_dir)
                dirObserver.wait()
                time.sleep(POLL_PERIOD + 0.2)
                assert( dirObserver.wasNotifiedOn(new_dir, FS_DIR_DELETED) == ((watch_flags & FS_DIR_DELETED) > 0) )
                assert( dirObserver.wasNotifiedOn(sub_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
                dirObserver.clear()

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now
      #finally:
      #  log.setLevel(logging.WARN)

    #
    # test_recursive_directory_with_symlinks()
    #   - Ensure we follow symlinked files/dirs properly
    #
    def test_recursive_directory_with_symlinks(self):
        if sys.platform.startswith("win"):
            # Windows does not support the symlink
            return
        #print
        separate_tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=2, files_per_dir=2)
        for tmpdir in self.tmpdirs:
            for link_to_dir in separate_tmpdirs:
                os.system( "ln -s %s %s" % (link_to_dir, tmpdir + os.sep + os.path.basename(link_to_dir)) )
                #print "linked: %s to %s" % (tmpdir + os.sep + os.path.basename(link_to_dir), link_to_dir)
            time.sleep(POLL_PERIOD + 0.2)
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            sub_dirs = self.sub_dirs[tmpdir]
            # Make sure we see the creation of the links
            dirObserver.wait()
            #print dirObserver
            for link_to_dir in separate_tmpdirs:
                link_dir = tmpdir + os.sep + os.path.basename(link_to_dir)
                #print "link_to_dir:", link_to_dir
                #print "link_dir:", link_dir
                assert( dirObserver.wasNotifiedOn(link_dir, FS_DIR_CREATED) == ((watch_flags & FS_DIR_CREATED) > 0) )
                for filename in separate_tmpdirs[link_to_dir]:
                    linked_filename = link_dir + os.sep + os.path.basename(filename)
                    #print "linked_filename:", linked_filename
                    assert( dirObserver.wasNotifiedOn(linked_filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # Make sure we get notifications of changes
            # Modify exist files, should get notifications on both real file path
            # and the linked file path.
            for link_to_dir in separate_tmpdirs:
                for filename in separate_tmpdirs[link_to_dir]:
                    file(filename, "w").write("File updated now!\n")
                    #print "Modified: %s" % (filename)
            # We have to sleep in order to give enough time to get this change
            time.sleep(POLL_PERIOD + 0.2)

            # Make sure we see the modification of the files
            dirObserver.wait()
            #print "watch_flags: %x" % (watch_flags)
            #print dirObserver
            for link_to_dir in separate_tmpdirs:
                for filename in separate_tmpdirs[link_to_dir]:
                    link_dir = tmpdir + os.sep + os.path.basename(link_to_dir)
                    linked_filename = link_dir + os.sep + os.path.basename(filename)
                    #print "link_to_dir:     %s" % (link_to_dir)
                    #print "link_dir:        %s" % (link_dir)
                    #print "linked_filename: %s" % (linked_filename)
                    #print
                    assert( dirObserver.wasNotifiedOn(linked_filename, FS_FILE_MODIFIED) == ((watch_flags & FS_FILE_MODIFIED) > 0) )
                    assert( dirObserver.wasNotifiedOn(link_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_recursive_directory_with_multiple_symlinks()
    #   - Ensure we follow symlinked files/dirs properly
    #
    def test_recursive_directory_with_multiple_symlinks(self):
        if sys.platform.startswith("win"):
            # Windows does not support the symlink
            return
        for tmpdir in self.tmpdirs:
            sub_dirs = self.sub_dirs[tmpdir]
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            # Create some symlinks (chain of 5) to sub_dir
            for sub_dir in sub_dirs:
                link_template = "%s%s%slink_%%d" % (tmpdir, os.sep, os.path.basename(sub_dir))
                #print "ln -s %s %s" % (sub_dir, link_template % 5)
                os.system( "ln -s %s %s" % (sub_dir, link_template % 5) )
                for i in range(4, 0, -1):
                    #print "ln -s %s %s" % (link_template % (i + 1), link_template % i)
                    os.system( "ln -s %s %s" % (link_template % (i + 1), link_template % i) )
                #print os.popen("ls -la %s" % (sub_dir)).read()
            #print os.popen("ls -la %s" % (tmpdir)).read()
            time.sleep(POLL_PERIOD + 0.2)
            # Make sure we see the creation of the links
            dirObserver.wait()
            #print dirObserver
            for sub_dir in sub_dirs:
                link_template = "%s%s%slink_%%d" % (tmpdir, os.sep, os.path.basename(sub_dir))
                for i in range(1, 6):
                    linking_dir = link_template % i
                    assert( dirObserver.wasNotifiedOn(linking_dir, FS_DIR_CREATED) == ((watch_flags & FS_DIR_CREATED) > 0) )
                    for filename in sub_dirs[sub_dir]:
                        linked_filename = linking_dir + os.sep + os.path.basename(filename)
                        #print "linked_filename:", linked_filename
                        assert( dirObserver.wasNotifiedOn(linked_filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # Make sure we get notifications of changes
            # Modify exist files, should get notifications on both real file path
            # and the linked file path.
            for sub_dir in sub_dirs:
                for filename in sub_dirs[sub_dir]:
                    file(filename, "w").write("File updated now!\n")
                    #print "Modified: %s" % (filename)
            # We have to sleep in order to give enough time to get this change
            time.sleep(POLL_PERIOD + 0.2)

            # Make sure we see the modification of the files
            dirObserver.wait()
            #print "watch_flags: %x" % (watch_flags)
            #print dirObserver
            for sub_dir in sub_dirs:
                link_template = "%s%s%slink_%%d" % (tmpdir, os.sep, os.path.basename(sub_dir))
                for i in range(1, 6):
                    linking_dir = link_template % i
                    for filename in sub_dirs[sub_dir]:
                        linked_filename = linking_dir + os.sep + os.path.basename(filename)
                        #print "linked_filename:", linked_filename
                        assert( dirObserver.wasNotifiedOn(linked_filename, FS_FILE_MODIFIED) == ((watch_flags & FS_FILE_MODIFIED) > 0) )
                    assert( dirObserver.wasNotifiedOn(linking_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    # test_recursive_directory_with_cyclical_symlinks()
    #   - Ensure we follow symlinked files properly, but do not get stuck in a
    #     cycle of re-checking the same files over and over.
    #
    def test_recursive_directory_with_cyclical_symlinks(self):
        if sys.platform.startswith("win"):
            # Windows does not support the symlink
            return
        #print
        for tmpdir in self.tmpdirs:
            sub_dirs = self.sub_dirs[tmpdir]
            dirObserver = self.dir_observers[tmpdir]
            watch_flags = self.action_list[tmpdir]
            # Create some symlinks (chain of 5) to sub_dir
            for sub_dir in sub_dirs:
                link_template = "%s%s%slink_%%d" % (tmpdir, os.sep, os.path.basename(sub_dir))
                #print "ln -s %s %s" % (sub_dir, link_template % 5)
                os.system( "ln -s %s %s" % (sub_dir, link_template % 5) )
                for i in range(4, 0, -1):
                    #print "ln -s %s %s" % (link_template % (i + 1), link_template % i)
                    os.system( "ln -s %s %s" % (link_template % (i + 1), link_template % i) )
                # Create the circular link
                os.system( "ln -s %s %slink_back" % (link_template % 1, sub_dir + os.sep) )
            #print os.popen("ls -la %s" % (tmpdir)).read()
            #print os.popen("ls -la %s" % (sub_dir)).read()
            time.sleep(POLL_PERIOD + 0.2)

            # Make sure we see the creation of the links
            dirObserver.wait()
            #print dirObserver
            for sub_dir in sub_dirs:
                link_template = "%s%s%slink_%%d" % (tmpdir, os.sep, os.path.basename(sub_dir))
                for i in range(1, 6):
                    linking_dir = link_template % i
                    assert( dirObserver.wasNotifiedOn(linking_dir, FS_DIR_CREATED) == ((watch_flags & FS_DIR_CREATED) > 0) )
                    for filename in sub_dirs[sub_dir]:
                        linked_filename = linking_dir + os.sep + os.path.basename(filename)
                        #print "linked_filename:", linked_filename
                        assert( dirObserver.wasNotifiedOn(linked_filename, FS_FILE_CREATED) == ((watch_flags & FS_FILE_CREATED) > 0) )
            assert( dirObserver.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # Make sure we get notifications of changes
            # Modify exist files, should get notifications on both real file path
            # and the linked file path.
            for sub_dir in sub_dirs:
                for filename in sub_dirs[sub_dir]:
                    file(filename, "w").write("File updated now!\n")
                #print "Modified: %s" % (filename)
            # We have to sleep in order to give enough time to get this change
            time.sleep(POLL_PERIOD + 0.2)

            # Make sure we see the modification of the files
            dirObserver.wait()
            #print "watch_flags: %x" % (watch_flags)
            #print dirObserver
            for sub_dir in sub_dirs:
                link_template = "%s%s%slink_%%d" % (tmpdir, os.sep, os.path.basename(sub_dir))
                for i in range(1, 6):
                    linking_dir = link_template % i
                    for filename in sub_dirs[sub_dir]:
                        linked_filename = linking_dir + os.sep + os.path.basename(filename)
                        #print "linked_filename:", linked_filename
                        assert( dirObserver.wasNotifiedOn(linked_filename, FS_FILE_MODIFIED) == ((watch_flags & FS_FILE_MODIFIED) > 0) )
                    assert( dirObserver.wasNotifiedOn(linking_dir, FS_DIR_MODIFIED) == ((watch_flags & FS_DIR_MODIFIED) > 0) )
            dirObserver.clear()

            # cleanup
            self.fws.removeObserver( dirObserver, tmpdir )
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now


#
# Monitoring tests done on a both file and directory levels
#
class test_monitoring_files_and_directories(unittest.TestCase):
    def setUp(self):
        self.maintempdir = tempfile.mkdtemp(".FNS", "koFNSDirectory")
        self.fws = _get_testing_file_watcher_service("fws_tests", logging.WARN)

    def tearDown(self):
        self.fws.stopNotificationService()
        shutil.rmtree(self.maintempdir, ignore_errors=True)

    #
    #   Bug: http://bugs.activestate.com/show_bug.cgi?id=45896
    #   watchDirectory()  - directory contains sub-directories with sub-files
    #                     - directory is watch non-recursively
    #                     - expected: no change notification raised for sub-files
    def test_watch_directory_with_unwatched_subdirectories(self):
        dir_observer = _test_koIFileNotificationObserver(self.fws)
        tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=1, files_per_dir=2)
        subdirs = {}
        for tmpdir in tmpdirs:
            # Create sub-dirs
            log.debug("Creating sub-directories")
            subdirs[tmpdir] = _get_temporary_dirs_for_testing(tmpdir, num_dirs=2, files_per_dir=2)
            for subdir in subdirs:
                log.debug("Created sub-dir: %s", subdir)
            assert self.fws.addObserver( dir_observer, tmpdir, WATCH_DIR, FS_NOTIFY_ALL ) == True

            dir_observer.wait()
            assert( len(dir_observer.notifications) == 0 )
            # Wait a few seconds to make sure we don't get extra notifications
            time.sleep(1)
            assert( len(dir_observer.notifications) == 0 )

            # Remove the observer, all was okay
            self.fws.removeObserver( dir_observer, tmpdir )

        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    #   watchDirectory()  - directory is watched but the no files are being watched
    #                     - expected: file change notification raised for directory
    #                     - expected: directory modified notification raised for directory
    def test_watch_directory(self):
        dir_observer = _test_koIFileNotificationObserver(self.fws)
        dir_observer_recursive = _test_koIFileNotificationObserver(self.fws)
        tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=1, files_per_dir=2)
        for tmpdir in tmpdirs:
            assert self.fws.addObserver( dir_observer, tmpdir, WATCH_DIR, FS_NOTIFY_ALL ) == True
            assert self.fws.addObserver( dir_observer_recursive, tmpdir, WATCH_DIR_RECURSIVE, FS_NOTIFY_ALL ) == True
            tmpfiles = tmpdirs[tmpdir].keys()
            tmpfile1 = tmpfiles[0]
            tmpfile2 = tmpfiles[1]

            time.sleep(POLL_PERIOD + 0.2)
            file(tmpfile2, "w").write("File updated now!\n")

            dir_observer.wait()
            assert( not dir_observer.wasNotifiedOn(tmpfile1, FS_NOTIFY_ALL) )
            assert( dir_observer.wasNotifiedOn(tmpfile2, FS_FILE_MODIFIED) )
            assert( dir_observer.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) )

            dir_observer_recursive.wait()
            assert( not dir_observer_recursive.wasNotifiedOn(tmpfile1, FS_NOTIFY_ALL) )
            assert( dir_observer_recursive.wasNotifiedOn(tmpfile2, FS_FILE_MODIFIED) )
            assert( dir_observer_recursive.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) )

            time.sleep(POLL_PERIOD + 0.2)
            dir_observer.clear()
            dir_observer_recursive.clear()
            # Wait a few seconds to make sure we don't get extra notifications
            dir_observer.wait()
            dir_observer_recursive.wait()
            assert( len(dir_observer.notifications) == 0 )
            assert( len(dir_observer_recursive.notifications) == 0 )

            #print "\n\n\nCreating subdirs\n"
            # Create some new temporary sub-directories
            sub_tmpdirs = _get_temporary_dirs_for_testing(tmpdir, num_dirs=2, files_per_dir=2)

            dir_observer.wait()
            dir_observer_recursive.wait()
            #print
            #print dir_observer
            #print
            #print dir_observer_recursive
            #print "\n\n"
            for new_sub_dir, new_sub_dir_files in sub_tmpdirs.items():
                assert( dir_observer.wasNotifiedOn(new_sub_dir, FS_DIR_CREATED) )
                #dir_observer_recursive.dump()
                assert( dir_observer_recursive.wasNotifiedOn(new_sub_dir, FS_DIR_CREATED) )
                for newfilename in new_sub_dir_files:
                    #log.warn("Checking newfilename: '%s'", newfilename)
                    assert( not dir_observer.wasNotifiedOn(newfilename, FS_FILE_CREATED) )
                    assert( dir_observer_recursive.wasNotifiedOn(newfilename, FS_FILE_CREATED) )
            time.sleep(POLL_PERIOD + 0.2)
            dir_observer.clear()
            dir_observer_recursive.clear()

            # Wait a few seconds to make sure we don't get extra notifications
            dir_observer.wait()
            dir_observer_recursive.wait()
            assert( len(dir_observer.notifications) == 0 )
            assert( len(dir_observer_recursive.notifications) == 0 )

            self.fws.removeObserver( dir_observer, tmpdir )
            self.fws.removeObserver( dir_observer_recursive, tmpdir )

        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    #   watchDirectory()  - directory is watched but the file that gets updated is
    #                       also being watched as well
    #                     - expected: dir notification + file notification raised
    #
    # XXX - add test_watchDirectory_fileAlsoWatched (WithSameObserver)
    #
    def test_watch_directory_file_also_watched(self):
        dir_observer  = _test_koIFileNotificationObserver(self.fws)
        tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=1, files_per_dir=2)
        for loop_type in ("watch_file_using_same_observer", "watch_file_using_different_observer"):
            for tmpdir in tmpdirs:
                assert self.fws.addObserver( dir_observer, tmpdir, WATCH_DIR, FS_NOTIFY_ALL ) == True
                tmpfile = tmpdirs[tmpdir].keys()[0]

                if loop_type == "watch_file_using_same_observer":
                    file_observer = dir_observer
                else:
                    file_observer = _test_koIFileNotificationObserver(self.fws)

                assert self.fws.addObserver( file_observer, tmpfile, WATCH_FILE, FS_NOTIFY_ALL ) == True
                time.sleep(1)
                file(tmpfile, "w").write("File updated now!\n")
        
                file_observer.wait()
                assert( file_observer.wasNotifiedOn(tmpfile, FS_FILE_MODIFIED) )
                dir_observer.wait()
                assert( dir_observer.wasNotifiedOn(tmpfile, FS_FILE_MODIFIED) )
                assert( dir_observer.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) )

                self.fws.removeObserver( file_observer, tmpfile )
                self.fws.removeObserver( dir_observer, tmpdir )
                file_observer.clear()
                dir_observer.clear()
        
            assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    #   watchDirectory()  - directory is watched but the file that gets updated is
    #                       not being watched
    #                     - expected: dir notification raised
    def test_watch_directory_file_not_watched(self):
        dir_observer  = _test_koIFileNotificationObserver(self.fws)
        file_observer = _test_koIFileNotificationObserver(self.fws)
        tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=1, files_per_dir=2)
        for tmpdir in tmpdirs:
            assert self.fws.addObserver( dir_observer, tmpdir, WATCH_DIR, FS_NOTIFY_ALL ) == True
            tmpfiles = tmpdirs[tmpdir].keys()
            tmpfile1 = tmpfiles[0]
            tmpfile2 = tmpfiles[1]
            assert self.fws.addObserver( file_observer, tmpfile1, WATCH_FILE, FS_NOTIFY_ALL ) == True

            time.sleep(POLL_PERIOD + 0.2)
            file(tmpfile2, "w").write("File updated now!\n")

            dir_observer.wait()
            assert( not file_observer.wasNotifiedOn(tmpfile1, FS_NOTIFY_ALL) )
            assert( not file_observer.wasNotifiedOn(tmpfile2, FS_NOTIFY_ALL) )
            assert( not dir_observer.wasNotifiedOn(tmpfile1, FS_FILE_MODIFIED) )
            assert( dir_observer.wasNotifiedOn(tmpfile2, FS_FILE_MODIFIED) )
            assert( dir_observer.wasNotifiedOn(tmpdir, FS_DIR_MODIFIED) )

            self.fws.removeObserver( file_observer, tmpfile1 )
            self.fws.removeObserver( dir_observer, tmpdir )
            file_observer.clear()
            dir_observer.clear()

        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    #   watched file        - delete the file being watched
    #                       - expected: is okay, we raise notification changed
    def test_watched_file_gets_deleted(self):
        dir_observer  = _test_koIFileNotificationObserver(self.fws)
        file_observer = _test_koIFileNotificationObserver(self.fws)
        tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=1, files_per_dir=2)
        for tmpdir in tmpdirs:
            assert self.fws.addObserver( dir_observer, tmpdir, WATCH_DIR, FS_NOTIFY_ALL ) == True
            tmpfiles = tmpdirs[tmpdir].keys()
            tmpfile1 = tmpfiles[0]
            tmpfile2 = tmpfiles[1]
            assert self.fws.addObserver( file_observer, tmpfile1, WATCH_FILE, FS_NOTIFY_ALL ) == True
            assert self.fws.addObserver( file_observer, tmpfile2, WATCH_FILE, FS_NOTIFY_ALL ) == True
            time.sleep(POLL_PERIOD + 0.2)

            log.debug("Removing file: %s", tmpfile1)
            os.unlink( tmpfile1 )
            log.debug("Removing file: %s", tmpfile2)
            os.unlink( tmpfile2 )

            file_observer.wait()
            #print
            #print "File Observer:"
            #print file_observer
            assert( file_observer.wasNotifiedOn(tmpfile1, FS_FILE_DELETED) )
            assert( file_observer.wasNotifiedOn(tmpfile2, FS_FILE_DELETED) )

            dir_observer.wait()
            #print
            #print "Dir Observer:"
            #print dir_observer
            assert( dir_observer.wasNotifiedOn( tmpfile1, FS_FILE_DELETED) )
            assert( dir_observer.wasNotifiedOn( tmpfile2, FS_FILE_DELETED) )
            assert( dir_observer.wasNotifiedOn( tmpdir,   FS_DIR_MODIFIED) )

            self.fws.removeObserver( file_observer, tmpfile1 )
            self.fws.removeObserver( file_observer, tmpfile2 )
            self.fws.removeObserver( dir_observer, tmpdir )
            time.sleep(POLL_PERIOD + 0.2)
            file_observer.clear()
            dir_observer.clear()

        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    #
    #   watched file        - delete the directory being watched
    #                       - expected: is okay, we raise notification changed for
    #                       -           all the files that were watched in that dir
    def test_watched_file_directory_gets_deleted(self):
        dir_observer  = _test_koIFileNotificationObserver(self.fws)
        file_observer1 = _test_koIFileNotificationObserver(self.fws)
        file_observer2 = _test_koIFileNotificationObserver(self.fws)

        tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=1, files_per_dir=2)
        for tmpdir in tmpdirs:
            assert self.fws.addObserver( dir_observer, tmpdir, WATCH_DIR, FS_NOTIFY_ALL ) == True
            tmpfiles = tmpdirs[tmpdir].keys()
            tmpfile1 = tmpfiles[0]
            tmpfile2 = tmpfiles[1]
            assert self.fws.addObserver( file_observer1, tmpfile1, WATCH_FILE, FS_NOTIFY_ALL ) == True
            assert self.fws.addObserver( file_observer2, tmpfile2, WATCH_FILE, FS_NOTIFY_ALL ) == True

            try:
                shutil.rmtree(tmpdir)
            except Exception, e:
                print "ERROR:", e
                return

            file_observer1.wait()
            file_observer2.wait()
            dir_observer.wait()
            #print
            #print "tmpfile1:", tmpfile1
            #print "tmpfile2:", tmpfile2
            #print "File 1 Observer:"
            #print file_observer1
            #print "File 2 Observer:"
            #print file_observer2
            #print "Dir Observer:"
            #print dir_observer

            assert( dir_observer.wasNotifiedOn( tmpdir,   FS_DIR_DELETED) )
            assert(     file_observer1.wasNotifiedOn(tmpfile1, FS_FILE_DELETED) )
            assert( not file_observer1.wasNotifiedOn(tmpfile2, FS_NOTIFY_ALL) )
            assert( not file_observer2.wasNotifiedOn(tmpfile1, FS_NOTIFY_ALL) )
            assert(     file_observer2.wasNotifiedOn(tmpfile2, FS_FILE_DELETED) )
            # We may not get the file deleted notifications if thw whole directory was removed
            #assert( dir_observer.wasNotifiedOn( tmpfile1, FS_FILE_DELETED) )
            #assert( dir_observer.wasNotifiedOn( tmpfile2, FS_FILE_DELETED) )

            self.fws.removeObserver( file_observer1, tmpfile1 )
            self.fws.removeObserver( file_observer2, tmpfile2 )
            self.fws.removeObserver( dir_observer, tmpdir )
            file_observer1.clear()
            file_observer2.clear()
            dir_observer.clear()

        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now


class test_loaded_monitoring(unittest.TestCase):
    def setUp(self):
        global POLL_PERIOD
        self.old_poll_period = POLL_PERIOD
        POLL_PERIOD = 5
        self.maintempdir = tempfile.mkdtemp(".FNS", "koFNSDirectory")
        self.fws = _get_testing_file_watcher_service("fws_tests", logging.WARN)

    def tearDown(self):
        global POLL_PERIOD
        self.fws.stopNotificationService()
        shutil.rmtree(self.maintempdir, ignore_errors=True)
        POLL_PERIOD = self.old_poll_period

    #
    # Make sure we can monitor files and directories with multiple observers
    #
    def test_large_number_of_observers(self):
        dir_observers = {}
        file_observers = {}
        delete_directories = {}

        # Setup directories and file
        tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=1, files_per_dir=1)
        for tmpdir in tmpdirs:
            # Create sub-dirs under tmpdir (these will get deleted)
            delete_directories[tmpdir] = _get_temporary_dirs_for_testing(tmpdir, num_dirs=2, files_per_dir=2)

        dir_count = 0
        # Setup the watchers
        for tmpdir in tmpdirs:
            dir_count += 1
            dir_observer = _test_koIFileNotificationObserver(self.fws)
            assert self.fws.addObserver( dir_observer, tmpdir, WATCH_DIR_RECURSIVE, FS_NOTIFY_ALL ) == True
            dir_observers[tmpdir] = [ dir_observer ]
            if (dir_count % 2) == 1:    # Every 2nd dir, make a duplicate
                dup_observer = _test_koIFileNotificationObserver(self.fws)
                assert self.fws.addObserver( dup_observer, tmpdir, WATCH_DIR_RECURSIVE, FS_NOTIFY_ALL ) == True
                dir_observers[tmpdir].append( dup_observer )
            if (dir_count % 3) == 1:    # Every 3rd dir, make a triplicate
                trip_observer = _test_koIFileNotificationObserver(self.fws)
                assert self.fws.addObserver( trip_observer, tmpdir, WATCH_DIR_RECURSIVE, FS_NOTIFY_ALL ) == True
                dir_observers[tmpdir].append( trip_observer )

            tmpfiles = tmpdirs[tmpdir].keys()
            file_count = 0
            for tmpfile in tmpfiles:
                file_count += 1
                file_observer = _test_koIFileNotificationObserver(self.fws)
                assert self.fws.addObserver( file_observer, tmpfile, WATCH_FILE, FS_NOTIFY_ALL ) == True
                file_observers[tmpfile] = [ file_observer ]
                if (dir_count % 2) == 1:    # Every 2nd dir, make a duplicate
                    dup_observer = _test_koIFileNotificationObserver(self.fws)
                    assert self.fws.addObserver( dup_observer, tmpfile, WATCH_FILE, FS_NOTIFY_ALL ) == True
                    file_observers[tmpfile].append( dup_observer )
                if (dir_count % 3) == 1:    # Every 3rd dir, make a triplicate
                    trip_observer = _test_koIFileNotificationObserver(self.fws)
                    assert self.fws.addObserver( trip_observer, tmpfile, WATCH_FILE, FS_NOTIFY_ALL ) == True
                    file_observers[tmpfile].append( trip_observer )

        # Setup is done, now do some modifications and check the notifications
        tmpdir_keys = tmpdirs.keys()
        random.shuffle(tmpdir_keys)

        for tmpdir in tmpdir_keys:
            time.sleep(1)   # Wait for file notification service to catch up
            # Create some sub-directories with some files
            log.debug("\n%s Creating new directories now %s", "*" * 20, "*" * 20)
            created_dirs = _get_temporary_dirs_for_testing(tmpdir, num_dirs=2, files_per_dir=5)

            for dir_observer in dir_observers[tmpdir]:
                #print "\n\ndir_observer:", dir_observer
                dir_observer.wait()
                for created_dir in created_dirs:
                    for filename in created_dirs[created_dir]:
                        assert( dir_observer.wasNotifiedOn( filename, FS_FILE_CREATED) )
                    assert( dir_observer.wasNotifiedOn( created_dir, FS_DIR_CREATED) )
                dir_observer.clear()

            time.sleep(1.0) # Wait a little for all notifications
            for dir_observer in dir_observers[tmpdir]:
                dir_observer.clear()
                time.sleep(0.1) # Wait a little for all notifications

            # Remove some sub-directories
            del_dirs = delete_directories[tmpdir]
            for rmdir in del_dirs:
                for filename in del_dirs[rmdir]:
                    os.unlink(filename)
                    for dir_observer in dir_observers[tmpdir]:
                        dir_observer.wait()
                        assert( dir_observer.wasNotifiedOn( filename, FS_FILE_DELETED) )
                        assert( dir_observer.wasNotifiedOn( rmdir, FS_DIR_MODIFIED) )
                        dir_observer.clear()
                shutil.rmtree(rmdir)
                for dir_observer in dir_observers[tmpdir]:
                    dir_observer.wait()
                    assert( dir_observer.wasNotifiedOn( rmdir, FS_DIR_DELETED) )
                    assert( dir_observer.wasNotifiedOn( tmpdir, FS_DIR_MODIFIED) )
                    dir_observer.clear()

            # Modify some files
            for filename in tmpdirs[tmpdir]:
                file(filename, "w").write("Modified ya!")
                for file_observer in file_observers[filename]:
                    file_observer.wait()
                    assert( file_observer.wasNotifiedOn( filename, FS_FILE_MODIFIED) )
                    file_observer.clear()
                for dir_observer in dir_observers[tmpdir]:
                    dir_observer.wait()
                    assert( dir_observer.wasNotifiedOn( tmpdir, FS_DIR_MODIFIED) )
                    dir_observer.clear()

            time.sleep(0.1) # Little extra time for any other notification

        for tmpdir in tmpdirs:
            for dir_observer in dir_observers[tmpdir]:
                self.fws.removeObserver( dir_observer, tmpdir )
            for filename in tmpdirs[tmpdir]:
                for file_observer in file_observers[filename]:
                    self.fws.removeObserver( file_observer, filename )

        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

    def test_large_number_of_locations(self):
        dir_observers = {}
        file_observers = {}
        delete_directories = {}

        # Setup directories and file
        # Try 100,000 files
        tmpdirs = _get_temporary_dirs_for_testing(self.maintempdir, num_dirs=100, files_per_dir=100)
    
        dir_count = 0
        # Setup the watchers
        for tmpdir in tmpdirs:
            dir_count += 1
            dir_observer = _test_koIFileNotificationObserver(self.fws)
            assert self.fws.addObserver( dir_observer, tmpdir, WATCH_DIR, FS_NOTIFY_ALL ) == True
            dir_observers[tmpdir] = dir_observer

        created_dirs   = {}
        deleted_dirs   = {}
        created_files  = {}
        deleted_files  = {}
        modified_files = {}

        # Setup is done, now do some modifications and check the notifications
        tmpdir_keys = tmpdirs.keys()
        random.shuffle(tmpdir_keys)

        time.sleep(10)   # Wait for file notification service to catch up

        for tmpdir in tmpdir_keys:
            dir_observer = dir_observers[tmpdir]
            # Create some sub-directories
            #log.debug("\n%s Creating new directories now %s", "*" * 20, "*" * 20)

            randint = random.randint(1, 100)
            # 5 % chance of deleting this directory
            if randint <= 5:
                shutil.rmtree(tmpdir)
                deleted_dirs[tmpdir] = dir_observer
                continue

            # 20 % chance of creating new directories
            elif randint <= 25:
                for newdir in _get_temporary_dirs_for_testing(tmpdir, num_dirs=random.randint(0, 5), files_per_dir=0):
                    created_dirs[newdir] = dir_observer

            # 95 % chance of reaching here
            tmpdir_files = tmpdirs[tmpdir].keys()
            random.shuffle(tmpdir_files)
            for tmpfile in tmpdir_files:
                randint = random.randint(1, 100)
                # 25 % chance of deleting the file
                if randint <= 25:
                    os.unlink(tmpfile)
                    deleted_files[tmpfile] = dir_observer
                # 20 % chance of creating new file
                if randint <= 45:
                    fd, newtmpfile = tempfile.mkstemp(dir=tmpdir)
                    os.close(fd)
                    created_files[newtmpfile] = dir_observer
                # 45 % chance of modifying file
                elif randint <= 90:
                    file(tmpfile, "w").write("Update the file")
                    modified_files[tmpfile] = dir_observer
                # 10 % chance of doing nothing
                #else:
                #    # We do nothing
                #time.sleep(0.01)

        time.sleep(10)   # Wait for file notification service to catch up

        # Removed directories
        for tmpdir, dir_observer in deleted_dirs.items():
            assert( dir_observer.wasNotifiedOn( tmpdir, FS_DIR_DELETED) )
        # Modified files
        for tmpfile, dir_observer in modified_files.items():
            assert( dir_observer.wasNotifiedOn( tmpfile, FS_FILE_MODIFIED) )
        # Deleted files
        for tmpfile, dir_observer in deleted_files.items():
            assert( dir_observer.wasNotifiedOn( tmpfile, FS_FILE_DELETED) )
        # Created directories
        #print "created_dirs:"
        #for dirname in created_dirs:
        #    print " ", dirname
        #print dir_observer
        for tmpdir, dir_observer in created_dirs.items():
            #print "Checking dirname:", tmpdir
            assert( dir_observer.wasNotifiedOn( tmpdir, FS_DIR_CREATED) )
        # Created files
        for tmpfile, dir_observer in created_files.items():
            assert( dir_observer.wasNotifiedOn( tmpfile, FS_FILE_CREATED) )

        # Remove our observers
        for tmpdir, dir_observer in dir_observers.items():
            #print "\n\ndir_observer:", dir_observer
            if tmpdir not in deleted_dirs:
                self.fws.removeObserver( dir_observer, tmpdir )
            #else:
            #    # It should already have been removed automatically
    
        assert(self.fws.number_of_observed_locations == 0)   # Should not be watching anything now

#    
#  To be done:
#   remote files        - what file on remote directory, like virtual filesystem
#                       - mounted filesystem, networked directories, webdav?


def _get_test_suite():
    file_monitoring_suite           = unittest.makeSuite(test_monitoring_files)
    file_monitoring_edgecase_suite  = unittest.makeSuite(test_monitoring_files_edge_cases)
    directory_monitoring_suite      = unittest.makeSuite(test_monitoring_directory)
    recursive_directory_monitoring_suite = unittest.makeSuite(test_monitoring_directories_recursively)
    file_and_directory_monitoring_suite  = unittest.makeSuite(test_monitoring_files_and_directories)
    monitoring_with_load_suite      = unittest.makeSuite(test_loaded_monitoring)

    full_suite = unittest.TestSuite((
                                        file_monitoring_suite,
                                        file_monitoring_edgecase_suite,
                                        directory_monitoring_suite,
                                        recursive_directory_monitoring_suite,
                                        file_and_directory_monitoring_suite,
                                        monitoring_with_load_suite,
                                    ))
    return full_suite

def _run_tests(notify_service):
    global notifications_type
    notifications_type = notify_service

    suite = _get_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
    #for i in range(10):
    #    runner.run(suite)

if __name__ == '__main__':
    #_run_tests(TYPE_POLLING)
    _run_tests(TYPE_OS_NOTIFICATIONS)
