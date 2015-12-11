/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var sys = require("sdk/system");

const {Cc, Ci} = require("chrome");
const USE_HITTEST = /^(win|macosx)/i.test(sys.platform);

module.exports = function(elem) {
    
    this._elem = elem;
    this._window = elem.ownerDocument.defaultView;
    
    this.mouseDownCheck = function(e) {
        return "_draggable" in this ? this._draggable : true;
    },
    this.dragTags = ["box", "hbox", "vbox", "spacer", "label", "statusbarpanel", "stack",
            "toolbox", "toolboxrow",
            "toolbaritem", "toolbarseparator", "toolbarspring", "toolbarspacer",
            "radiogroup", "deck", "scrollbox", "arrowscrollbox", "tabs"
    ],
    this.shouldDrag = function(aEvent) {
        if (aEvent.button != 0 ||
            this._window.fullScreen || !this.mouseDownCheck.call(this._elem, aEvent) ||
            aEvent.defaultPrevented)
            return false;

        let target = aEvent.originalTarget, parent = aEvent.originalTarget;

        // The target may be inside an embedded iframe or browser. (bug 615152)
        if (target.ownerDocument.defaultView != this._window)
            return false;
        
        if (this._elem._tophandle) {
            if (aEvent.pageY > 30) return false;
        }

        while (parent != this._elem) {
            let mousethrough = parent.getAttribute("mousethrough");
            if (mousethrough == "always")
                target = parent.parentNode;
            else if (mousethrough == "never")
                break;
            parent = parent.parentNode;
        }
        while (target != this._elem) {
            if (this.dragTags.indexOf(target.localName) == -1)
                return false;
            target = target.parentNode;
        }
        return true;
    };

    this.isPanel = function() {
        return this._elem instanceof Ci.nsIDOMXULElement &&
            this._elem.localName == "panel";
    };

    this.handleEvent = function(aEvent) {
        let isPanel = this.isPanel();
        if (USE_HITTEST && !isPanel) {
            if (this.shouldDrag(aEvent))
                aEvent.preventDefault();
            return;
        }

        switch (aEvent.type) {
            case "mousedown":
                if (!this.shouldDrag(aEvent))
                    return;

                if (/^linux/i.test(sys.platform)) {
                    // On GTK, there is a toolkit-level function which handles
                    // window dragging, which must be used.
                    this._window.beginWindowMove(aEvent, isPanel ? this._elem : null);
                    break;
                }
                if (isPanel) {
                    let screenRect = this._elem.getOuterScreenRect();
                    this._deltaX = aEvent.screenX - screenRect.left;
                    this._deltaY = aEvent.screenY - screenRect.top;
                } else {
                    this._deltaX = aEvent.screenX - this._window.screenX;
                    this._deltaY = aEvent.screenY - this._window.screenY;
                }
                this._draggingWindow = true;
                this._window.addEventListener("mousemove", this, false);
                this._window.addEventListener("mouseup", this, false);
                break;
            case "mousemove":
                if (this._draggingWindow) {
                    let toDrag = this.isPanel() ? this._elem : this._window;
                    toDrag.moveTo(aEvent.screenX - this._deltaX, aEvent.screenY - this._deltaY);
                }
                break;
            case "mouseup":
                if (this._draggingWindow) {
                    this._draggingWindow = false;
                    this._window.removeEventListener("mousemove", this, false);
                    this._window.removeEventListener("mouseup", this, false);
                }
                break;
        }
    };

    var init = function() {
        if (USE_HITTEST && !this.isPanel())
            this._elem.addEventListener("MozMouseHittest", this.handleEvent.bind(this), false);
        else
            this._elem.addEventListener("mousedown", this.handleEvent.bind(this), false);
            
    };
    
    init();

};