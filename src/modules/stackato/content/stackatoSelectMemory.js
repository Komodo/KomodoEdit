// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

var gObj;
var widgets = {};

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://stackatotools/locale/stackato.properties");

function onLoad() {
  gObj = window.arguments[0];
  widgets.memoryLimit = document.getElementById("memoryLimit");
  var currentMemoryLimit = gObj.memoryLimit;
  if (currentMemoryLimit) {
      widgets.memoryLimit.value = currentMemoryLimit;
  }
}

function onOK() {
    var memoryLimit = widgets.memoryLimit.value;
    if (memoryLimit) {
        gObj.newMemoryLimit = memoryLimit;
    } else {
        gObj.newMemoryLimit = null;
    }
    return true;
}

function onCancel() {
    gObj.newMemoryLimit = null;
    return true;
}
