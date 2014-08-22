// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

var gObj;
var widgets = {};
var updateEnabledAddService_ID = 0;

function fillMenu(menupopup, numInstances) {
  while (menupopup.firstChild) {
    menupopup.removeChild(menupopup.firstChild);
  }
  var menuitem;
  menuitem = document.createElement("menuitem");
  menuitem.setAttribute("label", "*");
  menupopup.appendChild(menuitem);
  for (var i = 1; i <= numInstances; i++) {
      menuitem = document.createElement("menuitem");
      menuitem.setAttribute("label", i);
      menupopup.appendChild(menuitem);
  }
  menupopup.parentNode.value = "*";
}

function onLoad() {
  gObj = window.arguments[0];
  var results = gObj.results;
  for each (var name in ["path",
                         "showAll",
                         "instance",
                         "instance_menupopup"
                         ]) {
          widgets[name] = document.getElementById(name);
      }
  var numInstances = gObj.numInstances;
  if (numInstances == 1) {
      widgets.instance.disabled = true;
  } else {
      fillMenu(widgets.instance_menupopup, gObj.numInstances);
  }
}

function onChecked() {
    widgets.path.focus();
}
          
function onOK() {
    try {
  var results = gObj.results;
  var selectedItem = widgets.instance.selectedItem;
  if (selectedItem && selectedItem.label) {
      results.instanceNum = (selectedItem.label == "*"
                             ? "*"
                             : (selectedItem.label - 1));
  } else {
      results.instanceNum = null;
  }
  results.path = widgets.path.value;
  results.showAll = widgets.showAll.checked;
  return true;
    } catch(ex) {
        dump("onOK: " + ex + "\n");
        return true;
    }
}
function onCancel() {
  return true;
}
