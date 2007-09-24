/**
 * Copyright (c) 2006,2007 ActiveState Software Inc.
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
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
}

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

tooltipHandler.prototype.show = function(parentElement, x, y) {
    if (this._hideTimeout) {
        window.clearTimeout(this._hideTimeout);
        this._hideTimeout = null;
    }
    if (this.fillInTooltip(parentElement)) {
        // to handle multi line tooltips, we have to do some magic.
        // first we resize to the minimal size needed by the
        // description tag that is used to hold the text.
        // set the height to zero, then show it.  this resets the
        // descriptions box size to the actual size of content.  Then
        // we resize to the new box size.  This depends on the effects
        // of mozilla reflow, which are not defined, and thus may
        // change in the future
        this._tooltip.setAttribute('style','height: 0px');
        this._tooltip.showPopup(parentElement,x,y,'tooltip',"topleft","topleft");
        var box = document.getBoxObjectFor(this._tooltipTextNode);
        // XXX we add 6 pixels, 1 for border, 2 for padding, as
        // defined in komodo.css for the tooltip popup
        this._tooltip.setAttribute('style','height: '+(box.height+6)+'px');
        this._hideTimeout = window.setTimeout(function (me) { me.hide(); } ,5000, this);
    }
}

tooltipHandler.prototype.hide = function() {
    this._tooltip.hidePopup();
}

tooltipHandler.prototype.fillInTooltip = function(tipElement) {
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

        var text = tipElement.getTooltipText();
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
