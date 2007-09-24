import os, sys

pid = os.getpid()

if sys.platform.startswith("win"):
    import win32pdh

    class Win32PDHCounter:
        """Interface to Win32 PDH API for the given process prefix."""
        def __init__(self, pid):
            self.my_process_prefix = self.getProcessPrefix(pid)
            self.counters = {}
            self.query = win32pdh.OpenQuery()
    
        def __del__(self):
            if win32pdh:
                win32pdh.CloseQuery(self.query)
        
        def getProcessPrefix(self, pid):
            object = "Process"
            items, instances = win32pdh.EnumObjectItems(None,None,object, win32pdh.PERF_DETAIL_WIZARD)
            # Need to track multiple instances of the same name.
            instance_dict = {}
            for instance in instances:
                try:
                    instance_dict[instance] = instance_dict[instance] + 1
                except KeyError:
                    instance_dict[instance] = 0
                
            # Bit of a hack to get useful info.
            item = "ID Process"
            for instance, max_instances in instance_dict.items():
                for inum in xrange(max_instances+1):
                    hq = win32pdh.OpenQuery()
                    try:
                        hcs = []
                        path = win32pdh.MakeCounterPath( (None,object,instance, None, inum, item) )
                        hc = win32pdh.AddCounter(hq, path)
                        try:
                            win32pdh.CollectQueryData(hq)
                            type, val = win32pdh.GetFormattedCounterValue(hc, win32pdh.PDH_FMT_LONG)
                            if val == pid:
                                return "\\".join(path.split("\\")[:-1]) + "\\"
                        finally:
                            win32pdh.RemoveCounter(hc)
                    finally:
                        win32pdh.CloseQuery(hq)
    
        def addCounter(self, counter):
            counter_use = counter
            if counter.find("\\")==-1:
                counter_use = self.my_process_prefix + counter
            hc = win32pdh.AddCounter(self.query, counter_use)
            self.counters[counter] = hc
    
        def getCounterValue(self, counter):
            hc = self.counters[counter]
            return win32pdh.GetFormattedCounterValue(hc, win32pdh.PDH_FMT_DOUBLE)[1]
    
        def collect(self):
            win32pdh.CollectQueryData(self.query)


    pdhCounter = Win32PDHCounter(pid)
    pdhCounter.addCounter("Working Set")
    
    def my_process_memory():
        global pdhCounter
        pdhCounter.collect()
        return pdhCounter.getCounterValue("Working Set")/1024

    _pdhCounterMap = {}
    def process_memory(pid):
        if pid not in _pdhCounterMap:
            pdhCounter = Win32PDHCounter(pid)
            pdhCounter.addCounter("Working Set")
            _pdhCounterMap[pid] = pdhCounter
        else:
            pdhCounter = _pdhCounterMap[pid]
        pdhCounter.collect()
        return pdhCounter.getCounterValue("Working Set")/1024

    def getpidsforprocess(processname):
        import win32pdh, win32pdhutil
        win32pdh.EnumObjects(None, None, 0, 1)  # refresh internal cache
        pids = win32pdhutil.FindPerformanceAttributesByName(processname,
                                                            "Process",
                                                            "ID Process")
        return pids
        
    def kill(pid):
        import win32api
        # constants pulled from win32con to save memory
        PROCESS_TERMINATE = 1 # from win32con
        handle = win32api.OpenProcess(PROCESS_TERMINATE, 0,pid)
        win32api.TerminateProcess(handle,0)
        win32api.CloseHandle(handle)
    

else:

    def my_process_memory():
        mem = int(os.system("ps -p %s -o rss -h" % pid).read())

    def process_memory(pid):
        mem = int(os.system("ps -p %s -o rss -h" % pid).read())

    def getpidsforprocess(processname):
        lines = os.system('ps -o pid -o fname -h | grep "\b%s\b"').readlines()
        pids = [int(line.strip().split[0]) for line in lines]
        return pids
    
    def kill(pid):
        os.kill(pid)

def memoryrepr(kb):
    if kb > 1000:
        mb = kb / 1024.
        return "%3.1f M" % mb
    return "%3d k" % kb

_imported_modules = {}
module_tree = {}
current_module = module_tree
def _memory_import(name, *args, **kw):
    global current_module
    start = int(my_process_memory())
    current_module[name] = {}
    orig = current_module
    current_module = current_module[name]
    mod = _old_import(name, *args, **kw)
    end = int(my_process_memory())
    realname = mod.__name__
    if name.startswith(realname):
        realname = name
    mem = end-start
    if mem:
        # Write an entry to the timeline service????
        #logger.info("%s\t%s" % (realname, memoryrepr(mem)))
        current_module['memory'] = memoryrepr(mem)
    current_module = orig
    if not current_module[name]:
        del current_module[name]
    return mod


#import __builtin__
#_old_import = __builtin__.__import__
#__builtin__.__import__ = _memory_import

# ... subsequent imports will result in their memory load being tracked

#import pprint
#pprint.pprint(module_tree)
