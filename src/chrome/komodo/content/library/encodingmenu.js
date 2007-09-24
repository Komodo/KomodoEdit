/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */


if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.widgets)=='undefined') {
    ko.widgets = {};
}

(function() {

this.getEncodingPopup = function encodingMenu_buildHierarchy(hierarchy, toplevel, action)  {
    const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
    var menu;
    var menupopup;
    var menuitem;
    var children = new Object();
    var count = new Object();
    var i;

    if (hierarchy.container == true)  {
        // build menu
        menupopup = document.createElementNS(XUL_NS, 'menupopup');
        menupopup.setAttribute('class','menulist-menupopup');
        hierarchy.getChildren(children, count);
        children = children.value;

        for (i=0;i<children.length;i++)  {
            menupopup.appendChild(ko.widgets.getEncodingPopup(children[i], false, action));
        }
        if (!toplevel)  {
            menu = document.createElementNS(XUL_NS, 'menu');
            menu.setAttribute('class', 'menulist-subLevel');
            menu.setAttribute('label', hierarchy.name);
            menu.appendChild(menupopup);
            return menu;
        }
        return menupopup;
    }

    var obj = hierarchy.item_object;
    menuitem = document.createElementNS(XUL_NS, 'menuitem');
    menuitem.setAttribute('data', obj.python_encoding_name);
    menuitem.setAttribute('label', hierarchy.name);
    menuitem.setAttribute('oncommand', action);
    return menuitem;
}

}).apply(ko.widgets);

