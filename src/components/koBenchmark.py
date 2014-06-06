#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Exposes the benchmark module via XPCOM.
"""

import benchmark

from xpcom import components

class koBenchmark(object):
    _com_interfaces_ = [components.interfaces.koIBenchmark,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "{13955859-9f4a-b34b-95b4-8b08ebadd17f}"
    _reg_contractid_ = "@activestate.com/koBenchmark;1"
    _reg_desc_ = "Komodo XPCOM benchmark service"

    def __init__(self):
        benchmark.initialise()
        obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService)
        obsSvc.addObserver(self, 'xpcom-shutdown', False)

    def observe(self, subject, topic, data):
        if topic == "xpcom-shutdown":
            self.display()

    def startTiming(self, name):
        return benchmark.startTiming(name)

    def endTiming(self, name):
        return benchmark.endTiming(name)

    def addTiming(self, name, duration):
        return benchmark.addTiming(name, duration)

    def addEvent(self, name):
        return benchmark.addEvent(name)

    def accumulate(self, name, duration):
        return benchmark.accumulate(name, duration)

    def addEventAtTime(self, name, t):
        return benchmark.addEventAtTime(name, t)

    def display(self):
        return benchmark.display()

