import functools
import os.path

import watchdog.observers.api
from watchdog.utils import platform

# Monkey-patch event queueing to emit additional events for compatibility with
# Komodo's API. I patched watchdog instead of the Komodo service because some of
# the watchdog backends behave differently. 
# (see https://github.com/gorakhargosh/watchdog/issues/72)

watchdog.observers.api.EventEmitter.queue_event_without_patch = \
    watchdog.observers.api.EventEmitter.queue_event

@functools.wraps(watchdog.observers.api.EventEmitter.queue_event)
def queue_event_with_patch(self, event):
    # Pro tip: Breaking/printing here tells you which events the backend queues
    self.queue_event_without_patch(event)

    extra_events = []

    # Emit a DIR_MODIFIED event with every FILE_MODIFIED event:
    if isinstance(event, watchdog.events.FileModifiedEvent):
        src_path = os.path.dirname(event.src_path)
        extra_events.append(watchdog.events.DirModifiedEvent(src_path))

    try:
        is_inotify = isinstance(self, watchdog.observers.inotify.InotifyEmitter)
    except AttributeError:
        is_inotify = False

    if is_inotify:
        # ... emit a DIR_MODIFIED with every FILE_MOVED event:
        if isinstance(event, watchdog.events.FileMovedEvent):
            src_path = os.path.dirname(event.dest_path)
            extra_events.append(watchdog.events.DirModifiedEvent(src_path))

        # ... emit a DIR_MODIFIED with every FILE_DELETED, DIR_CREATED and
        # DIR_DELETED event:
        if isinstance(event, (watchdog.events.FileDeletedEvent, 
                              watchdog.events.DirCreatedEvent,
                              watchdog.events.DirDeletedEvent,)):
            src_path = os.path.dirname(event.src_path)
            extra_events.append(watchdog.events.DirModifiedEvent(src_path))

    for extra_event in extra_events:
        self.queue_event_without_patch(extra_event)


watchdog.observers.api.EventEmitter.queue_event = queue_event_with_patch

