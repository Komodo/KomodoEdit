var log = ko.logging.getLogger("prefs::preview-properties");
var gDefaultBrowserName = null;

function LoadAvailableBrowsers(browserType)
{
    var menulist = document.getElementById("browser-select-menulist");
    var menupopup = document.getElementById("browser-select-menupopup");
    gDefaultBrowserName = menulist.label;
    // Load the menuitems, though we must remove the oncommand attribute.
    ko.uilayout.populatePreviewToolbarButton(menupopup);
    var menuitem = menupopup.firstChild;
    var selectedItem = null;
    while (menuitem) {
        if (browserType && menuitem.getAttribute("value") == browserType) {
            selectedItem = menuitem;
        }
        menuitem.removeAttribute("oncommand");
        menuitem = menuitem.nextSibling;
    }
    if (selectedItem) {
        menulist.selectedItem = selectedItem;
    }
}

function ClearPreviewSettings() {
    try {
        document.getElementById('preview').value = null;
        var menulist = document.getElementById('browser-select-menulist');
        menulist.setAttribute('label', gDefaultBrowserName);
        menulist.setAttribute('value', null);
    } catch (e) {
        log.exception(e);
    }
}

function OnPreferencePageLoading(prefset) {
    try {
        var browserType = prefset.getString("preview_browser", "");
        LoadAvailableBrowsers(browserType);
    } catch (e) {
        log.exception(e);
    }
}

function OnPreferencePageOK(prefset) {
    try {
        var menulist = document.getElementById('browser-select-menulist');
        if (!menulist.value) {
            prefset.setStringPref("preview_browser", "");
        } else {
            prefset.setStringPref("preview_browser", menulist.value);
        }
        return true;
    } catch (e) {
        log.exception(e);
    }
    return false;
}

