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

(function() {

    const Ci = Components.interfaces;
    const color = require("ko/color");
    var {XPCOMUtils} = Components.utils.import("resource://gre/modules/XPCOMUtils.jsm", {});
    var log = ko.logging.getLogger('hyperlinks::GotoDefinition');

    /**
     * A goto definition hyperlink handler.
     *
     * @class
     * @base ko.hyperlinks.BaseHandler
     */
    this.GotoDefinitionHandler = function() {
        var name = "Goto Definition";
        var fn = function(args) {
            ko.views.manager.do_cmd_goToDefinition.apply(null, args);
        };
        var lang_names = null;  /* All language types */
        var indic_style = Components.interfaces.ISciMoz.INDIC_PLAIN;
        //var indic_color = color.RGBToBGR(0xff,0x80,0x20);
        var indic_color = color.RGBToBGR(0xA0,0x00,0xF0);
        var base_args = [name, fn, lang_names, indic_style, indic_color];
        ko.hyperlinks.BaseHandler.apply(this, base_args);
    
        // Listen for enabled pref changes.
        this.enabledPrefName = "hyperlinksEnableGotoDefinition";
        var prefs = Components.classes["@activestate.com/koPrefService;1"].
                      getService(Components.interfaces.koIPrefService).prefs;
        prefs.prefObserverService.addObserver(this, this.enabledPrefName, 0);
        this.enabled = prefs.getBooleanPref(this.enabledPrefName);
        ko.main.addWillCloseHandler(this.destroy, this);
    };
    
    // The following two lines ensure proper inheritance (see Flanagan, p. 144).
    this.GotoDefinitionHandler.prototype = new ko.hyperlinks.BaseHandler();
    this.GotoDefinitionHandler.prototype.constructor = this.GotoDefinitionHandler;
    
    this.GotoDefinitionHandler.prototype.destroy = function()
    {
        var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                      getService(Components.interfaces.koIPrefService);
        prefSvc.prefs.prefObserverService.removeObserver(this, this.enabledPrefName);
    }
    
    this.GotoDefinitionHandler.prototype.observe = function(prefSet, prefName, prefSetID)
    {
        switch (prefName) {
            case this.enabledPrefName:
                this.enabled = prefSet.getBooleanPref(this.enabledPrefName);
                break;
        }
    };
    
    /**
     * Try and show a hyperlink at the current position in the view.
     *
     * @param view {Components.interfaces.koIScintillaView}  View to check.
     * @param scimoz {Components.interfaces.ISciMoz}  Scimoz for the view.
     * @param {int} pos  Position in the scimoz editor.
     * @param {string} line  The current line from the editor.
     * @param {int} lineStartPos Scimoz position for the start of the line.
     * @param {int} lineEndPos   Scimoz position for the end of the line.
     * @param {string} reason  What the triggering event reason was, can be one
     *        of "keypress" or "mousemove".
     * @returns {ko.hyperlinks.Hyperlink} - The hyperlink instance shown.
     */
    this.GotoDefinitionHandler.prototype.show = function(
                    view, scimoz, position, line, lineStartPos, lineEndPos, reason)
    {
        // If the popup tooltip is already open, leave it alone and return.
        var tooltip = document.getElementById("hyperlink_gotodefinition_tooltip");
        if (tooltip && tooltip.state == "open") {
            return null;
        }
        
        // For goto definition, if this view does not support codeintel
        // citadel stuff, then goto definition is not supported and
        // there is no need to mark any hyperlinks.
        if (!this.enabled || !view.isCICitadelStuffEnabled) {
            return null;
        }

        var start = scimoz.wordStartPosition(position, true);
        var end = scimoz.wordEndPosition(position, true);
        if (start < end) {
            var next_start;
            while (1) {
                next_start = scimoz.wordStartPosition(start, false);
                if (next_start < start) {
                    // XXX: This needs to use language specific separators.
                    if ([".", "->", "::"].indexOf(scimoz.getTextRange(next_start, start)) >= 0) {
                        start = scimoz.wordStartPosition(next_start, true);
                        continue;
                    }
                }
                break;
            }
            return this.setHyperlink(view, start, end);
        }
        return null;
    }

    /**
     * Remove this hyperlink instance.
     *
     * @param view {Components.interfaces.koIScintillaView}  The view instance.
     * @param hyperlink {ko.hyperlinks.Hyperlink} The hyperlink instance.
     * @param {string} reason  What the triggering event reason was, can be one
     *        of "keyup", "mousemove", "mouseup" or "blur".
     */
    this.GotoDefinitionHandler.prototype.remove = function(view, hyperlink, reason)
    {
        if (reason == "mousemove") {
            // Don't remove the hyperlink on mousemove events.
            return false;
        }
        ko.hyperlinks.BaseHandler.prototype.remove.apply(this, arguments);
        var tooltip = document.getElementById("hyperlink_gotodefinition_tooltip");
        if (tooltip) {
            tooltip.hidePopup();
        }
        return true;
    }

    /**
     * Called when the mouse dwells on this hyperlink.
     *
     * @param view {Components.interfaces.koIScintillaView}  The view instance.
     * @param hyperlink {ko.hyperlinks.Hyperlink} The hyperlink instance.
     */
    this.GotoDefinitionHandler.prototype.dwell = function(view, hyperlink)
    {
        ko.hyperlinks.BaseHandler.prototype.dwell.apply(this, arguments);
        if (view.isCICitadelStuffEnabled) {
            this._getDefinition(view, hyperlink);
        }
    }

    /**
     * Function used to update the definiton information
     * @param hyperlink {ko.hyperlinks.Hyperlink} The hyperlink
     * @private
     */
    this.GotoDefinitionHandler.prototype._getDefinition = function(view, hyperlink) {
        try {
            var scimoz = view.scimoz;
            if (!scimoz) {
                return;
            }
    
            var currentPos = hyperlink.endPos;
            var style = scimoz.getStyleAt(currentPos);
            var displayPath = view.koDoc.displayPath;
            var wordUnderCursor = ko.interpolate.getWordUnderCursor(scimoz);
    
            // We've told to update, but we may not need to:
            // If the position has not changed much and the the word under the
            // current position is the same as last time, if it is, do not
            // bother to update.
            //if ((this._lastDisplayPath == displayPath) &&
            //    (this._lastStyle == style) &&
            //    ((currentPos <= (this._lastCurrentPos + 20)) &&
            //     (currentPos >= (this._lastCurrentPos - 20)) &&
            //     (wordUnderCursor == this._lastWordUnderCursor))) {
            //    // The same place as current info, so nothing to update
            //    return;
            //}
            //dump("Updating codehelper\n");
            // Remember this filename, position and style
            //this._lastDisplayPath = displayPath;
            //this._lastCurrentPos = currentPos;
            //this._lastWordUnderCursor = wordUnderCursor;
    
            var langObj = view.koDoc.languageObj;
            var styleCount = new Object();
            var commentStyles = langObj.getCommentStyles(styleCount);
            var stringStyles = langObj.getStringStyles(styleCount);
            if ((commentStyles.indexOf(style) >= 0) ||
                (stringStyles.indexOf(style) >= 0)){
                // Doesn't work in strings or comments.
                return;
            }
    
            var ciBuf = view.koDoc.ciBuf;
            ko.codeintel.linkCurrentProjectWithBuffer(ciBuf);
            // Create a trigger, it must be a specific position in the document,
            // due to variable scope implications etc...
            ciBuf.defn_trg_from_pos(currentPos, function(trg) {
                if (!trg) {
                    return;
                }
                // Create a codeintel completion handler
                var ciUIHandler = new GotoDefinitionUIHandler();
                // Fire off the codeintel call, which will call
                // setDefinitionsInfo when done
                ciBuf.async_eval_at_trg(trg, ciUIHandler);
                //dump("async_called\n");
            });
    
        } catch (ex) {
            log.exception(ex);
        }
    }


    /********************************************************
     *      Utility functions for the on-hover calltip      *
     ********************************************************/

    function _simpleEscapeHtml(s) {
        s = s.replace("&", "&amp;", "g");
        s = s.replace("<", "&lt;", "g");
        return s.replace(">", "&gt;", "g");
    }

    function _parseXULAndReturnElement(xul_string) {
        // wrap the content in a box. This is necessary in case the user
        // enters multiple top-level nodes. Also, we declare the XUL namespace
        // so that the user doesn't have to type it in themselves.
        xul_string = "<xul:vbox id='dataBox' flex='1' " +
                "xmlns:xul='http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul' " +
                "xmlns:html='http://www.w3.org/1999/xhtml' " +
                "xmlns='http://www.w3.org/1999/xhtml'>" +
                    "<div>" + xul_string + "</div>" +
                "</xul:vbox>";
      
        // create a new DOMParser object and parse the content. The
        // parseFromString function takes two arguments, the string to
        // parse and the content type. Currently Mozilla only supports
        // parsing HTML and XML using the DOMParser, so features that
        // require a XUL document, such as templates or overlays, won't
        // work using this method.
        var parser = new DOMParser();
        var resultDoc = parser.parseFromString(xul_string, "text/xml");
      
        // if the top-level node of the parsed document turns out
        // to be 'parsererror' that means that the XML was not
        // well-formed.
        if (resultDoc.documentElement.tagName == "parsererror") {
            return null;
        }
      
        // if no error occurred, grab the documentElement property of
        // the parsed document and append it to this XUL window. The
        // content should appear at the bottom of the window.
        return resultDoc.documentElement;
    }

    /**
     * Return a string with escaped html attributes.
     */
    function _setDefinitionsInfo(count, ciDefns, trg) {
        try {
            /** @type {Components.interfaces.koIScintillaView} */
            var view = ko.views.manager.currentView;
            var scimoz = view.scimoz;
            if (!scimoz || !scimoz.isFocused) {
                // Don't show the tooltip if scimoz doesn't have the focus
                // anymore - bug 88347.
                return;
            }
            var defns = ciDefns;
            // defns is an array of koICodeIntelDefinition
            if (defns && defns.length > 0) {
                // Just display the first available one
                /** @type {Components.interfaces.koICodeIntelDefinition} */
                var def = defns[0];
    
                var div;
                var tooltip = document.getElementById("hyperlink_gotodefinition_tooltip");
                if (tooltip == null) {
                    tooltip = document.createElement('panel');
                    tooltip.setAttribute("noautofocus", "true");
                    tooltip.setAttribute('id', 'hyperlink_gotodefinition_tooltip');
                    div = document.createElement('div');
                    div.setAttribute("id", "hyperlink_gotodefinition_div");
                    div.setAttribute("class", "hyperlink_gotodefinition_div");
                    tooltip.appendChild(div);
                    document.documentElement.appendChild(tooltip);
                } else {
                    div = tooltip.firstChild;
                    // Remove old elements
                    while (div.lastChild) {
                        div.removeChild(div.lastChild);
                    }
                }
    
                // The layout we want:
                //<div>
                //  <span> Name </span> <span> Signature </span>
                //  <hr/>
                //  <span> Lang </span>
                //  <span> Type </span>
                //  <span> Attrs </span>
                //  <hr/>
                //  <span> Doc </span>
                //</div>
    
                var textlines = [];
                var cmd = "";
                if (def.path && def.line >= 0) {
                    cmd = "ko.open.openURI('" + def.path + "#" + def.line + "');";
                    //dump("cmd: " + cmd + "\n");
                }
                textlines.push('<span class="codehelper_name" onclick="'
                               + cmd + '">' + def.name + "</span>");
                if (def.ilk == "function") {
                    textlines.push('<span class="codehelper_signature">('
                                   + _simpleEscapeHtml(def.signature.split("(", 2)[1])
                                   + '</span>');
                }
    
                textlines.push("<hr />");
    
                var datalines = [];
                //var fullname = def.fullname;
                //fullname = fullname.replace(".", ". ");
                //datalines.push("Scope: " + fullname.substring(0, fullname.length - (def.name.length + 1)));
                datalines.push("Lang:  " + def.lang);
                var path = def.path;
                if (path && def.line >= 0) {
                    if (path.length > 60) {
                        // Shorten it down.
                        path = path.substr(0, 20) + " ... " + path.substr(-40);
                    }
                    datalines.push("Defined in: " + path);
                }
                if (def.ilk == "variable" ||
                    (def.ilk == "argument" && def.citdl)) {
                    datalines.push("Type:  " + def.citdl);
                    //datalines.push(def.citdl);
                } else if (def.ilk == "blob") {
                    datalines.push("Type:  " + "module");
                    //datalines.push("Module");
                } else {
                    datalines.push("Type:  " + def.ilk);
                }
                if (def.attributes) {
                    datalines.push("Attr:  " + def.attributes);
                    //datalines.push(def.attributes);
                }
                for (var i=0; i < datalines.length; i++) {
                    textlines.push('<span class="codehelper_info">' + _simpleEscapeHtml(datalines[i]) + "</span><br />");
                }
    
                if (def.doc) {
                    textlines.push("<hr />");
                    //textlines.push('<i style="white-space: pre-wrap !important;">' + _simpleEscapeHtml(def.doc) + '</i>');
                    textlines.push('<span class="codehelper_doc">' + _simpleEscapeHtml(def.doc) + '</span>');
                }
    
                //dump("textlines:\n\n" + textlines.join("\n") + "\n\n");
    
                //tooltip.contents = textlines.join("\n");
                var node = _parseXULAndReturnElement(textlines.join("\n"));
                if (node) {
                    //div.appendChild(node.cloneNode(true));
                    var elem;
                    while (node.firstChild) {
                        elem = node.removeChild(node.firstChild);
                        div.appendChild(elem);
                    }
                }

                // Ensure the tooltip colors match the editor colors.
                if (view.scheme.isDarkBackground) {
                    tooltip.setAttribute("class", "dark");
                } else {
                    tooltip.setAttribute("class", "light");
                }
                var foreColor = view.scheme.getFore(view.languageObj.name, "default");
                tooltip.style.color = foreColor;

                var x, y;
                [x,y] = view._last_mousemove_xy;
                tooltip.openPopup(view, "after_pointer", x, y, false, false);
            }
        } catch (ex) {
            log.exception(ex);
        }
    }
    
    var GotoDefinitionUIHandler = function() {
    }

    GotoDefinitionUIHandler.prototype.QueryInterface =
        XPCOMUtils.generateQI([Ci.koICodeIntelCompletionUIHandler]);
    GotoDefinitionUIHandler.prototype.setStatusMessage = function() {
        // Do nothing...
    }
    GotoDefinitionUIHandler.prototype.setDefinitionsInfo = function(count, ciDefns, trg) {
        _setDefinitionsInfo(count, ciDefns, trg);
    }
    GotoDefinitionUIHandler.prototype.done = function() {};

}).apply(ko.hyperlinks);


ko.hyperlinks.handlers.gotoDefinitionHandler = new ko.hyperlinks.GotoDefinitionHandler();
ko.hyperlinks.addHandler(ko.hyperlinks.handlers.gotoDefinitionHandler);
