/* Copyright (c) 2000-2007 ActiveState Software Inc.
 */

var applyToObject = {};

(function() {
    this.var1 = "variable 1";
    this.var2 = "variable 2";
    var finder = {
                    searchString: "",
                    direction: 0
                 };
    
    this.log = function(msg) {
        dump("LOG: " + msg + "\n");
    }
}).apply(applyToObject);

// Was failing with observe becoming a member of ns!
var ns = {};
(function() {
    this.name = "Test";
    var willQuitListener = {
        observe: function(subject, topic, data) { }
    }
}).apply(ns);


(function() {
  function testing_apply() {}
}).apply(); // apply into the global namespace

