/**
 * Copyright (c) 2006,2007 ActiveState Software Inc.
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Contributors:
 *   David Ascher <davida@activestate.com>
 *   Shane Caraveo <shanec@activestate.com>
 */

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*- */

if (typeof(xtk)=='undefined') {
    var xtk = {};
}

/*
 * Base class for controllers.  Subclasses need only implement
 * is_<command>_enabled() and do_<command>() functions for each
 * command to get basic controller functionality.

 * If a command does not have an is_<command>_enabled() function,
 * it will always be enabled.

 * If controllers need to change the response to supportsCommand() for
 * particular commands (as in checkbox commands), they can implement
 * is_<command>_supported() for those commands.
 */
xtk.Controller = function Controller() {}
xtk.Controller.prototype = {

supportsCommand: function(command) {
    var result;
    var query = "is_" + command + "_supported";
    if (query in this) {
        result = this[query]();
    } else {
        var doer = "do_" + command;
        result = doer in this;
    }
    return result;
},

isCommandEnabled: function(command) {
    var result;
    var query = "is_" + command + "_enabled";
    if (query in this) {
        result = this[query]();
    } else {
        var doer = "do_" + command;
        result = doer in this;
    }
    return result;
},

doCommand: function(command) {
    var func = "do_" + command;
    if (func in this) {
        this[func]();
    }
},

onEvent: function(event) {
}

};

