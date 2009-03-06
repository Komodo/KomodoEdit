/* Copyright (c) 2009 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Fast open functionality.
 *
 * Defines the "ko.fastopen" namespace.
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}

ko.fastopen = {};
(function() {

    var log = ko.logging.getLogger("fastopen");


    //---- public interface

    this.open_gotofile_dialog = function open_dialog() {
        var obj = new Object();
        ko.windowManager.openDialog("chrome://fastopen/content/gotofile.xul",
            "dialog-gotofile",
            "chrome,modal,centerscreen,titlebar,resizable=yes",
            obj);
    }


    //---- support routines

    //this.switch_to_open_view = function switch_to_open_view(pattern) {
    //    // Find the matching views.
    //    var i, view, name, type;
    //    var views = _get_view_mgr().topView.getViews(true);
    //    var matches = [];
    //    var norm_pattern = pattern.toLowerCase();
    //    for (i = 0; i < views.length; ++i) {
    //        view = views[i];
    //        type = view.getAttribute("type")
    //        switch (type) {
    //        case "tabbed":
    //            name = null;
    //            break;
    //        case "browser":
    //        case "editor":
    //        case "diff":
    //            name = view.document.displayPath;
    //            break;
    //        case "startpage":
    //            name = "Start Page";
    //            break;
    //        default:
    //            log.debug("unexpected view type: '"+type+"' (ignoring)")
    //            name = null;
    //        }
    //        if (name && name.toLowerCase().indexOf(norm_pattern) != -1) {
    //            matches.push({"name": name, "type": type, "view": view});
    //        }
    //    }
    //    
    //    // Open the matching views if any.
    //    if (matches.length == 0) {
    //        return "no open views match '"+pattern+"'";
    //    } else if (matches.length == 1) {
    //        matches[0].view.makeCurrent();
    //    } else {
    //        function pick_name(match) {
    //            return match.name;
    //        }
    //        var selection = ko.dialogs.selectFromList(
    //            "Select View to Open", //title
    //            "Multiple open views match your pattern. Select the one "
    //                +"you'd like to switch to.", // prompt
    //            matches, // items
    //            "one", // selectionCondition
    //            pick_name); // stringifier
    //        if (selection) {
    //            selection[0].view.makeCurrent();
    //        } else {
    //            return "";
    //        }
    //    }
    //    return null;
    //}

    //function _get_view_mgr() {
    //    return ko.views.manager;
    //}

}).apply(ko.fastopen);

