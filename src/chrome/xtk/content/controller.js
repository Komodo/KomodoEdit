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

/* * *
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

