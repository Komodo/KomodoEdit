// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

var gObj;
var widgets = {};
var updateEnabledAddService_ID = 0;

function fillMenu(menupopup, names, defaultValue) {
  while (menupopup.firstChild) {
    menupopup.removeChild(menupopup.firstChild);
  }
  var menuitem;
  for each (var name in names) {
      menuitem = document.createElement("menuitem");
      menuitem.setAttribute("label", name);
      menupopup.appendChild(menuitem);
  }
  menupopup.parentNode.value = defaultValue;
}

function onLoad() {
  gObj = window.arguments[0];
  var results = gObj.results;
  for each (var name in ["systemServices_menupopup",
                         "new_provisioned_service_name",
                         "system_services"
                         ]) {
          widgets[name] = document.getElementById(name);
      }
  fillMenu(widgets.systemServices_menupopup,
           gObj.stackato.systemServiceNames,
           results.systemServices || "");
  widgets.new_provisioned_service_name.addEventListener("keypress",
      queueUpdateEnabledAddService, false);
  updateEnabledAddService();
}
          
function onShutdown() {
  widgets.new_provisioned_service_name.removeEventListener("keypress", queueUpdateEnabledAddService, false);
}

function onOK() {
  var results = gObj.results;
  var selectedItem = widgets.system_services.selectedItem;
  if (selectedItem && selectedItem.label) {
      results.baseServiceName = selectedItem.label;
  } else {
      results.baseServiceName = null;
  }
  results.provisionedServiceName = widgets.new_provisioned_service_name.value;
  onShutdown();
  return true;
}
function onCancel() {
  onShutdown();
  return true;
}

function generateName_aux(serviceName) {
    // Favor certain letters in suggested names over others.
    var letters = "aaaaabbbbbcccccdddddeeffffgggghhhhhijjjkkklmmmnnnopppqqqrrrssstttuuvvvwwxxxyzzz";
    var digits = "0123456789";
    var rand = Math.random
    var results = [serviceName, "-"];
    results.push(letters[Math.floor(Math.random() * letters.length)]);
    for (var i = 4; i > 0; i--) {
        results.push(digits[Math.floor(Math.random() * digits.length)]);
    }
    return results.join("");
}

function generateName(serviceName) {
    var existingServiceNames = gObj.stackato.provisionedServiceNames;
    var candidate;
    for (var i = 10; i > 0; i--) {
        candidate = generateName_aux(serviceName);
        if (!~existingServiceNames.indexOf(candidate)) {
            return candidate;
        }
        dump("Have collision with " + candidate + ", try another\n");
    }
    return candidate;
}

function onMenuitemChanged(menulist) {
    var textbox = widgets.new_provisioned_service_name;
    var serviceName = menulist.selectedItem.label;
    textbox.value = generateName(serviceName);
    updateEnabledAddService();
    textbox.select();
}
                                   
function queueUpdateEnabledAddService() {
    if (updateEnabledAddService_ID) {
        clearTimeout(updateEnabledAddService_ID);
    }
    updateEnabledAddService_ID = setTimeout(updateEnabledAddService, 400);
}

function updateEnabledAddService() {
    var disableOk;
    if (!widgets.new_provisioned_service_name.value) {
        disableOk = true;
    } else if (!widgets.system_services.selectedItem
               || !widgets.system_services.selectedItem.label) {
        disableOk = true;
    } else {
        disableOk = false;
    }
    document.documentElement.getButton("accept").disabled = disableOk;
}


