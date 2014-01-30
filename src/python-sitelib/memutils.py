import sys
import logging
import gc

log = logging.getLogger("memutils")

#
# Uses the gc module to return a list of accessible objects.
#
# Things to note:
#   1. gc only tracks complex objects, but not atomic types like ints, small strings
#   2. gc.get_referents() will also return these untracked gc objects (e.g. ints)
#
_ignored_object_ids = set()

def _memusage(obj, seen=None, getsizeof=sys.getsizeof):
    obj_id = id(obj)
    if obj_id in seen:
        # already say this object; don't double-count
        # (note that this means we can't have temporary things
        # in the recursion, since they report the same id)
        return 0
    seen.add(obj_id)

    size = 0
    try:
        size = getsizeof(obj, 0)
        size += sum(_memusage(o, seen) for o in gc.get_referents(obj))
    except:
        if obj_id not in _ignored_object_ids:
            # XPCOM type objects do not place nicely, so we ignore these
            # objects.
            if str(type(type(obj))) != "<type 'interface-type'>":
                log.error("error getting size for %r", obj)
                _ignored_object_ids.add(obj_id)
    return size

def memusage(obj):
    """Return the memory usage (in bytes) for the given object."""
    seen = set()
    seen.add(id(seen))
    return _memusage(obj, seen)

def totalusage():
    seen = set()
    seen.add(id(seen))
    return sum(_memusage(obj, seen) for obj in gc.get_objects())

def object_memory_summary(obj):
    """Print out child attributes and their memory consumption."""
    for name in dir(obj):
        if name.startswith("__"):
            continue
        child_obj = getattr(obj, name)
        if child_obj is not None:
            usage = memusage(child_obj)
            print "%-40s %6dKb" % (name, usage / 1024)
