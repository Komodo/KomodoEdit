/* Copyright (c) 2000-2006 ActiveState Software Inc. */

if (typeof(ko) == 'undefined') {
    ko = {};
}

ko.o1 = {
    arg1: 1,
    arg2: 2,
    makeArgsEqual: function() {
        this.arg1 = this.arg2;
    },
    showThis: function() {
        alert(this);
    }
};

ko.o2 = {};
ko.o2.arg1 = 1;
ko.o2.arg2 = 2;
ko.o2.makeArgsEqual = function() {
    this.arg1 = this.arg2;
}
ko.o2.showThis = function() {
    alert(this);
}

ko.f1 = function f1() {
    this.arg1 = 1;
    this.arg2 = 2;
}
ko.f1.prototype.makeArgsEqual = function() {
    this.arg1 = this.arg2;
}
ko.f1.prototype.showThis = function() {
    alert(this);
}
