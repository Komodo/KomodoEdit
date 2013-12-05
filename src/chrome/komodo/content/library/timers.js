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

/* objectTimers allows you to set a window timeout or timeinterval
   on a method of an instance of an object.  This works with js
   objects or xbl objects :)

   example usage (within a class)

someobject.prototype.startInterval() {
    this._repeater = new ko.objectTimer(this,this.doRepeater,['test string',12345]);
    this._repeater.startInterval(20);
}

someobject.prototype.stopInterval() {
    if (!this._repeater) return;
    this._repeater.stopInterval();
    this._repeater.free();
    this._repeater = null;
}

someobject.prototype.doRepeater(tag, value) {
    // do something here.
}


*/

if (typeof(ko) == 'undefined') {
    var ko = {};
}

ko.objectTimer = function objectTimer(instance, func, args) {
    this.timer = 200;
    this.instance = instance;
    this.func = func;
    this.args = args;
    this.running = false;
    this.timeout = null;
    this.interval = null;
}

ko.objectTimer.prototype.free = function() {
    // backwards compat for existing code that calls this
}

ko.objectTimer.prototype.monitor  = function() {
    this.func.apply(this.instance, this.args);
}

ko.objectTimer.prototype.startTimeout  = function(timer) {
    if (this.running) return;
    this.timer = timer;
    try {
        var self = this;
        this.timeout = window.setTimeout(function() {self.monitor()}, this.timer);
        return;
    } catch(e) {
        log.exception(e,'objectTimer.startTimeout exception');
        this.running = false;
        return;
    }
    this.running = true;
}

ko.objectTimer.prototype.stopTimeout  = function() {
    if (!this.timeout) return;
    window.clearTimeout(this.timeout);
    this.timeout = null;
    this.running = false;
}

ko.objectTimer.prototype.stop  = function(timer) {
    this.stopTimeout();
    this.stopInterval();
}

ko.objectTimer.prototype.startInterval  = function(timer) {
    if (this.running) return;
    this.timer = timer;
    try {
        var self = this;
        this.interval = window.setInterval(function() {self.monitor()}, this.timer);
    } catch(e) {
        log.exception(e,'objectTimer.startInterval exception');
        this.running = false;
        return;
    }
    this.running = true;
}

ko.objectTimer.prototype.stopInterval  = function() {
    if (!this.interval) return;
    window.clearInterval(this.interval);
    this.interval = null;
    this.running = false;
}
