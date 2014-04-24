Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");
Components.utils.import("resource://gre/modules/Services.jsm");

window.addEventListener("load", function() {
    const Cc = Components.classes;
    const Ci = Components.interfaces;
    var tree = document.getElementById("toolbarTree");
    var view;

    /**
     * Sort comparator for toolbars / toolbar items. This is expected to be
     * passed to Array.prototype.sort.
     * 
     * @param   {Element} left    The first element to compare
     * @param   {Element} right   The second element to compare
     * 
     * @returns {Number} <0 if left is before right, >0 if left is after right,
     *                   0 if they should be the same (!?)
     */
    function sortComparator(left, right) {
        if (left.parentNode === right.parentNode) {
            if (left.ordinal !== "" || right.ordinal !== "") {
                // one of them has an ordinial (or both); treat empty ordinal as 0
                return (parseInt(left.ordinal, 10) || 0) -
                       (parseInt(right.ordinal, 10) || 0);
            }
        }
        // no ordinals, or too far away; use document position
        var position = left.compareDocumentPosition(right);
        if (position & Node.DOCUMENT_POSITION_PRECEDING ||
            position & Node.DOCUMENT_POSITION_CONTAINS)
        {
            return 1;
        }
        if (position & Node.DOCUMENT_POSITION_FOLLOWING ||
            position & Node.DOCUMENT_POSITION_CONTAINED_BY)
        {
            return -1;
        }
        // nothing else makes sense!?
        return left.id < right.id ? -1 : right.id < left.id ? 1 : 0;
    }

    /**
     * Constructor for the custom tree view used in the customize toolbar dialog
     * 
     * @param   {<toolbox>} toolbox   The toolbox to customize
     * @note    This constructs a nsITreeView via xtk.hierarchicalTreeView
     */
    function ToolboxTreeView(toolbox) {
        this._toolbox = toolbox;
        var toolbars = Array.slice(toolbox.childNodes)
                            .concat(toolbox.externalToolbars)
                            .filter(function(elem) elem instanceof Element &&
                                                   elem.localName == "toolbar" &&
                                                   !elem.getAttribute("fullscreencontrol") &&
                                                   elem.getAttribute("customizable") != "false" &&
                                                   !!elem.id)
                            .sort(sortComparator);
        this.wrappedJSObject = this;
        this._toolbars = toolbars.map(function(t) new Toolbar(t));
        xtk.hierarchicalTreeView.call(this, this._toolbars);

        // Mozilla 22 changed the way tree properties work.
        if ((parseInt(Services.appinfo.platformVersion)) < 22) {
            this.getCellProperties = this.getCellPropertiesMoz21AndOlder;
        }

        // set up ordinals for reordering support
        var container = toolbox.querySelector("toolboxrow") || toolbox;
        var elems = toolbars.filter(function(n) n.parentNode === container)
                            .filter(function(n) n.hasAttribute("can-drag"))
                            .sort(sortComparator);
        var ordinal = 0;
        for (var i = 0; i < elems.length; ++i) {
            var elem = elems[i];
            if (elem.hasAttribute("ordinal")) {
                var thisOrdinal = parseInt(elem.getAttribute("ordinal", 10));
                if (thisOrdinal <= ordinal) {
                    // ordinal overlap
                    elem.setAttribute("ordinal", ordinal);
                } else {
                    ordinal = parseInt(elem.getAttribute("ordinal", 10));
                }
            } else {
                elem.setAttribute("ordinal", ordinal);
            }
            ++ordinal;
        }
    }
    ToolboxTreeView.prototype = new xtk.hierarchicalTreeView();
    ToolboxTreeView.prototype.constructor = ToolboxTreeView;

    ToolboxTreeView.prototype.getCellText = function(row, column) {
        switch (column.id) {
            case "colName":
                if (this._rows[row].elem.localName == "toolbarseparator") {
                    return Array(11).join("\u2500");
                }
                return this._rows[row].elem.tooltipText;
        }
        return "<error getting text for column " + column.id + ">";
    }

    ToolboxTreeView.prototype.getCellValue = function(index, column) {
        return this._rows[index].elem.getAttribute("kohidden") != "true";
    };

    ToolboxTreeView.prototype.getCellProperties = function(row, col) {
        var properties = "col-checkbox";
        var parent = this.getParentIndex(row);
        if (parent < 0) {
            properties += " no-parent";
        } else if (this.getCellValue(parent, col)) {
            properties += " parent-checked";
        }
        return properties;
    };

    ToolboxTreeView.prototype.getCellPropertiesMoz21AndOlder = function(row, col, properties) {
        properties.AppendElement(this._atom_col_checkbox);
        var parent = this.getParentIndex(row);
        if (parent < 0) {
            properties.AppendElement(this._atom_no_parent);
            return;
        }
        if (this.getCellValue(parent, col)) {
            properties.AppendElement(this._atom_parent_checked);
        }
    };

    ToolboxTreeView.prototype.getImageSrc = function(row, col) {
        if (col.id != "colName") {
            // we only do images in the name column (the checkboxes go via
            // properties, see getCellProperties above)
            return null;
        }
        
        if ("imagesrc" in this._rows[row]) {
            // we have a cached value
            return this._rows[row].imagesrc;
        }
        var elem = this._rows[row].elem;
        if (elem.getAttribute("image")) {
            // images set via attribute, probably a custom toolbar button
            return elem.getAttribute("image");
        }
        var style = getComputedStyle(elem);
        var url = /^url\(['"]?(.*?)['"]?\)$/.exec(style.listStyleImage);
        if (!url) {
            if (elem.localName == "toolbar") {
                // toolbars with no icon get a default one
                // (but don't cache this)
                return "chrome://komodo/skin/images/toolbar_icon.png";
            }
            return null;
        }
        var rect = /^rect\((\d+)px, (\d+)px, (\d+)px, (\d+)px\)/.exec(style.MozImageRegion);
        if (!rect) {
            // no cropping, do the easy thing
            return this._rows[row].imagesrc = url[1];
        }

        // We would rather not get here, but we need to figure out what image
        // to use here. This is complicated by the fact that the image load is
        // asynchronous. Here, we set up the load then spin the event loop until
        // the load completes (or errors out), then try to blit the section of
        // the image we care about into a <canvas>.
        var eventName = null;
        function onDone(event) { eventName = event.type; }
        this._image.addEventListener("load", onDone, false);
        this._image.addEventListener("error", onDone, false);
        this._image.setAttribute("src", url[1]);
        while (eventName === null) {
            Services.tm.currentThread.processNextEvent(true);
        }
        this._image.removeEventListener("load", onDone, false);
        this._image.removeEventListener("error", onDone, false);
        if (eventName != "load") {
            // Load failed (errored out). Return nothing.
            return null;
        }
        // The image has loaded. Figure out the rectangle of it we want, then
        // draw it into the canvas.
        var dest = {
            left: rect[4],
            top: rect[1],
            width: rect[2] - rect[4],
            height: rect[3] - rect[1] };
        this._canvas.setAttribute("width", dest.width);
        this._canvas.setAttribute("height", dest.height);
        this._canvas.width = dest.width;
        this._canvas.height = dest.height;
        var ctx = this._canvas.getContext("2d");
        ctx.clearRect(0, 0, dest.width, dest.height);
        ctx.drawImage(this._image,
                      dest.left, dest.top, dest.width, dest.height,
                      0, 0, dest.width, dest.height);
        // Everything's good; cache the result and return the url.
        return this._rows[row].imagesrc = this._canvas.toDataURL();
    };
    
    ToolboxTreeView.prototype.cycleCell = function(row, col) {
        if (col.id != "colCheck") {
            // we should not get here; this isn't the right column
            return;
        }
        var parent = this.getParentIndex(row);
        if (parent !== -1) {
            // valid parent
            if (this._rows[parent].elem.hidden || this._rows[parent].elem.getAttribute("kohidden") == "true") {
                // but it's hidden; this is disabled
                return;
            }
        }
        var elem = this._rows[row].elem;
        elem.setAttribute("kohidden", (elem.getAttribute("kohidden") == "true") ? "false" : "true");
        // Fire an event so the caller can tell something changed
        var event = document.createEvent("XULCommandEvent");
        event.initCommandEvent("customize", true, true,
                               window, 0, false, false, false, false, null);
        this.tree.element.dispatchEvent(event);
    };

    ToolboxTreeView.prototype.canDrop = function(index, orientation, dataTransfer) {
        switch (orientation) {
            case Ci.nsITreeView.DROP_AFTER:
                ++index;
                // fallthrough
            case Ci.nsITreeView.DROP_BEFORE:
                break;
            default:
                return false;
        }
        if (dataTransfer.mozItemCount != 1) {
            return false;
        }
        var source = dataTransfer.mozGetDataAt("komodo/toolbar-customize-tree", 0);
        if (!source) {
            return false;
        }

        var target = this._rows[index];
        if (!(target instanceof Toolbar)) {
            // not a toolbar
            return false;
        }

        if (source === target) {
            // dropping next to (before) the source; no point
            return false;
        }
        if (index > 0 && this._rows[index - 1] === source) {
            // dropping next to (after) the source; no point
            return false;
        }
        return target;
    };

    ToolboxTreeView.prototype.drop = function(rowIndex, orientation, dataTransfer) {
        var target = this.canDrop(rowIndex, orientation, dataTransfer);
        if (!target) {
            return;
        }
        var source = dataTransfer.mozGetDataAt("komodo/toolbar-customize-tree", 0);

        var dropIndex = this._rows.indexOf(target);
        var start = this._rows.indexOf(source);
        var end = start + 1;
        while (end in this._rows && this._rows[end].level > source.level) {
            ++end;
        }
        var cut = this._rows.splice(start, end - start);
        if (start < dropIndex) {
            dropIndex -= (end - start);
        }
        this._rows.splice.apply(this._rows, [dropIndex, 0].concat(cut));
        this.tree.invalidate();

        // fix the ordinals
        var ordinal = -1;
        var level = target.level;
        source.elem.setAttribute("ordinal", ordinal);
        for (var index = 0; index < this._rows.length; ++index) {
            var row = this._rows[index];
            if (row.level != target.level) {
                continue;
            }
            if (!row.elem.hasAttribute("can-drag")) {
                continue;
            }
            var elem = row.elem;
            var stored = parseInt(elem.getAttribute("ordinal") || 1, 10);
            if (stored > ordinal) {
                ordinal = stored;
            } else {
                elem.setAttribute("ordinal", ++ordinal);
                if (elem.id) {
                    elem.ownerDocument.persist(elem.id, "ordinal");
                }
            }
        }
    };

    XPCOMUtils.defineLazyGetter(ToolboxTreeView.prototype, "_atomSvc",
        function() Cc["@mozilla.org/atom-service;1"].getService(Ci.nsIAtomService));

    XPCOMUtils.defineLazyGetter(ToolboxTreeView.prototype, "_atom_parent_checked",
        function() this._atomSvc.getAtom("parent-checked"));
    XPCOMUtils.defineLazyGetter(ToolboxTreeView.prototype, "_atom_no_parent",
        function() this._atomSvc.getAtom("no-parent"));
    XPCOMUtils.defineLazyGetter(ToolboxTreeView.prototype, "_atom_col_checkbox",
        function() this._atomSvc.getAtom("col-checkbox"));

    XPCOMUtils.defineLazyGetter(ToolboxTreeView.prototype, "_canvas",
        function() document.getElementById("canvas"));
    XPCOMUtils.defineLazyGetter(ToolboxTreeView.prototype, "_image",
        function() document.getElementById("image"));

    /**
     * Constructs a toolbaritem for the tree view
     * 
     * @param   {Element} item   The element to wrap
     * @note    This conforms to requirements for a xtk.hierarchicalTreeView row
     */
    function ToolbarItem(item) {
        this.elem = item;
        this.original = {"hidden": this.elem.getAttribute("kohidden"),
                         "ordinal": this.elem.hasAttribute("ordinal") ?
                                        this.elem.getAttribute("ordinal") : null};
        this._id = this.elem.id;
    }
    ToolbarItem.prototype.isContainer = false;
    ToolbarItem.prototype.hasChildren = false;
    ToolbarItem.prototype.getChildren = function() [],
    ToolbarItem.prototype.state = 0;
    ToolbarItem.prototype.level = 0;

    /**
     * Constructs a toolbar for the tree view
     * 
     * @param   {<toolbar>} toolbar The toolbar element to wrap
     * @note    This conforms to requirements for a xtk.hierarchicalTreeView row
     */
    function Toolbar(toolbar) {
        if (toolbar.getAttribute("customizable") == "true") {
			var ko = window.opener.ko;
            this.children = Array.slice(toolbar.querySelectorAll("toolbarbutton"))
                                 .filter(function(n) /^toolbar/.test(n.localName) &&
                                                     !!n.id)
                                 .sort(sortComparator)
                                 .map(function(n) new ToolbarItem(n));
        } else {
            // this toolbar shouldn't be customizable
            this.children = [];
        }
        this.elem = toolbar;
        this.original = {"hidden": this.elem.getAttribute("kohidden"),
                         "ordinal": this.elem.hasAttribute("ordinal") ?
                                        this.elem.getAttribute("ordinal") : null};
        this._id = this.elem.id;
    }
    Toolbar.prototype.isContainer = true;
    Toolbar.prototype.__defineGetter__("hasChildren",
                                       function() this.children.length > 0);
    Toolbar.prototype.getChildren = function() Array.slice(this.children);
    Toolbar.prototype.state = 0;
    Toolbar.prototype.level = 0;

    // initialize the tree
    if ("arguments" in window && window.arguments[0]) {
        // dialog
        view = new ToolboxTreeView(window.arguments[0]);
    } else {
        // sheet
        view = new ToolboxTreeView(window.frameElement.toolbox);
    }
    tree.view = view;

    // add a hook for toggling with the keyboard
    tree.addEventListener("keypress", function(event) {
        if (event.charCode == " ".charCodeAt(0)) {
            var col = tree.columns.getNamedColumn("colCheck");
            view.cycleCell(tree.currentIndex, col);
            tree.boxObject.invalidate();
        }
    }, false);

    tree.addEventListener("dragstart", function(event) {
        if (!view.selection.single || !view.selection.getRangeCount()) {
            return;
        }
        var item =  view._rows[view.selection.currentIndex];
        if (!(item instanceof Toolbar) || !item.elem.hasAttribute("can-drag")) {
            return;
        }
        event.dataTransfer.mozSetDataAt("komodo/toolbar-customize-tree",
                                        view._rows[view.selection.currentIndex],
                                        0);
    }, false);

    // Fix up buttons for instant apply
    var isInstantApply = false;
    try {
        isInstantApply = Services.prefs.getBoolPref("browser.preferences.instantApply");
    } catch (e) {
        // failed to get pref, use default
    }
    var dialogElem = document.documentElement;
    dialogElem.getButton("cancel").hidden = isInstantApply;
    if (isInstantApply) {
        // Copy the label over from extra1. We do this with the accept button to
        // make sure we don't revert the changes when we close.
        dialogElem.getButton("accept").label = dialogElem.getButton("extra1").label;
    }

    // Tell the caller we're all done
    if (window.frameElement) {
        var event = new CustomEvent("ready", { bubbles: true, cancelable: false});
        window.frameElement.dispatchEvent(event);
    }

}, false);

/**
 * Toolbar customization is finished, the dialog is about to close
 * @param aAccept {boolean} Whether the customization was accepted
 */
function onCustomizeToolbarFinished(aAccept) {
    try {
        if (Services.prefs.getBoolPref("browser.preferences.instantApply")) {
            // instantApply is on; it's always accepted.
            aAccept = true;
        }
    } catch (e) {
        // ignore errors in getting the instantApply pref; assume false.
    }

    var tree = document.getElementById("toolbarTree");
    var view = tree.view.wrappedJSObject;
    var objs = [].concat.apply(view._toolbars,
                               view._toolbars.map(function(r) r.children));
    for each (var obj in objs) {
        if ("elem" in obj && "original" in obj) {
            if (!aAccept) {
                obj.elem.setAttribute("kohidden", obj.original.hidden);
                if (obj.original.ordinal === null) {
                    obj.elem.removeAttribute("ordinal");
                } else {
                    obj.elem.setAttribute("ordinal", obj.original.ordinal);
                }
            }
            obj.elem.ownerDocument.persist(obj.elem.id, "kohidden");
        }
    }
    // Also hide all toolbars with no visible children
    for each (var toolbar in view._toolbars) {
        if (toolbar.elem.getAttribute("kohidden") == "true") {
            continue;
        }
        var visible = toolbar.children.some(function(item) {
            return item.elem.getAttribute("kohidden") != "true";
        });
        if (!visible) {
            toolbar.elem.setAttribute("kohidden", "true");
        }
    }
    // Force reflow :| (This works around problems where many elements without
    // ordinal= can be in an unexpected order.)
    view._toolbox.style.direction = "rtl";
    view._toolbox.boxObject.height;
    view._toolbox.style.direction = "";

    // Call the customization complete callback
    // This needs to be fired from here because if the caller just listened to
    // "dialogaccept"/"dialogcancel" they will fire before we do (so they will
    // see the wrong states for the toolbars).
    var callback = null;
    if ("arguments" in window && window.arguments[1]) {
        // dialog
        callback = window.arguments[1];
    } else {
        // sheet
        callback = window.frameElement.onCustomizeFinished;
    }
    if (callback) {
        try {
            callback();
        } catch (e) {
            Components.utils.reportError(e);
            // don't propagate the exception, we still need to close
        }
    }
}
