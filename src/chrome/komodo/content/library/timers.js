/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* objectTimers allows you to set a window timeout or timeinterval
   on a method of an instance of an object.  This works with js
   objects or xbl objects :)

   example usage (within a class)

someobject.prototype.startInterval() {
    this._repeater = new objectTimer(this,this.doRepeater,['test string',12345]);
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

var objectTimer = ko.objectTimer;
