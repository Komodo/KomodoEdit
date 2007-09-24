#!/usr/bin/env python

"""Scrap pieces of code from Code Intel development that I don't want to
delete just yet.
"""


class _PriorityQueue:
    """A specialized priority queue for holding items with an 'id' attribute.

    The queue is specialized in the following ways:
    - It maintains a prioritized order of items (lowest priority value
      first, i.e. priority==1 comes before priority==2) using the
      inserted item's comparison.
    - It uses the 'id' attribute on inserted items to support .remove_id()
      and to ensure that an item is never in the list twice. Subsequent
      adds will just re-order the item with the new priority.
    """
    # Dev Notes:
    # - This class is a modification if Python's std Queue.Queue class:
    #   - drop maxsize related stuff
    #   - calls are always blocking
    #   - add .prepend() and .remove_id() methods and re-ordering sematics
    def __init__(self):
        import thread
        self._init()
        self.mutex = thread.allocate_lock()
        self.esema = thread.allocate_lock() # if acquired, then queue is empty
        self.esema.acquire()

    def put(self, priority, item):
        """Put an item into the queue and the given priority."""
        log.debug("in _PriorityQueue.put, acquiring mutex")
        self.mutex.acquire()
        log.debug("in _PriorityQueue.put, acquired mutex")
        try:
            was_empty = self._empty()
            self._put(priority, item)
            # If we fail before here, the empty state has
            # not changed, so we can skip the release of esema
            if was_empty:
                log.debug("in _PriorityQueue.put, releasing esema")
                self.esema.release()
        finally:
            # Catching system level exceptions here (RecursionDepth,
            # OutOfMemory, etc) - so do as little as possible in terms
            # of Python calls.
            log.debug("in _PriorityQueue.put, releasing mutex")
            self.mutex.release()

    def get(self):
        """Remove and return an item (and its priority) from the queue.

        Block if necessary until an item is available.
        """
        log.debug("in _PriorityQueue.get, acquiring esema")
        self.esema.acquire()
        log.debug("in _PriorityQueue.get, acquired esema")
        log.debug("in _PriorityQueue.get, acquiring mutex")
        self.mutex.acquire()
        log.debug("in _PriorityQueue.get, acquired mutex")
        release_esema = 1
        try:
            item = self._get()
            # Failure means empty state also unchanged - release_esema
            # remains true.
            release_esema = not self._empty()
        finally:
            if release_esema:
                log.debug("in _PriorityQueue.get, releasing esema")
                self.esema.release()
            log.debug("in _PriorityQueue.get, releasing mutex")
            self.mutex.release()
        return item

    def remove_id(self, id):
        """Remove all current requests with the given id.

        Does not return anything.
        """
        log.debug("in _PriorityQueue.remove_id, acquiring esema")
        if not self.esema.acquire(0): # do not block to acquire lock
            # return if could not acquire: means queue is empty and
            # therefore do not have any items to remove
            log.debug("in _PriorityQueue.remove_id, did not acquire esema")
            return
        log.debug("in _PriorityQueue.remove_id, acquired mutex")
        log.debug("in _PriorityQueue.remove_id, acquiring mutex")
        self.mutex.acquire()
        release_esema = 1
        try:
            self._remove_id(id)
            # Failure means empty state also unchanged - release_esema
            # remains true.
            release_esema = not self._empty()
        finally:
            if release_esema:
                log.debug("in _PriorityQueue.remove_id, releasing esema")
                self.esema.release()
            log.debug("in _PriorityQueue.remove_id, releasing mutex")
            self.mutex.release()

    #---- Override these methods to implement other queue organizations
    # (e.g. stack or priority queue). These will only be called with
    # appropriate locks held.

    # Initialize the queue representation
    def _init(self):
        self.queue = []
        # Dict for fast lookup of ids, presense of key indicates an item
        # with that ID is in the queue.
        self._ids = {}

    # Check whether the queue is empty
    def _empty(self):
        return not self.queue

    # Put a new item in the queue.
    # If the same item (judging by its 'id' attribute) is already in the
    # queue then remove it first (i.e. this re-insert is probably just
    # changing its priority).
    def _put(self, priority, item):
        if item.id in self._ids:
            for index in range(len(self.queue)):
                if self.queue[index][2].id == item.id:
                    del self.queue[index]
                    break
        else:
            self._ids[item.id] = 1
        # Insert this triplet (priority, time, item) to ensure that:
        # - higher priority items are first
        # - items with the same priority are sort based on when they were
        #   inserted
        bisect.insort(self.queue, (priority, time.time(), item))

    # Get an item from the queue
    def _get(self):
        priority, t, item = self.queue[0]
        del self.queue[0]
        del self._ids[item.id]
        return priority, item

    # Remove the item with the given id, if it is in the queue (there can
    # be only one).
    def _remove_id(self, id):
        if id in self._ids:
            for index in range(len(self.queue)):
                if self.queue[index][2].id == item.id:
                    del self.queue[index]
                    break
            del self._ids[id]
