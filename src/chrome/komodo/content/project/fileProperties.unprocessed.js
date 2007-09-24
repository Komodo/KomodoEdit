var gItem; // used by Apply to effect renames
var gApply, gOKButton;
var gNameField;
var observerSvc;

function onLoad() {
    try {
        var item = window.arguments[0].item;
        window.screenX += 20 * window.arguments[0].offsetIndex;
        window.screenY += 20 * window.arguments[0].offsetIndex;
        var type = item.type;
        var dialog = document.getElementById("dialog-fileproperties")
        gApply = dialog.getButton("extra1");
        gApply.setAttribute('label', 'Apply');
        gApply.setAttribute('accesskey', 'a');
        gOKButton = dialog.getButton("accept");

        type = type[0].toUpperCase() + type.slice(1);
        if (item.url) {
            document.title = type + " Properties for " + ko.uriparse.baseName(item.url);
        } else {
            document.title = type + " Properties for " + item.name;
        }
        if (item.url) {
            // Force a refresh
            observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                              getService(Components.interfaces.nsIObserverService);
            observerSvc.notifyObservers(this,'file_status_now',item.url);
        }
        gNameField = document.getElementById('nameField');
        gItem = item;
        UpdateFields(item);
        updateApply();
    } catch (e) {
        log.error(e);
    };
};

function roundDigits (n,d) {
    n = Math.round(n * 100) / 100;
    n = (n + 0.001) + '';
    return n.substring(0, n.indexOf('.') + d);
}

function getSize(item) {
    var file = item.getFile();
    var numbytes = file.size;
    var size;
    if (numbytes < 1024) {
        return numbytes + ' bytes';
    } else if (numbytes < 1024*1024) {
        size = Math.ceil(numbytes / 1024);
        return size + ' K (' + numbytes  + ' bytes)';
    } else {
        size = roundDigits(size / (1024 * 1024),2);
        return size + 'MB (' + numbytes  + ' bytes)';
    }
}
function getDateTimeString(datetime) {
    if (typeof(datetime) == 'undefined' || !datetime) {
        return "N/A";
    }
    // XXX not localization friendly
    var now = new Date();
    var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    var mins = datetime.getMinutes();
    if (mins.toString().length == 1)  {
        mins = '0' + mins;
    }
    var hours = datetime.getHours();
    var fulltime;
    if (hours > 12)  {
        hours = hours-12;
        fulltime = hours.toString() + ':' + mins + " PM";
    }
    else  {
        fulltime = hours.toString() + ':' + mins + " AM";
    }
    var dtstring;
    if (datetime.getFullYear() == now.getFullYear() &&
        datetime.getMonth() == datetime.getMonth() &&
        now.getDate() == datetime.getDate()) {
            dtstring = 'Today, at ' + fulltime;
    } else {
        dtstring = datetime.getDate() + ' ' + months[datetime.getMonth()] + ', ' + datetime.getFullYear() + ', ' + fulltime;
    }
    return dtstring;
}

function UpdateFields(item)  {
    var url = '';
    var path = '';
    var file = item.getFile();
    var sizeStr = "Not Available";
    var ctimeStr = "Not Available";
    var mtimeStr = "Not Available";
    var atimeStr = "Not Available";
    var initiallyWriteable = false;
    var accessible = false;
    var name = item.name;
    if (file) {
        url = file.URI;
        path = file.displayPath;
        initiallyWriteable = file.isWriteable;
        accessible = false;
        if (file.exists)  {
            // Size info.
            sizeStr = file.fileSize + " bytes";
            if (file.isLocal) {
                accessible = true; // XXX Should use mythical good "access" call
            }
            // Time info.
            var timeSvc = Components.classes["@activestate.com/koTime;1"].
                            getService(Components.interfaces.koITime);
            var prefSvc = Components.classes['@activestate.com/koPrefService;1'].
                            getService(Components.interfaces.koIPrefService);
            var format = prefSvc.prefs.getStringPref("defaultDateFormat");
            var timeTuple;
            timeTuple = timeSvc.localtime(file.createdTime, new Object());
            ctimeStr = timeSvc.strftime(format, timeTuple.length, timeTuple);
            timeTuple = timeSvc.localtime(file.lastModifiedTime, new Object());
            mtimeStr = timeSvc.strftime(format, timeTuple.length, timeTuple);
            timeTuple = timeSvc.localtime(file.lastAccessedTime, new Object());
            atimeStr = timeSvc.strftime(format, timeTuple.length, timeTuple);
        }

        // Update UI with data.
        name = file.leafName;
        document.getElementById('sizeField').value = sizeStr;

        if (path != "") {
            document.getElementById('locationField').value = file.displayPath;
            document.getElementById('createdField').value = ctimeStr;
            document.getElementById('modifiedField').value = mtimeStr;
            document.getElementById('accessedField').value = atimeStr;
        } else {
            document.getElementById('locationField').value = "Unsaved";
            document.getElementById('createdField').value = "Unsaved";
            document.getElementById('modifiedField').value = "Unsaved";
            document.getElementById('accessedField').value = "Unsaved";
        }
        var rwCheckbox = document.getElementById('rwCheckbox');
        /* XXX bug 41719, removing the disabled allows the user to change
          this setting, however, no code implements changing this from
          this dialog
        if (accessible) {
            rwCheckbox.removeAttribute('disabled');
        }
        */
        if (file.isReadable) {
            rwCheckbox.setAttribute('checked', file.isReadOnly);
        } else  {
            var rwbox = document.getElementById('rwbox');
            rwbox.setAttribute('collapsed', 'true');
        }
    }
    document.getElementById("nameField").value = name;
    if (item.renameable) {
        // True for virtual folders, projects, others?)
        gNameField.removeAttribute('readonly');
        gNameField.focus();
        gNameField.select();
        updateApply();
        if (gApply.hasAttribute('collapsed')) {
            gApply.removeAttribute('collapsed');
            gApply.setAttribute('disabled', 'true');
        }
    }
    // directory fields
    if (item.type == 'livefolder') {
        document.getElementById('directory_tabpanel').removeAttribute('collapsed');
        document.getElementById('directory-tab').removeAttribute('collapsed');
        var includeFilter = document.getElementById('inc-filter');
        var excludeFilter = document.getElementById('ex-filter');
        includeFilter.value = item.prefset.getStringPref('import_include_matches');
        excludeFilter.value = item.prefset.getStringPref('import_exclude_matches');
    } else {
        var panel = document.getElementById('directory_tabpanel');
        var tab = document.getElementById('directory-tab');
        panel.parentNode.removeChild(panel);
        tab.parentNode.removeChild(tab);
    }
}

function OK()  {
    Apply();
    window.arguments[0].res = true;
    window.close();
};


function updateApply() {
    var enableApply = gItem.name != gNameField.value;
    
    if (!enableApply && gItem.type == 'livefolder') {
        var includeFilter = document.getElementById('inc-filter');
        var excludeFilter = document.getElementById('ex-filter');
        enableApply = includeFilter.value != gItem.prefset.getStringPref('import_include_matches') ||
                      excludeFilter.value != gItem.prefset.getStringPref('import_exclude_matches');
    }
    if (enableApply) {
        if (gApply.hasAttribute('disabled')) {
            gApply.removeAttribute('disabled');
        }
    } else {
        gApply.setAttribute('disabled', 'true');
    }
}

function Apply()  {
    gItem.name = gNameField.value;
    if (gItem.type == 'livefolder') {
        var includeFilter = document.getElementById('inc-filter');
        var excludeFilter = document.getElementById('ex-filter');
        gItem.prefset.setStringPref('import_include_matches', includeFilter.value);
        gItem.prefset.setStringPref('import_exclude_matches', excludeFilter.value);
    }
    opener.ko.projects.active.view.refresh(gItem);
    updateApply();
}

function Cancel()  {
    window.arguments[0].res= false;
    window.close();
}
