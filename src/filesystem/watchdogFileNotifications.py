import logging
import os.path
import time
import threading

from pathtools.path import parent_dir_path
import watchdog.events
import watchdog.observers
import watchdog.observers.api

from osFileNotificationUtils import * # FIXME

# Monkey patch watchdog with Komodo API modifications
import watchdog_patches

# watch_type - Type of watch to perform (used in addObserver)
WATCH_FILE = 0
WATCH_DIR = 1
WATCH_DIR_RECURSIVE = 2

log = logging.getLogger("watchdogFileNotifications")
#log.setLevel(logging.DEBUG)

class FileSystemPatternEventHandler(watchdog.events.PatternMatchingEventHandler):

    _event_map = {
        watchdog.events.DirCreatedEvent: FS_DIR_CREATED,
        watchdog.events.DirDeletedEvent: FS_DIR_DELETED,
        watchdog.events.DirModifiedEvent: FS_DIR_MODIFIED,
        watchdog.events.FileCreatedEvent: FS_FILE_CREATED,
        watchdog.events.FileDeletedEvent: FS_FILE_DELETED,
        watchdog.events.FileModifiedEvent: FS_FILE_MODIFIED,
    }

    def __init__(self, observer_monitor, flags, patterns=None):
        super(FileSystemPatternEventHandler, self).__init__(patterns=patterns)
        self.observer_monitor = observer_monitor
        self.flags = flags
        self._lock = threading.Lock()

    def has_flags(self, flags):
        return self.flags & flags

    def notify_observer_monitor(self, path, flags):
        with self._lock:
            self.observer_monitor.notifyChanges({path: flags})

    def on_any_event(self, event):
        flag = self._event_map.get(event.__class__)
        if flag and self.has_flags(flag):
            self.notify_observer_monitor(event.src_path, flag)
        super(FileSystemPatternEventHandler, self).on_any_event(event)

    def on_moved(self, event):
        _event_map = {
            watchdog.events.DirMovedEvent: [FS_DIR_DELETED, FS_DIR_CREATED],
            watchdog.events.FileMovedEvent: [FS_FILE_DELETED, FS_FILE_CREATED],
        }
        flags = _event_map.get(event.__class__)
        if not flags:
            return
        for flag, path in zip(flags, (event.src_path, event.dest_path)):
            if self.has_flags(flag):
                self.notify_observer_monitor(path, flag)



class WatchdogFileNotificationService(object):
    """An implementation of koIFileNotificationService based on watchdog."""

    def __init__(self):
        self._observer = watchdog.observers.Observer()
        self._handler_and_watch_map = {}

    def _get_watch_path_and_patterns(self, path):
        # If path points to a file, return its parent and patterns to match the
        # file. Else return path and None.
        # FIXME use realpath to follow symlinks (necessary?)- but make sure
        # FileSystemPatternEventHandler reports the original path.
        watch_path = os.path.abspath(path)
        patterns = None
        if not os.path.isdir(watch_path):
            patterns = (watch_path,)
            watch_path = os.path.dirname(watch_path)
        return watch_path, patterns

    def addObserver(self, ko_observer, path, watch_type, flags):
        log.info('addObserver: %d %r', flags, path)
        watch_path, patterns = self._get_watch_path_and_patterns(path)
        if not os.path.exists(watch_path):
            raise ValueError("Neither path nor its parent is a directory.")
        recursive = watch_type == WATCH_DIR_RECURSIVE
        monitor = ObserverMonitor(ko_observer, path, watch_type, flags, log)
        event_handler = FileSystemPatternEventHandler(monitor, flags,
            patterns=patterns)
        watch = self._observer.schedule(event_handler, watch_path, recursive)
        self._handler_and_watch_map[(ko_observer, path)] = event_handler, watch
        return True

    def removeObserver(self, ko_observer, path):
        log.info('removeObserver: %s', path)
        try:
            handler, watch = self._handler_and_watch_map.pop((ko_observer, path))
            # If this is the last handler of the watch, remove the emitter, the
            # watch, and all its handlers. Remove just the handler else.
            last_handler = len(self._observer._get_handlers_for_watch(watch)) == 1
            if last_handler:
                self._observer.unschedule(watch)
            else:
                self._observer.remove_handler_for_watch(handler, watch)
        except KeyError:
            # The watch doesn't exist anymore - must have been already removed.
            return False
        return True

    @property
    def number_of_observed_locations(self):
        return len(self._handler_and_watch_map)

    def startNotificationService(self):
        self._observer.start()
        return True

    def stopNotificationService(self):
        # Shut down all the observer monitors; this prevents attempts to notify
        # changes after the target thread has gone away.
        for handler, _ in self._handler_and_watch_map.values():
            handler.observer_monitor.shutdown()
        self._observer.stop()
        log.debug("Stopped notification service")
        return True

    def waitTillFinishedRun(self):
        # Wait for all events to reach the queue and the queue to be processed.
        # TODO I sometimes see a heisenbug in test_file_notification_on_write,
        # that can be fixed by sleeping 3 seconds or more here. Looks like
        # FSEvents being *slow*.
        time.sleep(1.0)
        self._observer.event_queue.join()

    @property
    def available(self):
        return True

    def dump(self):
        print(self._handler_and_watch_map)
