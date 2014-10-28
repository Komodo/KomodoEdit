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

/**

 Hyperlink handling for Komodo buffers. These are enabled/disabled using
 the "hyperlinksEnabled" preference.
 
 The idea of a hyperlink is that when the user is hovering over a particular
 point of the editor, an interactable indication can be shown to the user that
 there is something of interest at this point.
 
 The hyperlink will *only* be show when the user holds down the Ctrl key (or
 Meta key on the Mac). Whilst Ctrl is being held down, where-ever the mouse
 moves, the editor text under the mouse will be checked to see if it has a
 hyperlink, if it does it will become highlighted in the editor.

 If the user left-clicks on the hyperlink, then a hyperlink action
 will be performed (example: opening the target text in a browser).

 The main hyperlink elements are:
 1) the view (scimoz), for management of the hyperlinks (mousemove, etc...)
 2) the handlers (multiples), to show/remove individual hyperlinks
 3) the hyperlink itself, marking an individual hyperlink instance
 
 All handlers must inherit from {ko.hyperlinks.BaseHandler} and can be
 added/removed using the ko.hyperlinks API.

 */

if (typeof(ko)=='undefined') {
    var ko = {};
}
ko.hyperlinks = {};

(function() {

    /**************************************************/
    /*              module internals                  */
    /**************************************************/

    const color = require("ko/color");

    var log = ko.logging.getLogger("hyperlinks");
    //log.setLevel(ko.logging.LOG_DEBUG);

    var _handlers = [];

    /**************************************************/
    /*              module classes                    */
    /**************************************************/

    /**
     * A hyperlink instance created by a handler and set on the view.
     *
     * @param handler {ko.hyperlinks.BaseHandler} - Handler that made it.
     * @param {int} startPos Scimoz position for the start of the hyperlink.
     * @param {int} endPos   Scimoz position for the end of the hyperlink.
     * @param {array} args   Optional - Array of args to pass to the function.
     */
    this.Hyperlink = function(handler, startPos, endPos, args)
    {
        this.handler = handler;
        this.startPos = startPos;
        this.endPos = endPos;
        this.args = args;
    }

    /**
     * Activate this hyperlink.
     *
     * @param view {Components.interfaces.koIScintillaView}  The view instance.
     */
    this.Hyperlink.prototype.jump = function(view)
    {
        this.handler.jump(view, this);
    }

    /**
     * Called when the mouse dwells on this hyperlink.
     *
     * @param view {Components.interfaces.koIScintillaView}  The view instance.
     */
    this.Hyperlink.prototype.dwell = function(view)
    {
        this.handler.dwell(view, this);
    }

    /**
     * Remove this hyperlink.
     *
     * @param view {Components.interfaces.koIScintillaView}  The view instance.
     * @param {string} reason  What the triggering event reason was, can be one
     *        of "keyup", "mousemove", "mouseup" or "blur".
     * @returns {Boolean} True if the hyperlink was removed, false otherwise.
     */
    this.Hyperlink.prototype.remove = function(view, reason)
    {
        return this.handler.remove(view, this, reason);
    }


    /**
     * The base hyperlink handler class. Handlers are responsible for checking
     * to see if an editor position is a hyperlink and then highlighting the
     * hyperlink within the editor.
     *
     * @class
     * @param {string} name A unique name of the hyperlink handler.
     * @param {function} jump_fn Will be called when the user clicks on the jump
     *        point. The matching (or replaced) hyperlink value is the only
     *        argument passed to this function.
     * @param lang_names {array|null} Optional - If set, the handler will
     *        only show hyperlinks when the editor language is one of these
     *        language names.
     * @param {int} indic_style Optional - Indicator style, see scimoz.INDIC_*
     * @param {int} indic_color Optional - Indicator color (BGR), i.e. 0xFFCC33
     */
    this.BaseHandler = function(name, jump_fn, lang_names, indic_style, indic_color)
    {
        if (typeof(lang_names) == 'undefined') {
            lang_names = null;
        }
        if (typeof(indic_style) == 'undefined') {
            indic_style = Components.interfaces.ISciMoz.INDIC_PLAIN;
        }
        if (typeof(indic_color) == 'undefined') {
            indic_color = color.RGBToBGR(0x60,0x90,0xff);
        }

        this.name = name;
        this.func = jump_fn;
        this.lang_names = lang_names;
        this.indic_style = indic_style;
        this.indic_color = indic_color;
    }

    /**
     * Try and show a hyperlink at the current position in the view.
     *
     * @param view {Components.interfaces.koIScintillaView}  View to check.
     * @param scimoz {Components.interfaces.ISciMoz}  Scimoz for the view.
     * @param {int} position  Position in the scimoz editor.
     * @param {string} line  The current line from the editor.
     * @param {int} lineStartPos Scimoz position for the start of the line.
     * @param {int} lineEndPos   Scimoz position for the end of the line.
     * @param {string} reason  What the triggering event reason was, can be one
     *        of "keypress" or "mousemove".
     * @returns {boolean} Whether this handler added a hyperlink here.
     */
    this.BaseHandler.prototype.show = function(view, scimoz, position, line,
                                               lineStartPos, lineEndPos, reason)
    {
        return false;
    }

    /**
     * Called when the mouse dwells on this hyperlink.
     *
     * @param view {Components.interfaces.koIScintillaView}  The view instance.
     * @param hyperlink {ko.hyperlinks.Hyperlink} The hyperlink instance.
     */
    this.BaseHandler.prototype.dwell = function(view, hyperlink)
    {
        // Nothing to do.
    }

    /**
     * Remove this hyperlink instance.
     *
     * @param view {Components.interfaces.koIScintillaView}  The view instance.
     * @param hyperlink {ko.hyperlinks.Hyperlink} The hyperlink instance.
     * @param {string} reason  What the triggering event reason was, can be one
     *        of "keyup", "mousemove", "mouseup" or "blur".
     * @returns {Boolean} True if the hyperlink was removed, false otherwise.
     */
    this.BaseHandler.prototype.remove = function(view, hyperlink, reason)
    {
        // Nothing to do.
        return true;
    }

    /**
     * Set a hyperlink at this position.
     *
     * @param view {Components.interfaces.koIScintillaView}  View to mark.
     * @param {int} startPos Scimoz position for the start of the hyperlink.
     * @param {int} endPos   Scimoz position for the end of the hyperlink.
     * @param {array} args   Optional - Array of args to pass to the function.
     * @returns {ko.hyperlinks.Hyperlink} - The hyperlink instance shown.
     */
    this.BaseHandler.prototype.setHyperlink = function(view, startPos, endPos,
                                                       args)
    {
        //dump(this.name + ": setting hyperlink, style: " + this.indic_style +
        //     ", color: " + this.indic_color + "\n");
        var hyperlink = new ko.hyperlinks.Hyperlink(this, startPos, endPos,
                                                    args);
        view.setHyperlink(hyperlink);
        return hyperlink;
    }

    /**
     * Activate this hyperlink instance.
     *
     * @param view {Components.interfaces.koIScintillaView}  The view instance.
     * @param hyperlink {ko.hyperlinks.Hyperlink} The hyperlink instance.
     */
    this.BaseHandler.prototype.jump = function(view, hyperlink)
    {
        this.func.apply(null, hyperlink.args);
    }

    /**************************************************/
    /*              module functions                  */
    /**************************************************/

    /**
     * Add a handler to the list of known hyperlink handlers.
     *
     * @param handler {ko.hyperlinks.BaseHandler} - The handler to add.
     */
    this.addHandler = function(handler)
    {
        _handlers.push(handler);
    }

    /**
     * Remove this handler from the list of known hyperlink handlers.
     *
     * @param handler {ko.hyperlinks.BaseHandler} - The handler to remove.
     */
    this.removeHandler = function(handler)
    {
        var idx = _handlers.indexOf(handler);
        if (idx >= 0) {
            _handlers.splice(idx, 1);
        }
    }

    /**
     * Return the handler with this name from the list of known hyperlink
     * handlers.
     * 
     * @param {string} name - The handler name to find.
     * @returns {ko.hyperlinks.BaseHandler} - A Handler instance.
     */
    this.getHandlerWithName = function(name)
    {
        for (var i=0; i < _handlers.length; i++) {
            if (_handlers[i].name == name) {
                return _handlers[i];
            }
        }
        return null;
    }

    /**
     * Return a copy of the available hyperlink handlers.
     *
     * @returns {array} Array of the available hyperlink handlers.
     */
    this.getAllHandlers = function()
    {
        return _handlers.slice(0, _handlers.length);
    }

    /**
     * Get the available hyperlink handlers for the given language name, or all
     * hyperlink handlers when lang is not set.
     *
     * @param {string} lang Optional - Language the handler must be valid for.
     * @returns {array} Array of the available hyperlink handlers.
     */
    this.getHandlersForLang = function(lang_name)
    {
        if (!lang_name) {
            return this.getAllHandlers();
        }

        var result = [];
        for (var i=0; i < _handlers.length; i++) {
            if (!_handlers[i].lang_names ||
                _handlers[i].lang_names.indexOf(lang_name) >= 0) {
                result.push(_handlers[i]);
            }
        }
        return result;
    }

    /**
     * Show any available hyperlink at the position in the view.
     *
     * @param view {Components.interfaces.koIScintillaView}  View to check.
     * @param {int} position  Position in the scimoz editor.
     * @param {string} reason  What the triggering event reason was, can be one
     *        of "keypress" or "mousemove".
     * @returns {ko.hyperlinks.BaseHandler} - The handler for the hyperlink
     *          that was shown, or null if no hyperlink was shown.
     */
    this.show = function(view, position, reason)
    {
        if (!view.koDoc || !view.prefs.getBooleanPref("hyperlinksEnabled")) {
            return null;
        }
        var scimoz = view.scimoz;
        var lineNo = scimoz.lineFromPosition(position);
        var startOfLine = scimoz.positionFromLine(lineNo);
        var endOfLine = scimoz.getLineEndPosition(lineNo);
        var line = scimoz.getTextRange(startOfLine, endOfLine);
        var lang_name = view.koDoc.languageForPosition(position);
        var handlers = this.getHandlersForLang(lang_name);
        for (var i=0; i < handlers.length; i++) {
            if (handlers[i].show(view, scimoz, position, line,
                                 startOfLine, endOfLine, reason)) {
                log.debug("Showing hyperlink for handler: " + handlers[i].name);
                return handlers[i];
            }
        }
        return null;
    }

}).apply(ko.hyperlinks);


// A namespace for handlers to use.
ko.hyperlinks.handlers = {};

