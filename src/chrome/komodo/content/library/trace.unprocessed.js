/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

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

