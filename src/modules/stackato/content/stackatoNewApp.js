// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

var gObj;
var widgets = {};
var wizardPages = {};
var appNameChanged_ID = 0;
var updateEnabledOK_ID = 0;
var updateEnabledAddService_ID = 0;
var urlExplicitlyUpdated = false;
var finalDataItems = {};
var log;

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://stackatotools/locale/stackato.properties");

function fillMenu(menupopup, names, defaultValue) {
  while (menupopup.firstChild) {
    menupopup.removeChild(menupopup.firstChild);
  }
  var menuitem;
  for each (var name in names) {
      menuitem = document.createElement("menuitem");
      menuitem.setAttribute("label", name);
      menuitem.setAttribute("id", menupopup.parentNode.id + "_" + name);
      menupopup.appendChild(menuitem);
  }
  menupopup.parentNode.value = defaultValue;
}


function initWizard() {
  gObj = window.arguments[0];
  log = gObj.gko.logging.getLogger("stackatoNewApp");
  for each (var name in ["appname", "path", "url", "numInstances",
                         "memoryLimit", "startImmediately",
                         "runtime_menupopup",
                         "framework", "framework_menupopup",
                         "provisioned_services", // menulist
                         "provisionedService_menupopup", // menupopup
                         "systemServices_menupopup",
                         "runtime", "runtime_menupopup",
                         "provisionedServices",
                         "new_provisioned_service_name",
                         "new_provisioned_button",
                         "system_services",
                         "getNewAppWizard",
                         "outlineCreationParameters"
                         ]) {
          widgets[name] = document.getElementById(name);
      }
  ["page1_addApp_define", "page2_addApp_serviceChoicePage",
   "page3_addApp_defineNewServicePage", "page4_addApp_addExistingServicePage",
   "page5_addApp_reviewAndFinish"].forEach(function(name) {
      wizardPages[name] = document.getElementById(name);
  });
  fillMenu(widgets.framework_menupopup,
           gObj.stackato.frameworkNames, "");
  fillMenu(widgets.runtime_menupopup,
           gObj.stackato.runtimeNames, "");
  fillMenu(widgets.provisionedService_menupopup,
           gObj.stackato.provisionedServiceNames, "");
  fillMenu(widgets.systemServices_menupopup,
           gObj.stackato.systemServiceNames, "");
  if (!widgets.path.value) {
    var gko = gObj.gko;
    var project = gko.projects.manager.currentProject;
    if (project && project.importDirectoryLocalPath) {
        widgets.path.value = project.importDirectoryLocalPath;
    } else if (gko.places && gko.places.manager.currentPlaceIsLocal) {
        widgets.path.value = gko.uriparse.URIToLocalPath(gko.places.manager.currentPlace);
    }
    if (widgets.path.value) {
        var config = processConfigFile(widgets.path.value);
        if (config !== null) {
            [['name', 'appname'], ['mem', 'memoryLimit'],
             ['instances', 'numInstances']].forEach(function(pair) {
                var configName = pair[0];
                if (configName in config && config[configName]) {
                    widgets[pair[1]].value = config[configName];
                    if (configName == 'name') {
                        onAppNameUpdated();
                    }
                }
             });
            var selectItem = function(menulist, menupopup, valueToFind) {
                var idx = Array.slice(menupopup.children).map(function(elt) elt.label).indexOf(valueToFind);
                if (idx >= 0) {
                    menulist.selectedIndex = idx;
                }
            };
            var menulist, menupopup;
            if (config.framework) {
                if (config.framework.type) {
                    selectItem(widgets.framework, widgets.framework_menupopup,
                               config.framework.type);
                }
                if (config.framework.runtime) {
                    selectItem(widgets.runtime, widgets.runtime_menupopup,
                               config.framework.runtime);
                }
            }
            if (config.service) {
                selectItem(widgets.provisioned_services,
                           widgets.provisionedService_menupopup,
                           config.service);
                widgets.provisioned_services.value = config.service;
            }
        }
    }
  }
  updateEnabledOK();
}

function onLoad() {
  if (!widgets.path) {
      initWizard();
  }
}

function onPage1_Show() {
  try {
  if (!widgets.path) {
      initWizard();
  }
  for each (var name in ["appname", "path", "url", "numInstances",
                         "memoryLimit",]) {
          widgets[name].addEventListener("keypress", queueUpdateEnabledOK, false);
      }
  updateEnabledOK();
  widgets.appname.addEventListener("keypress", wrapOnAppNameUpdated, false);
  widgets.url.addEventListener("keypress", onUrlUpdated, false);
  } catch(ex) {
      log.exception(ex, "onPage1_Show");
  }
  return true;
}

function processConfigFile(path) {
    var os = Components.classes["@activestate.com/koOs;1"].getService();
    var ospath = os.path;
    var checkFullPath = function() {
        var configPath = ospath.join(path, 'stackato.yml');
        if (ospath.exists(configPath)) return configPath;
        configPath = ospath.join(path, 'stackato.yaml');
        if (ospath.exists(configPath)) return configPath;
        return null;
    };      
    var fullpath = checkFullPath();
    if (!fullpath) {
        return null;
    }
    var contents = os.readfile(fullpath);
    if (!contents) {
        return null;
    };
    return simpleYamlParser(contents);
};

function simpleYamlParser(contents) {
    // We only care about a few things:
    // app name (name:)
    // framework/runtime
    // mem
    // instances

    var config = {};
    var i, j, idx, lim, line, m, pos;
    var lines = contents.split(/\r?\n/);
    lim = lines.length;
    var singleNames = ['name', 'mem', 'instances'];
    var thisSingleName;
    for (i = 0; i < lim; i++) {
        line = lines[i];
        m = /^(\w+):\s*(\S.*?)\s*$/.exec(line);
        if (m && (idx = singleNames.indexOf(m[1])) != -1) {
            config[m[1]] = m[2];
        } else if (line.indexOf("framework:") == 0) {
            i += 1;
            config.framework = {};
            while (i < lim) {
                line = lines[i];
                if (/^\s*#/.test(line) || /^\s*$/.test(line)) {
                    // Skip comments and empty lines
                    i += 1;
                } else {
                    m = /\s+(\w+):\s*(\S.*?)\s*$/.exec(line);
                    if (m) {
                        if (m[1] == 'type' || m[1] == 'runtime') {
                            config.framework[m[1]] = m[2];
                            i += 1;
                        }
                    } else {
                        i -= 1; // retry this line at top of loop
                        break;
                    }
                }
            }
        } else if (line.indexOf("services:") == 0) {
            i += 1;
            while (i < lim) {
                line = lines[i];
                if (/^\s*#/.test(line) || /^\s*$/.test(line)) {
                    // Skip comments and empty lines
                    i += 1;
                } else {
                    m = /\s+\S.*?:\s*(\S.*?)\s*$/.exec(line);
                    if (m) {
                        config.service = m[1];
                    } else {
                        i -= 1; // retry this line at top of loop
                    }
                    break;
                }
            }
        }
    }
    return config;
}

function onPage1_Next() {
    try {
        if (!widgets.getNewAppWizard.canAdvance) {
            log.debug("onPage1_Next: can't advance!\n");
            return false;
        }
        clearPage1();
        ["appname", "path", "url", "numInstances", "memoryLimit"].forEach(function(name) {
                finalDataItems[name] = widgets[name].value;
            });
        finalDataItems.startImmediately = widgets.startImmediately.checked;
        var rt = widgets.runtime;
        if (!rt.selectedItem) {
            finalDataItems.runtime = null;
        } else {
            finalDataItems.runtime = rt.selectedItem.label;
        }
        rt = widgets.framework;
        if (!rt.selectedItem) {
            finalDataItems.framework = null;
        } else {
            finalDataItems.framework = rt.selectedItem.label;
        }
    } catch(ex) {
        log.exception(ex, "onPage1_Next error");
    }
    return true;
}

function onPage2_Show() {
    var descr = document.getElementById("offerToBindService");
    while (descr.firstChild) {
        descr.removeChild(descr.firstChild);
    }
    var s = bundle.formatStringFromName("Would you like to add a data service for X",
                                        [widgets.appname.value], 1);
    descr.appendChild(document.createTextNode(s));
    return true;
}

var nextPage_from_serviceChoice = {
    "chooseService_noService": "page5_addApp_reviewAndFinish",
    "chooseService_existingService": "page4_addApp_addExistingServicePage",
    "chooseService_defineNewService": "page3_addApp_defineNewServicePage"
};
function onPage2_Next() {
    var serviceChoice = document.getElementById("serviceGroup").selectedItem.id;
    var nextPage = nextPage_from_serviceChoice[serviceChoice];
    if (nextPage) {
        wizardPages.page2_addApp_serviceChoicePage.setAttribute("next", nextPage);
    } else {
        log.debug("No nextPage_from_serviceChoice for "
             + serviceChoice
             + "\n");
    }
    return true;
}


//================================================================

// Define a new service here.  If we go with it, stay on this page
// until it's defined.

function onPage3_Show() {
    widgets.getNewAppWizard.canAdvance = !!finalDataItems.provisionedService;
  widgets.new_provisioned_service_name.addEventListener("keypress",
      queueUpdateEnabledAddService, false);
}

function onPage3_Next() {
    clearPage3();
    var serviceName = widgets.new_provisioned_service_name.value;
  if (serviceName) {
      finalDataItems.provisionedService = serviceName;
  } else {
      delete finalDataItems.provisionedService;
  }
  return true;
}

function onPage3_Rewound() {
    delete finalDataItems.provisionedService;
  return true;
}

function onPage4_Show() {
    var menulist = widgets.provisioned_services;
    if (menulist.itemCount == 0) {
        menulist.disabled = true;
        widgets.getNewAppWizard.canAdvance = false;
        //XXX: Show a description field that there are no prov services.
        //     Go back and define one, or specify no database is needed.
    } else {
        menulist.selectedIndex = 0;
        widgets.getNewAppWizard.canAdvance = true;
    }
}

function onPage4_Next() {
  var serviceName = widgets.provisioned_services.label;
  if (serviceName) {
      finalDataItems.provisionedService = serviceName;
  } else {
      delete finalDataItems.provisionedService;
  }
  return true;
}

function onPage4_Rewound() {
    delete finalDataItems.provisionedService;
  return true;
}

function onPage5_Show() {
    var outlineCreationParameters = widgets.outlineCreationParameters;
    while (outlineCreationParameters.firstChild) {
        outlineCreationParameters.removeChild(outlineCreationParameters.firstChild);
    }
    var nodes = [];
    var prompt = bundle.GetStringFromName("The directory containing the application");
    nodes.push(bundle.GetStringFromName("Here are the parameters youve selected.Colon"));
    nodes.push(bundle.GetStringFromName("Application name.Colon") + " "  + finalDataItems.appname);
    nodes.push(bundle.GetStringFromName("Path.Colon") + " " + finalDataItems.path);
    nodes.push(bundle.GetStringFromName("URL.Colon") + " " + finalDataItems.url);
    nodes.push(bundle.GetStringFromName("Num Instances.Colon") + " " + finalDataItems.numInstances);
    nodes.push(bundle.GetStringFromName("Memory Limit.Colon") + " " + finalDataItems.memoryLimit);
    nodes.push(bundle.GetStringFromName("Runtime.Colon")
               + " "
               + (finalDataItems.runtime
                  || bundle.GetStringFromName("None")));
    nodes.push(bundle.GetStringFromName("Provisioned Service.Colon")
               + " "
               + (finalDataItems.provisionedService
                  || bundle.GetStringFromName("None")));
    nodes.push(bundle.GetStringFromName("Start immediately.Colon") + " " + finalDataItems.startImmediately);
    var d, s;
    nodes.forEach(function(item) {
            s = document.createTextNode(item);
            d = document.createElement("description");
            d.appendChild(s);
            outlineCreationParameters.appendChild(d);
        });
}

function doFinish() {
  var results = gObj.results;
  // Names:
  // appname path url mem instances runtime startImmediately
  ["appname", "path", "url", "numInstances", "memoryLimit",
   "startImmediately", "runtime",
   "framework",
   "provisionedService"].forEach(function(name) {
          results[name] = finalDataItems[name];
      });
  results.instances = finalDataItems.numInstances;
  results.mem = finalDataItems.memoryLimit;
    doShutdown();
  return true;
}

function clearPage1() {
    try {
  for each (var name in ["appname", "path", "url", "numInstances",
                         "memoryLimit",]) {
          widgets[name].removeEventListener("keypress", queueUpdateEnabledOK, false);
      }
  widgets.appname.removeEventListener("keypress", wrapOnAppNameUpdated, false);
  widgets.url.removeEventListener("keypress", onUrlUpdated, false);
  if (updateEnabledOK_ID) {
      clearTimeout(updateEnabledOK_ID);
  }
  } catch(ex) {
        log.exception(ex, "onPage1_Next");
  }
}

function clearPage3() {
  widgets.new_provisioned_service_name.removeEventListener("keypress", queueUpdateEnabledAddService, false);
}

function doShutdown() {
    clearPage1();
    clearPage3();
}

function onCancel() {
    doShutdown();
  return true;
}

function onWizardBack() {
    // If we moved forward at one point, then when we move back,
    // we should always be able to move forward again.
    widgets.getNewAppWizard.canAdvance = true;
}

function browsePath() {
    var prompt = bundle.GetStringFromName("The directory containing the application");
    var res = gObj.gko.filepicker.getFolder(widgets.path.value, prompt);
    if (res) {
        widgets.path.value = res;
    }
    window.focus();
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
        log.debug("Have collision with " + candidate + ", try another\n");
    }
    return candidate;
}

function onMenuitemChanged(menulist) {
    hideNewServiceDescription(true);
    var textbox = widgets.new_provisioned_service_name;
    var serviceName = menulist.selectedItem.label;
    textbox.value = generateName(serviceName);
    updateEnabledAddService();
    textbox.select();
}

function queueUpdateEnabledOK() {
    if (updateEnabledOK_ID) {
        clearTimeout(updateEnabledOK_ID);
    }
    updateEnabledOK_ID = setTimeout(updateEnabledOK, 400);
}

function onUrlUpdated() {
    urlExplicitlyUpdated = true;
    widgets.url.removeEventListener("keypress", onUrlUpdated, false);
    widgets.appname.removeEventListener("keypress", wrapOnAppNameUpdated, false);
}

function wrapOnAppNameUpdated() {
    // Let the field get updated.
    if (appNameChanged_ID) {
        clearTimeout(appNameChanged_ID);
    }
    appNameChanged_ID = setTimeout(onAppNameUpdated, 100);
}

function onAppNameUpdated() {
    appNameChanged_ID = 0;
    var currentURL = widgets.url.value;
    var appName = widgets.appname.value;
    if (appName.length === 0) {
        widgets.url.value = "";
    } else {
        var target = gObj.currentTarget.substr(gObj.currentTarget.indexOf("."));
        if (!currentURL || currentURL.indexOf(target) >= 0) {
            widgets.url.value = appName + target;
        }
    }
}

function queueUpdateEnabledAddService() {
    if (updateEnabledAddService_ID) {
        clearTimeout(updateEnabledAddService_ID);
    }
    updateEnabledAddService_ID = setTimeout(updateEnabledAddService, 400);
}


function updateEnabledAddService() {
    var disableAddService;
    if (!widgets.new_provisioned_service_name.value) {
        disableAddService = true;
    } else if (!widgets.system_services.selectedItem
               || !widgets.system_services.selectedItem.label) {
        disableAddService = true;
    } else {
        disableAddService = false;
    }
    widgets.new_provisioned_button.disabled = disableAddService;
}

function updateEnabledOK() {
    try {
    var disableOk = false;
    for each (var name in ["appname", "path", "url", "numInstances",
                           "memoryLimit"]) {
            if (!widgets[name].value) {
                disableOk = true;
                break;
            }
        }
    if (!disableOk) {
        disableOk = (!widgets.runtime.selectedItem
                     || !widgets.runtime.selectedItem.label
                     || !widgets.runtime.selectedItem
                     || !widgets.runtime.selectedItem.label);
    }
    widgets.getNewAppWizard.canAdvance = !disableOk;
    } catch(ex) {
        log.exception(ex, "updateEnabledOK");
    }
}

function hideNewServiceDescription(hideIt) {
    document.getElementById("new-service-description").setAttribute("hidden", hideIt ? "true" : "false");
}

function onNewServiceNameFocused() {
    hideNewServiceDescription(true);
}

function addProvisionedService() {
    hideNewServiceDescription(false);
    var textbox = widgets.new_provisioned_service_name;
    var serviceName = widgets.system_services.selectedItem.label;
    var provisionedServiceName = textbox.value;
    var icon = document.getElementById("new-service-icon");
    var outerCallback = function() {
        try {
            fillMenu(widgets.provisionedService_menupopup,
                     gObj.stackato.provisionedServiceNames,
                     provisionedServiceName);
            icon.setAttribute("class", "user-icon");
        } catch(ex) {
        }
    };
    var callback = function() {
        if (finalDataItems.provisionedService) {
            widgets.getNewAppWizard.canAdvance = true;
            try {
                // Update the list of service names
                gObj.stackato._updateProvisionedServicesTable(outerCallback,
                                                              "provisioned_services_button");
            } catch(ex) {
                log.exception(ex, "addProvisionedService: failed");
            }
        } else {
            icon.setAttribute("class", "user-icon");
        }
    };

    var handleTarget = {
      setData: function(data) {
        finalDataItems.provisionedService = widgets.new_provisioned_service_name.value;
      }
    };
    // 'document' in stackato.js points to the parent, not this window.
    icon.setAttribute("class", "async_operation");
    gObj.stackato.wrapCallbackFunction("runCommand",
                                       null, // handle async here.
                                       handleTarget,
                                       callback,
                                       false, // no JSON
                                       ["create-service", serviceName, provisionedServiceName],
                                       true);
};
