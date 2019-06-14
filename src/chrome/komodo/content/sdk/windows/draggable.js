var sys = require("sdk/system");

const {Cc, Ci} = require("chrome");
const USE_HITTEST = /^(win|macosx)/i.test(sys.platform);

var draggable = function (elem) {
    this.init(elem);
};

/**
 * Used to make windows draggable using custom handlers
 *
 * @module ko/windows/draggable
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 */
(function () {

    this.mouseDownCheck = function(e) {
        return "_draggable" in this ? this._draggable : true;
    },
    this.dragTags = ["box", "hbox", "vbox", "spacer", "label", "statusbarpanel", "stack",
            "toolbox", "toolboxrow", "description", "toolbaritem", "groupbox", "window",
            "toolbaritem", "toolbarseparator", "toolbarspring", "toolbarspacer", "toolbar",
            "radiogroup", "deck", "scrollbox", "arrowscrollbox", "tabs"
    ],
    this.dragTagsAlways = ["box", "hbox", "vbox", "spacer"],
    this.shouldDrag = function(aEvent) {
        if (aEvent.button != 0 ||
            this._window.fullScreen || !this.mouseDownCheck.call(this._elem, aEvent) ||
            aEvent.defaultPrevented)
            return false;

        let target = aEvent.originalTarget || aEvent.target;
        let parent = target;

        // The target may be inside an embedded iframe or browser. (bug 615152)
        //if (target.ownerDocument.defaultView != this._window)
        //    return false;

        var inDragTags = false;
        var _target = target;
        while (_target.localName && _target != this._elem) {
            if (this.dragTags.indexOf(_target.localName) != -1)
            {
                inDragTags = true;
                break;
            }
            _target = _target.parentNode;
        }

        if (this._elem._tophandle && ! inDragTags) {
            if (aEvent.pageY > 30) return false;
        }

        while (parent && parent != this._elem) {
            let mousethrough = parent.getAttribute ? parent.getAttribute("mousethrough") : null;
            if (mousethrough == "always")
                target = parent.parentNode;
            else if (mousethrough == "never")
                break;
            parent = parent.parentNode;
        }

        while (target.localName && target != this._elem) {
            if (this.dragTags.indexOf(target.localName) == -1)
            {
                return false;
            }
            if (target.getAttribute("not-draggable") == "true")
            {
                return false;
            }
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

    this.init = function(elem) {
        this._elem = elem;
        this._window = elem.ownerDocument.defaultView;

        if (elem.ownerDocument.readyState != "complete")
        {
            this._window.addEventListener("load", this.init.bind(this, elem));
            return;
        }

        if (USE_HITTEST && !this.isPanel())
            this._elem.addEventListener("MozMouseHittest", this.handleEvent.bind(this), false);
        else
            this._elem.addEventListener("mousedown", this.handleEvent.bind(this), false);

    };

}).apply(draggable.prototype);

/**
 * @constructor module:ko/windows/draggable
 * 
 * @param {Element} elem    The element to turn into a draggable
 */
module.exports = function(elem) {
    return new draggable(elem);
};
