/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}
ko.trace = {};
(function() {
/*
 * this file contains general debugging functionality we use
 * during development.  None of these functions should be used
 * in a release build, and this file should not be included in
 * release builds.
 */

this.Trace = function Trace() {
    // initialize timeline
    this.timelineService = null;
    if ("@mozilla.org;timeline-service;1" in Components.classes) {
        try {
            this.timelineService =
                Components.classes["@mozilla.org;timeline-service;1"].getService(Components.interfaces.nsITimelineService);
            // and check it is actually operatiing (ie, enabled)
            this.timelineService.indent();
            this.timelineService.outdent();
        }
        catch (ex) { this.timelineService = null }
    }
}
this.Trace.prototype.constructor = this.Trace;
this.Trace.prototype = {
    myPerfTimer: {},
    perfLog: 0,
    perfTimer: function perfTimer(name, title, reset)
    {
        if (!this.perfLog) {
            this.perfLog = ko.logging.getLoggingMgr().getLogger('perf');
            this.perfLog.setLevel(ko.logging.LOG_DEBUG);
        }
        if (typeof reset == 'undefined' || !reset) {
            reset = false;
        }
        var timenow = new Date();
        if (reset || this.myPerfTimer[name] == 0) this.myPerfTimer[name] = timenow;
        var timediff = timenow.getTime()-this.myPerfTimer[name].getTime();
        //dump("[" + name + ":"+title+"] = "+timediff + " ms\n");
        this.perfLog.info("[" + name + ":"+title+"] = "+timediff + " ms");
        this.myPerfTimer[name] = timenow;
    },
    timestamp: function timestamp(name, title)
    {
        if (this.timelineService)
            this.timelineService.mark("perfTimer: " + name + ": " + title)
    },

    startTimer: function startTimer(name)
    {
        if (this.timelineService) {
            this.timelineService.startTimer(name);
        }
    },
    stopTimer: function stopTimer(name)
    {
        if (this.timelineService) {
            try {
                this.timelineService.stopTimer(name);
            } catch (e) {
                log.warn('Error calling timelineService.stopTimer('+ name + ')');
            }
        }
    },
    resetTimer: function resetTimer(name)
    {
        if (this.timelineService) {
            try {
                this.timelineService.resetTimer(name);
            } catch (e) {
                log.warn('Error calling timelineService.resetTimer('+ name + ')');
            }
        }
    },
    markTimer: function markTimer(name, text)
    {
        if (this.timelineService) {
            if (typeof(text) == 'undefined' || text == '') {
                this.timelineService.markTimer(name);
            } else {
                try {
                    this.timelineService.markTimerWithComment(name, text);
                } catch (e) {
                    this.timelineService.markTimerWithComment(name + '-' + text);
                }
            }
        }
    },
    mark: function mark(text)
    {
        if (this.timelineService) {
            this.timelineService.mark(text);
        }
    },
    indent: function indent(text)
    {
        if (this.timelineService) {
            this.timelineService.indent(text);
        }
    },
    outdent: function outdent(text)
    {
        if (this.timelineService) {
            this.timelineService.outdent(text);
        }
    },
    enter: function enter(text)
    {
        if (this.timelineService) {
            this.timelineService.enter(text);
            this.timelineService.startTimer(text);
        }
    },
    leave: function leave(text)
    {
        if (this.timelineService) {
            this.timelineService.stopTimer(text);
            this.markTimer(text);
            this.timelineService.resetTimer(text);
            this.timelineService.leave(text);
        }
    }
};

var _tracer = null;
this.get = function() {
    if (!_tracer)
        _tracer = new ko.trace.Trace();
    return _tracer;
}

}).apply(ko.trace);

