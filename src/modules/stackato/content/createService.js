/* Copyright (c) 2003-2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var widgets = {};
var g_obj;

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://stackatotools/locale/stackato.properties");

function populateMenuList(menulist, strings) {
    while (menulist.firstChild) {
        menulist.removeChild(menulist.firstChild);
    }
    var menupopup = document.createElement("menupopup");
    if (strings.length == 0) {
        menulist.disabled = true;
        strings = [bundle.GetStringFromName("no values provided")];
    } else {
        menulist.disabled = false;
    }
    menulist.appendChild(menupopup);
    var string_pairs = strings.map(function(s) [s.toLowerCase(), s]);
    string_pairs.sort();
    var sorted_strings = string_pairs.map(function(pair) pair[1]);
    sorted_strings.forEach(function(s) {
        var menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", s);
        menuitem.setAttribute("data", s);
        menupopup.appendChild(menuitem);
    });
    menulist.value = sorted_strings[0];
    menulist.selectedIndex = 0;
}

function onLoad() {
    widgets.service = document.getElementById("service");
    widgets.appname = document.getElementById("appname");
    widgets.serviceInstanceNameMenu = document.getElementById("serviceInstanceNameMenu");
    widgets.serviceInstanceName = document.getElementById("serviceInstanceName");
    g_obj = window.arguments[0];
    populateMenuList(widgets.service, g_obj.serviceNames);
    populateMenuList(widgets.appname, g_obj.appNames);
    onSelectService({}, widgets.service);
}

function onSelectServiceInstanceName(event, obj) {
    g_obj.selectedObj = obj;
    widgets.serviceInstanceName.value = obj.selectedItem.label;
}

function onSelectService(event, obj) {
    var selectedServiceName = obj.selectedItem.label;
    var names = g_obj.provisionedServiceNamesByService[selectedServiceName];
    if (names && names.length) {
        populateMenuList(widgets.serviceInstanceNameMenu, names);
    } else {
        dump("**** no names \n");
        populateMenuList(widgets.serviceInstanceNameMenu, [selectedServiceName]);
    }
    widgets.serviceInstanceName.value = obj.selectedItem.label;
}

function onOk() {
    g_obj.retVal = true;
    g_obj.selectedAppName = widgets.appname.selectedItem.label;
    g_obj.selectedService = widgets.service.selectedItem.label;
    g_obj.selectedServiceInstanceName = widgets.serviceInstanceName.value;
    return true;
}

function onCancel() {
    g_obj.retVal = false;
    return true;
}
