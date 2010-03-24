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
 *   Shane Caraveo <shanec@activestate.com>
 */

if (typeof(xtk) == 'undefined') {
    var xtk = {};
}
xtk.domutils = {

/**
 * is this element or an ancestor focused?
 *
 * @param {Element} element
 * @return {Boolean} 
 */
elementInFocus: function(el) {
    try {
        var commandDispatcher = top.document.commandDispatcher
        var focusedElement = commandDispatcher.focusedElement;
        while (focusedElement != null) {
            if (el == focusedElement) return true;
            focusedElement = focusedElement.parentNode;
        }
    } catch (e) {
        log.exception(e);
    }
    return false;
},

/**
 * is the focused element, or it's ancestor a element with a matching localName?
 *
 * @param {String} localName
 * @return {Element} element
 */
getFocusedAncestorByName: function(localName) {
    try {
        var commandDispatcher = top.document.commandDispatcher
        var focusedElement = commandDispatcher.focusedElement;
        if (!focusedElement) return null;
        while (focusedElement.parentNode) {
            if (focusedElement.localName == localName) return focusedElement;
            focusedElement = focusedElement.parentNode;
        }
    } catch (e) {
        log.exception(e);
    }
    return null;
},

fireEvent : function(target, eventName) {
    var event = document.createEvent("Events");
    event.initEvent(eventName, true, true);
    target.dispatchEvent(event);
},

/**
 * Helper method to easily create a new DOM element with a bunch of (optional)
 * attributes set.
 *
 * @param name {string} - The element name to create.
 * @param attributes {object} - (Optional) A map object containing attributes
                                names to values.
 * @returns {domnode}
 */
newElement : function(name, attributes) {
    var elem = document.createElement(name);
    for (var attr in attributes) {
        elem.setAttribute(attr, attributes[attr]);
    }
    return elem;
},


__END__ : null
};


xtk.domutils.tooltips = {};
(function() {

function tooltipHandler(tooltipName) {
    this._hideTimeout = null;
    this._tooltipName = tooltipName;
}
tooltipHandler.constructor = tooltipHandler;

tooltipHandler.prototype.__defineGetter__("_tooltip",
function() {
    return document.getElementById(this._tooltipName);
});

tooltipHandler.prototype.__defineGetter__("_tooltipTextNode",
function() {
    return document.getElementById(this._tooltipName+"-tooltipText");
});

/**
 * Show the tooltip on this element.
 * @param parentElement {DomElement} - The element to show the tooltip above.
 * @param  x {int} - The x co-ordinate.
 * @param  y {int} - The y co-ordinate.
 * @param  timeout {int} - Remove the tooltip after this number of milliseconds,
 *                         if this value is <= 0, then there is no timeout.
 */
tooltipHandler.prototype.show = function(parentElement, x, y, timeout /* 5000 ms */) {
    if ((typeof(timeout) == 'undefined') || (timeout == null)) {
        timeout = 5000;
    }

    if (this._hideTimeout) {
        window.clearTimeout(this._hideTimeout);
        this._hideTimeout = null;
    }
    if (this.fillInTooltip(parentElement, x, y)) {
        // to handle multi line tooltips, we have to do some magic.
        // first we resize to the minimal size needed by the
        // description tag that is used to hold the text.
        // set the height to zero, then show it.  this resets the
        // descriptions box size to the actual size of content.  Then
        // we resize to the new box size.  This depends on the effects
        // of mozilla reflow, which are not defined, and thus may
        // change in the future
        this._tooltip.setAttribute('style','height: 0px');
        this._tooltip.openPopup(parentElement,"after_pointer",x,y,false);
        if (timeout > 0) {
            this._hideTimeout = window.setTimeout(function (me) { me.hide(); }, timeout, this);
        }
    }
}

tooltipHandler.prototype.hide = function() {
    this._tooltip.hidePopup();
}

tooltipHandler.prototype.fillInTooltip = function(tipElement, x, y) {
    // this function only gets called if the tooltip attribute
    // on an element has been set to 'editorTooltip'.  This is
    // specificly to support tooltips in scintilla, and should
    // not be used by any other elements.
    try {
        // first update the tooltiptext on the view, but put it
        // directly into our special tooltip handler.  The basic
        // logic here is copied from moz 1.4 globalOverlay.js
        // FillInTooltip()
        while (this._tooltipTextNode.hasChildNodes())
            this._tooltipTextNode.removeChild(this._tooltipTextNode.firstChild);

        var text = tipElement.getTooltipText(x, y);
        if (text)  {
            var node = document.createTextNode(text);
            this._tooltipTextNode.appendChild(node);
            return true;
        }
    } catch(e) {
        log.exception(e);
    }
    return false;
}

var _handlers = {};
this.getHandler = function(tooltipName) {
    if (!(tooltipName in _handlers))
        _handlers[tooltipName] = new tooltipHandler(tooltipName);
    return _handlers[tooltipName];
}

}).apply(xtk.domutils.tooltips);
