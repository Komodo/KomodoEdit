var hPrefWindow = null;
var prefPanelTree = null;
var view = null;
var part = null;
var prefInvokeType = "global";
var prefs = Components.classes["@activestate.com/koPrefService;1"].
    getService(Components.interfaces.koIPrefService).prefs;
var lastFilter = "";

var koFilterBox;

/* General startup routine for preferences dialog.
 * Place all necessary modifications to pref tree here.
 *    "windows.arguments[0]" can be null or a string identifying the
 *        pref panel to open. If null, then the last used pref panel
 *        is opened. The correct string is the id attribute of the
 *        <treeitem> tags in preftree.xul. For example: "debuggerItem",
 *        "editorItem", "perlItem".
 */
function Onload()
{
    hPrefWindow = new koPrefWindow('panelFrame', null, true);
    prefPanelTree = document.getElementById( "prefsTree" );

    if (!hPrefWindow) {
        throw new Error("failed to create prefwindow");
    }
    var filteredTreeView = setupFilteredTree();
    hPrefWindow.setTreeView(filteredTreeView);
    document.getElementById("pref-deck").selectedIndex = 1;
    hPrefWindow.prefDeckSwitched(1);

    // The following selects the default selection (see preftree.xul
    // for the ids of the treeitems to choose from)
    // if an argument is passed in, otherwise loads it from a preference.
    var selectedItem;
    if (window.arguments && window.arguments[0] != null) {
        selectedItem = window.arguments[0];
    } else {
        selectedItem = Components.classes["@activestate.com/koPrefService;1"]
              .getService(Components.interfaces.koIPrefService).prefs
              .getStringPref('defaultSelectedPref');
    }
    if (!selectedItem || !document.getElementById(selectedItem)) {
        var firstChild = document.getElementById( "panelChildren" ).firstChild;
        selectedItem = firstChild.getAttribute('id');
    }
    switchToPanel(selectedItem);
    koFilteredTreeView.loadPrefsFullText();

    var showAdvanced = prefs.getBoolean("prefs_show_advanced", false);
    document.getElementById('toggleAdvanced').checked = showAdvanced;
    koFilteredTreeView.updateFilter();
    setAdvancedPanelState();
}

function switchToPanel(selectedItem) {
    hPrefWindow.helper.selectRowById(selectedItem);
    prefPanelTree.focus();
}

function doOk() {
    if (!hPrefWindow.onOK())
        return false;
    return true;
}

function doApply() {
    if ( ! hPrefWindow.onApply())
        return false;

    // The pref change itself might trigger more pref changes from
    // observers, give them a bit of time to modify prefs further
    // before we reinitialize
    // todo: use actual events for this
    // todo: block pref ui while this is in progress
    setTimeout(function()
    {
        hPrefWindow.orig_prefset = null;
        hPrefWindow.init();
    }, 500);

    return true;
}

function doCancel() {
    if (!hPrefWindow.onCancel())
        return false;
    return true;
}

function getHelpTag() {
    return hPrefWindow.helper.getSelectedCellValue("helptag");
}

function canHelp() {
    // enable or disable the help button based on whether a tag exists
    var helpTag = getHelpTag();
    // help_tag2page located in launch.js
    if (helpTag) {
        document.getElementById('prefs_help_button').removeAttribute('disabled');
    } else {
        document.getElementById('prefs_help_button').setAttribute('disabled','true');
    }
}

function doHelp() {
    ko.windowManager.getMainWindow().ko.help.open(getHelpTag());
}

function setupFilteredTree() {
    var filteredTreeView = koFilteredTreeView.getPrefTreeView.apply(koFilteredTreeView);
    if (!filteredTreeView) {
        throw new Error("Couldn't create a filteredTreeView");
    }
    var filteredTree = document.getElementById("filteredPrefsTree");
    filteredTree.treeBoxObject
                .QueryInterface(Components.interfaces.nsITreeBoxObject)
                .view = filteredTreeView;
    koFilterBox = document.getElementById("pref-filter-textbox");
    return filteredTreeView;
}

function onFilterKeypress(event) {
    try {
        if (event.keyCode == event.DOM_VK_ESCAPE) {
            if (koFilterBox.value !== '') {
                koFilterBox.value = '';
                koFilteredTreeView.updateFilter("");
                lastFilter = "";
                event.cancelBubble = true;
                event.stopPropagation();
                event.preventDefault();
            }
            return;
        }
    } catch (e) {
        log.exception(e);
    }
}

function updateFilter(event) {
    lastFilter = koFilterBox.value;
    koFilteredTreeView.updateFilter(koFilterBox.value);
}

function toggleAdvanced(event) {
    var prefset = hPrefWindow._getCurrentPrefSet();
    var checkbox = document.getElementById('toggleAdvanced');
    var checked = checkbox.checked;
    prefs.setBoolean("prefs_show_advanced", checked);
    prefset.setBoolean("prefs_show_advanced", checked);
    koFilteredTreeView.updateFilter(lastFilter);
    setAdvancedPanelState();
}

function forceAdvanced() {
    var prefset = hPrefWindow._getCurrentPrefSet();
    var checkbox = document.getElementById('toggleAdvanced');
    console.log(checkbox.checked);
    if (checkbox.checked) return;
    
    checkbox.setAttribute("checked", true);
    toggleAdvanced();
    
    var showAdvancedWarned = prefs.getBoolean("prefs_show_advanced_warned", false);
    if (! showAdvancedWarned) {
        setTimeout(function() {
            var msg = 'Advanced preferences have been enabled, you can disable them ' +
                      'by toggling "Show Advanced" at the bottom left of the preference window.';
            require("ko/dialogs").alert(msg);
            
            prefs.setBoolean("prefs_show_advanced_warned", true);
            prefset.setBoolean("prefs_show_advanced_warned", true);
        }, 100);
    }
}

function setAdvancedPanelState() {
    var showAdvanced = prefs.getBoolean("prefs_show_advanced", false);
    var frames = document.getElementById("panelFrame").childNodes;
    for (var x=0;x<frames.length;x++)
    {
        var frame = frames[x].contentWindow.document.documentElement;
        frame.classList.add("pref-window");

        if (showAdvanced)
        {
            frame.classList.add("show-advanced");
        }
        else
        {
            frame.classList.remove("show-advanced");
        }
    }
}
