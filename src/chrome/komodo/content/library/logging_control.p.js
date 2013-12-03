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

var gLoggerNames;
var gLoggingService;
var _loggingObserver;

function loggingControl_OnLoad() {
    gLoggingService = Components.classes["@activestate.com/koLoggingService;1"].
                        getService(Components.interfaces.koILoggingService);

    document.getElementById('loggers').treeBoxObject.view = gLoggerView;

    gLoggerView.loggernames= gLoggingService.getLoggerNames(new Object());
    gLoggerView.setRowCount(gLoggerView.loggernames.length);

    _loggingObserver = new loggingObserver();
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                            getService(Components.interfaces.nsIObserverService);
    observerSvc.addObserver(_loggingObserver, 'add_logger',false);
}

function loggingControl_OnUnload()
{
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                            getService(Components.interfaces.nsIObserverService);
    observerSvc.removeObserver(_loggingObserver, 'add_logger');

}
function loggingObserver() {
}

loggingObserver.prototype.constructor = ko.logging.Logger;

loggingObserver.prototype.observe = function(subject, topic, data) {
    switch (topic) {
        case 'add_logger':
            gLoggerView.loggernames.push(data);
            gLoggerView.setRowCount(gLoggerView.loggernames.length);
            break;
    }
}

var gLoggerView = ({
    // nsITreeView
    rowCount : 0,
    getRowProperties : function(i, prop) {},
    getColumnProperties : function(index, prop) {},
    getCellProperties : function(index, prop) {},
    isContainer : function(index) {return false;},
    isSeparator : function(index) {return false;},
    setTree : function(out) { this.tree = out; },
    getCellText : function(i, column) {
        switch(column.id){
        case "logger":
            var name = this.loggernames[i];
            if (name == '') { return '<root>' };
            return name;
            break;
        case "effectivelevel":
            var level = ko.logging.getLogger(this.loggernames[i]).getEffectiveLevel();
            if (level == ko.logging.LOG_DEBUG) { return "DEBUG (10)"; }
            if (level == ko.logging.LOG_INFO) { return "INFO (20)"; }
            if (level == ko.logging.LOG_WARN) { return "WARN (30)"; }
            if (level == ko.logging.LOG_ERROR) { return "ERROR (40)"; }
            if (level == ko.logging.LOG_CRITICAL) { return "CRITICAL (50)"; }
            return String(level);
            break;
        case "level":
            var level = ko.logging.getLogger(this.loggernames[i]).level;
            if (level == ko.logging.LOG_NOTSET) { return "<unset>"; }
            if (level == ko.logging.LOG_DEBUG) { return "DEBUG (10)"; }
            if (level == ko.logging.LOG_INFO) { return "INFO (20)"; }
            if (level == ko.logging.LOG_WARN) { return "WARN (30)"; }
            if (level == ko.logging.LOG_ERROR) { return "ERROR (40)"; }
            if (level == ko.logging.LOG_CRITICAL) { return "CRITICAL (50)"; }
            return String(level);
            break;
        default:
            return "XXX in " + column.id + " and " + i;
        }
        return "";
    },
    getImageSrc : function() {return null;},
    isSorted : function() {return true;},
    performAction : function(action) {},
    cycleHeader : function(index) {},
    selectionChanged : function() {},
    getSelectedItem : function() {
        var i = this.selection.currentIndex;
        return this.loggernames[i];
    },

    // Private stuff
    loggernames : [],
    setRowCount : function(rowCount) {
        this.rowCount = rowCount;
        this.tree.beginUpdateBatch();
        this.tree.rowCountChanged(0, this.rowCount);
        this.tree.invalidate();
        this.tree.endUpdateBatch();
    }
});

function setLevel(thing, level) {
    var i, f;
    f = gLoggerView.getSelectedItem();
    ko.logging.getLogger(f).setLevel(Number(level));
    gLoggerView.selectionChanged();
}

