
# A Komodo Python memory reporter, used to populate the "about:memory" page.

import os
import sys
import threading
import logging

from xpcom import components

log = logging.getLogger("koMemoryReporter")
#log.setLevel(logging.DEBUG)

Ci = components.interfaces
Cc = components.classes

class KoMemoryReporter:
    # Support Mozilla 24 and 31 (name change)
    nsIMemoryReporter = Ci.nsIMemoryReporter
    if "nsIMemoryMultiReporter" in Ci.keys():
        nsIMemoryReporter = Ci.nsIMemoryMultiReporter

    _com_interfaces_ = [nsIMemoryReporter,
                        Ci.nsIObserver]
    _reg_clsid_ = "{c75e5746-50ab-49af-9ecd-b66388a0522c}"
    _reg_contractid_ = "@activestate.com/koMemoryReporter;1"
    _reg_desc_ = "Komodo Memory Reporter"
    _reg_categories_ = [
         ("komodo-delayed-startup-service", "KoMemoryReporter"),
    ]

    def __init__(self):
        # Register ourself with the memory manager.
        if "nsIMemoryMultiReporter" not in Ci.keys():
            # Mozilla 31
            Cc["@mozilla.org/memory-reporter-manager;1"]\
              .getService(Ci.nsIMemoryReporterManager)\
              .registerStrongReporter(self)
        else:
            # Mozilla 24
            Cc["@mozilla.org/memory-reporter-manager;1"]\
              .getService(Ci.nsIMemoryReporterManager)\
              .registerMultiReporter(self)

    def observe(self, subject, topic, data):
        pass

    ##
    # nsIMemoryReporter
    name = "Komodo"
    explicitNonHeap = 0

    def collectReports(self, reportHandler, closure):
        log.info("collectReports")

        process = ""
        kind_heap = components.interfaces.nsIMemoryReporter.KIND_HEAP
        kind_other = components.interfaces.nsIMemoryReporter.KIND_OTHER
        units_bytes = components.interfaces.nsIMemoryReporter.UNITS_BYTES
        units_count = components.interfaces.nsIMemoryReporter.UNITS_COUNT

        reportHandler.callback(process,
                               "komodo python active threads",
                               kind_other,
                               units_count,
                               threading.activeCount(), # amount
                               "The number of active Python threads that are currently running.", # tooltip description
                               closure)

        import gc
        gc.collect()
        gc_objects = gc.get_objects()

        import memutils
        total = memutils.memusage(gc_objects)

        # Get the Python memory reporters, generate reports and find out how
        # much memory they are using - and deduct it from the total.
        catman = components.classes["@mozilla.org/categorymanager;1"].\
                        getService(components.interfaces.nsICategoryManager)
        category = 'python-memory-reporter'
        names = catman.enumerateCategory(category)
        while names.hasMoreElements():
            nameObj = names.getNext()
            nameObj.QueryInterface(components.interfaces.nsISupportsCString)
            name = nameObj.data
            cid = catman.getCategoryEntry(category, name)
            log.info("Generating report for %r: %r", name, cid)
            try:
                reporter = components.classes[cid].\
                    getService(components.interfaces.koIPythonMemoryReporter)
                total -= reporter.reportMemory(reportHandler, closure)
            except Exception, e:
                log.exception("Unable to report memory for %r: %r", name, cid)

        reportHandler.callback(process,
                               "explicit/python/unclassified-objects",
                               kind_heap,
                               units_bytes,
                               total, # amount
                               "Total bytes used by Python objects.",
                               closure)

        reportHandler.callback(process,
                               "komodo python objects",
                               kind_other,
                               units_count,
                               len(gc_objects), # amount
                               "Total number of referenced Python objects.",
                               closure)

        koViewSvc = components.classes["@activestate.com/koViewService;1"] \
                        .getService(components.interfaces.koIViewService)
        view_count, view_leak_count = koViewSvc.getReferencedViewCount()
        reportHandler.callback(process,
                               "komodo koIView instances", # name
                               kind_other,
                               units_count,
                               view_count, # amount
                               "The number of koIView instances being referenced.", # tooltip description
                               closure)
        if view_leak_count:
            reportHandler.callback(process,
                                   "komodo koIView leaked instances", # name
                                   kind_other,
                                   units_count,
                                   view_leak_count, # amount
                                   "The number of koIView instances referencing .", # tooltip description
                                   closure)

        koDocumentSvc = components.classes["@activestate.com/koDocumentService;1"] \
                        .getService(components.interfaces.koIDocumentService)
        reportHandler.callback(process,
                               "komodo koIDocument instances", # name
                               kind_other,
                               units_count,
                               len(koDocumentSvc.getAllDocuments()), # amount
                               "The number of koIDocument instances being referenced.", # tooltip description
                               closure)

        koFileSvc = components.classes["@activestate.com/koFileService;1"] \
                        .getService(components.interfaces.koIFileService)
        reportHandler.callback(process,
                               "komodo koIFile instances", # name
                               kind_other,
                               units_count,
                               len(koFileSvc.getAllFiles()), # amount
                               "The number of koIFileEx instances being referenced.", # tooltip description
                               closure)

