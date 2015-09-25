/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 *
 * The Original Code is Komodo code.
 *
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 *
 * Contributor(s):
 *   ActiveState Software Inc
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

/* ---- UI Helpers for showing/hiding, expanding collapsing, various UI features ---- */
if (typeof(ko)=='undefined') {
    var ko = {};
}
ko.uilayout = {};

(function() {
var _gPrefs = Components.classes["@activestate.com/koPrefService;1"].
                getService(Components.interfaces.koIPrefService).prefs;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/library.properties");
var XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
var {Services} = Components.utils.import("resource://gre/modules/Services.jsm", {});

var _log = ko.logging.getLogger('uilayout');
//_log.setLevel(ko.logging.LOG_DEBUG);

/**
 * Toggle whether the toolbox should auto-hide in full screen mode
 */
this.toggleFullScreenToolboxAutoHide = function uilayout_toggleFullScreenToolboxAutoHide()
{
  const kPrefName = "browser.fullscreen.autohide";
  try {
    Services.prefs.setBoolPref(kPrefName, !Services.prefs.getBoolPref(kPrefName));
  } catch (ex) {
    // this might happen if the pref doesn't exist (though it should!) or it was
    // set to the wrong type.  Force clear it and set it to something sensible.
    Services.prefs.clearUserPref(kPrefName);
    Services.prefs.setBoolPref(kPrefName, true);
  }
  setTimeout(function() {
    // We need to update the menu state on a timeout because <menuitem
    // type="checkbox"> itself fiddles with it after our even handler exits
    var menuitem = document.getElementById("menu_toolbars_fullscreen_autohide");
    if (menuitem) {
      if (Services.prefs.getBoolPref(kPrefName)) {
        menuitem.setAttribute("checked", true);
      } else {
        menuitem.removeAttribute("checked");
      }
    }
  }, 0);
};

// Toggle the visibility of the specified toolbar,
// along with the corresponding broadcaster if it exists.
this.toggleToolbarVisibility = function uilayout_toggleToolbarVisibility(toolbarId)
{
    /**
     * @type {Node}
     */
    var toolbar = document.getElementById(toolbarId);
    if (!toolbar) {
        _log.error("Couldn't find toolbar: " + toolbarId);
        return;
    }
    var broadcasterId = toolbar.getAttribute('broadcaster');
    if (!broadcasterId) {
        _log.info("No broadcaster associated with toolbar: " + toolbarId);
        return;
    }
    var broadcaster = document.getElementById(broadcasterId);
    if (!broadcaster) {
        _log.error("Couldn't find broadcaster: " + broadcasterId);
        return;
    }
    if (toolbar.getAttribute("kohidden") == "true") {
        toolbar.setAttribute("kohidden", "false");
        broadcaster.setAttribute("checked", "true");
    } else {
        toolbar.setAttribute("kohidden", "true");
        broadcaster.setAttribute("checked", "false");
    }
    document.persist(toolbarId, "kohidden");

    this._updateToolbarViewStates();
}

// 'toolbarId' is the id of the toolbar that should be affected
// 'show' is a boolean -- true means show the text.
function _setToolbarButtonText(toolbarId, buttonTextShowing)
{
    var toolbar = document.getElementById(toolbarId);
    if (!toolbar) {
        _log.error("Could not find toolbar with id: " + toolbarId);
        return;
    }
    try {
        toolbar.setAttribute('mode', buttonTextShowing ? 'full' : 'icons');
    } catch(e) {
        _log.error(e);
    }
}

// Toggle all toolbars
this.toggleToolbars = function uilayout_toggleToolbars()
{
    var toolbarsShowing;
    var broadcaster = document.getElementById('cmd_toggleToolbars');
    if (broadcaster.hasAttribute('checked') && broadcaster.getAttribute('checked') == 'true') {
        toolbarsShowing = false;
    } else {
        toolbarsShowing = true;
    }

    this.setToolbarsVisibility(toolbarsShowing);
}

this.setToolbarsVisibility = function uilayout_setToolbarsVisibility(toolbarsShowing)
{
    var broadcaster = document.getElementById('cmd_toggleToolbars');
    broadcaster.setAttribute("checked", toolbarsShowing);

    var toolboxrow = document.getElementById('main-toolboxrow-wrapper');
    if (toolbarsShowing)
    {
        toolboxrow.removeAttribute('collapsed');
    }
    else
    {
        toolboxrow.setAttribute('collapsed', 'true');
    }

    document.persist('cmd_toggleToolbars', 'checked');

// #if PLATFORM != "darwin"
        ko.uilayout.ensureMenuButtonVisible();
        ko.uilayout.updateToolboxVisibility();
// #endif
}

var _buttonTextShowing = false;
this.isButtonTextShowing = function() {
    return _buttonTextShowing;
}

// Toggle whether text is shown on toolbar buttons
this.toggleButtons = function uilayout_toggleButtons()
{
    var buttonTextShowing;
    var broadcaster = document.getElementById('cmd_toggleButtonText');
    if (broadcaster.hasAttribute('checked') && broadcaster.getAttribute('checked') == 'true') {
        broadcaster.setAttribute("checked", "false");
        buttonTextShowing = false;
    } else {
        broadcaster.setAttribute("checked", "true");
        buttonTextShowing = true;
    }
    _buttonTextShowing = buttonTextShowing;
    _setToolbarButtonText('toolbox_main', buttonTextShowing);
    _setToolbarButtonText('standardToolbar', buttonTextShowing);
    _setToolbarButtonText('debuggerToolbar', buttonTextShowing);
    _setToolbarButtonText('workspaceToolbar', buttonTextShowing);
    ko.uilayout.updateToolbarArrangement(buttonTextShowing);
    document.persist('cmd_toggleButtonText', 'checked');
}

// #if PLATFORM != "darwin"
this.toggleMenubar = function uilayout_toggleMenubar() {
    var broadcaster = document.getElementById('cmd_toggleMenubar');
    broadcaster.setAttribute('checked', !(broadcaster.getAttribute('checked') == 'true'));
    ko.uilayout.setMenubarVisibility();
}

// Copy the top-level menus into the button menus.
this.cloneUnifiedMenuItems = function uilayout_cloneUnifiedMenuItems(event) {
    if (event.originalTarget != document.getElementById('unifiedMenuPopup')) return;
    
    // Reset the menupopup each time its initialized
    var wrapper = document.getElementById('unifiedMenuPopupHbox');
    if ( ! ("__cloned" in this.cloneUnifiedMenuItems))
    {
        this.cloneUnifiedMenuItems.__cloned = wrapper.cloneNode(true);
    }
    var _wrapper = this.cloneUnifiedMenuItems.__cloned.cloneNode(true);
    wrapper.parentNode.replaceChild(_wrapper, wrapper);
    wrapper = _wrapper;

	var menubar       = document.getElementById('menubar_main');
	var popupFile     = document.getElementById('popup_file');
	var panePrimary   = document.getElementById('unifiedMenuPrimaryPane');
	var paneSecondary = document.getElementById('unifiedMenuSecondaryPane');
	var menuSeparator = document.getElementById('unifiedMenuMruSeparator');

	panePrimary.innerHTML = "";
	for (var x=0; x < paneSecondary.childNodes.length; x++)
	{
		let node = paneSecondary.childNodes[x];
		if (node.getAttribute("preserve") == "true")
			continue;
		paneSecondary.removeChild(node);
	}

	var length = popupFile.childNodes.length;
	for (let x=0;x<length;x++) {
		panePrimary.appendChild(popupFile.childNodes[x].cloneNode(true));
	}

	var length = menubar.childNodes.length;
	for (let x=1;x<length;x++) {
		paneSecondary.insertBefore(menubar.childNodes[x].cloneNode(true), menuSeparator);
	}

	UpdateUnifiedMenuMru();

	// TODO: Re-initialize all cloned id's ??
}

/**
 * Update the top-level menu visibility.
 *
 * Note that even when the menubar is hidden, it can still be made visible using
 * the Alt key.
 *
 * @param menubarShowing {Boolean}  Whether the menu is always showing.
 */
this.setMenubarVisibility = function uilayout_setMenubarVisibility(menubarShowing) {
    //dump('setMenubarVisibility:: menubarShowing: ' + menubarShowing + '\n');
    var menuButton  = document.getElementById('unifiedMenuButton');
    var menuToolbar = document.getElementById('toolbar-menubar');

    if (menubarShowing === undefined) {
        // Check the broadcaster to find out if it should be showing.
        var broadcaster = document.getElementById('cmd_toggleMenubar');
        menubarShowing = (broadcaster.getAttribute('checked') == 'true');
        //dump('setMenubarVisibility:: menubarShowing found as: ' + menubarShowing + '\n');
    }

    menuToolbar.setAttribute("autohide", !(menubarShowing));
    if (menubarShowing) {
        // Hide the menu button - as the menu is always showing.
        menuButton.collapsed = true;
    } else {
        menuButton.collapsed = false;
        UpdateUnifiedMenuMru();
    }

	ko.uilayout.ensureMenuButtonVisible();
    ko.uilayout.updateToolboxVisibility();
};

this.ensureMenuButtonVisible = function uilayout_ensureMenuButtonVisible()
{
	var broadcaster = document.getElementById('cmd_toggleMenubar');
	var menubarShowing = (broadcaster.getAttribute('checked') == 'true');

    broadcaster = document.getElementById('cmd_toggleToolbars');
	var toolbarShowing = (broadcaster.getAttribute('checked') == 'true');

	var menuButton = document.getElementById('unifiedMenuButton');

	if ( ! toolbarShowing && ! menubarShowing)
	{
		var statusbar = document.getElementById("statusbarviewbox");
		var panel = document.createElement("statusbarpanel");
		panel.setAttribute("id", "menubuttonpanel");
		panel.appendChild(menuButton);
		statusbar.insertBefore(panel, statusbar.firstChild);
	}
	else if ( ! menubarShowing && menuButton.parentNode.nodeName == "statusbarpanel")
	{
		var toolboxWrap = document.getElementById("main-toolboxrow-wrapper");
		toolboxWrap.appendChild(menuButton);

		var statusbar = document.getElementById("statusbarviewbox");
		var panel = document.getElementById("menubuttonpanel");
		statusbar.removeChild(panel);
	}
}

this.updateToolboxVisibility = function uilayout_updateToolboxVisibility()
{
    var broadcaster = document.getElementById('cmd_toggleMenubar');
    var menubarShowing = (broadcaster && broadcaster.getAttribute('checked') == 'true');
    
    var broadcaster = document.getElementById('cmd_toggleToolbars');
    var toolbarsShowing = (broadcaster && broadcaster.getAttribute('checked') == 'true');
    
    var toolbox = document.getElementById('toolbox_main');
    var windowNode = document.getElementById('komodo_main');
    if ( ! menubarShowing && ! toolbarsShowing) {
        toolbox.collapsed = true;
        windowNode.classList.add("toolbox-hidden");
    } else {
        toolbox.collapsed = false;
        windowNode.classList.remove("toolbox-hidden");
    }
}

// #endif

this.updateToolbarArrangement = function uilayout_updateToolbarArrangement(buttonTextShowing /* default: look it up */)
{
    var menuItem = document.getElementById('menu_toggleButtonText');
    var fromloading = false;
    var contextMenuItem = document.getElementById('menu_toggleButtonText');
    if (typeof(buttonTextShowing) == 'undefined') {
        var broadcaster = document.getElementById('cmd_toggleButtonText');
        buttonTextShowing = broadcaster.hasAttribute('checked') &&
                            broadcaster.getAttribute('checked') == 'true';
        fromloading = true;
    }
    _buttonTextShowing = buttonTextShowing;
    var toolbars = document.getElementById('main-toolboxrow').querySelectorAll('toolbar');
    var i;
    for (i = 0; i < toolbars.length; i++ ) {
        // Note: this can include custom toolbars
        _setToolbarButtonText(toolbars[i].id, buttonTextShowing);
    }
}

/**
 * Start toolbar customization
 *
 * @param   {<toolbox>} aToolbox [optional] The toolbox to customize
 */
this.customizeToolbars = function uilayout_customizeToolbars(aToolbox) {
    var toolbox = aToolbox;
    if (!(toolbox instanceof Element)) {
        toolbox = document.getElementById(aToolbox);
    }
    if (!toolbox) {
        _log.error("ko.uilayout.customizeToolbars: can't find toolbox " + aToolbox);
    }

    /**
     * Update the UI to sync with the customization changes
     */
    var syncUIWithReality = (function syncUIWithReality() {
        var toolbars = Array.slice(toolbox.childNodes).concat(toolbox.externalToolbars);

        // Update hidden / visible state of toolbar items
        // and set relevant ancestry classes
        this._updateToolbarViewStates(toolbox);

        // Hide separators if all elements before or after it in the toolbar
        // are hidden
        this._updateToolbarSeparators(toolbox);

        // Update the menu states
        for each (var toolbar in toolbars) {
            var broadcasterId = toolbar.getAttribute("broadcaster");
            if (broadcasterId) {
                var broadcaster = document.getElementById(broadcasterId);
                if (broadcaster) {
                    if (toolbar.getAttribute("kohidden") == "true") {
                        broadcaster.removeAttribute("checked");
                    } else {
                        broadcaster.setAttribute("checked", "true");
                    }
                }
            }
        }

        // make the overflow button rebuild the next time it's open
        var toolboxRow = document.getElementById("main-toolboxrow");
        if (toolboxRow) {
            toolboxRow.dirty = true;
        }
    }).bind(this);

    // set up drag-and-drop states
    var toolboxrow = toolbox.querySelector("toolboxrow");
    if (toolboxrow) {
        Array.slice(toolboxrow.childNodes).forEach(function(elem) {
            if ((elem instanceof Element) && elem.localName == "toolbar") {
                elem.setAttribute("can-drag", "true");
            }
        });
    }

    const DIALOG_URL = "chrome://komodo/content/dialogs/customizeToolbar.xul";
    var sheet = document.getElementById("customizeToolbarSheetPopup");
    var useSheet = false, dialog = null;
    try {
        Components.utils.import("resource://gre/modules/Services.jsm");
        useSheet = Services.prefs.getBoolPref("toolbar.customization.usesheet");
    } catch (e) {
        // failed to get pref, use default of true
    }
    if (sheet && useSheet) {
        var sheetFrame = sheet.firstElementChild;
        sheetFrame.hidden = false;
        sheetFrame.toolbox = toolbox;
        sheetFrame.onCustomizeFinished = function(toolbox) {
            syncUIWithReality(toolbox);
            sheet.hidePopup();
        };

        // Load the dialog if it hasn't been loaded. If it _has_ been loaded,
        // force a reload anyway, to make sure it finds the right toolbox
        if (sheetFrame.getAttribute("src") == DIALOG_URL) {
            sheetFrame.contentWindow.location.reload();
        } else {
            sheetFrame.setAttribute("src", DIALOG_URL);
        }

        // only show things when we're all ready
        sheet.style.visibility = "hidden";
        sheetFrame.addEventListener("ready", function _() {
            sheetFrame.removeEventListener("ready", _, false);
            sheet.style.visibility = "";
        }, false);
        sheet.openPopup(toolbox, "after_start", 0, 0, false, false, null);
        dialog = sheetFrame.contentWindow;
    } else {
        dialog = window.openDialog(DIALOG_URL,
                                   "",
                                   "chrome,dependent,centerscreen",
                                   toolbox,
                                   syncUIWithReality);
    }

    if (dialog && !dialog.closed) {
        dialog.addEventListener("customize", syncUIWithReality, false);
    }
    return dialog;
};

/**
 * Enter panes/widgets customization mode
 * Eventually, toolbar customization should be moved here as well.
 */
this.customize = (function uilayout_customize() {
    document.documentElement.setAttribute("customizing", "true");
    let placeholder = document.getElementById("customizingPlaceHolder");
    document.getElementById("editorviewbox").selectedPanel = placeholder;
    for (let paneId of ko.widgets.panes) {
        ko.widgets.getPaneAt(paneId).customizing = true;
    }
    let toolbox = document.getElementById("toolbox_main");
    let hoverBox = document.getAnonymousElementByAttribute(toolbox, "anonid", "hover-box");
    hoverBox.removeAttribute("bottom");
    this.updateViewRef();
    
    this.customize._state = {
        'workspace_left_area': this.isPaneShown('workspace_left_area'),
        'workspace_right_area': this.isPaneShown('workspace_right_area'),
        'workspace_bottom_area': this.isPaneShown('workspace_bottom_area')
    }
    
    this.ensurePaneShown('workspace_left_area');
    this.ensurePaneShown('workspace_right_area');
    this.ensurePaneShown('workspace_bottom_area');
}).bind(this);

this._customizeComplete = (function uilayout__customizeComplete() {
    // Get us out of customize mode
    document.documentElement.removeAttribute("customizing");
    this.updateViewDeck();
    this.updateViewRef();
    for (let paneId of ko.widgets.panes) {
        ko.widgets.getPaneAt(paneId).customizing = false;
    }
    let toolbox = document.getElementById("toolbox_main");
    let hoverBox = document.getAnonymousElementByAttribute(toolbox, "anonid", "hover-box");
    hoverBox.setAttribute("bottom", "0");
    
    if ('_state' in this.customize) {
        for (let k in this.customize._state) {
            if (this.customize._state[k]) continue;
            this.ensurePaneHidden(k);
        }
        delete this.customize._state;
    }
}).bind(this);

/**
 * Update the toolbar classes to add first-child and last-child
 * to the first/last toolbar items that are not hidden
 * This is used to get the rounded corner effect
 * @param toolbox {<toolbox>} The toolbox to update
 */
this._updateToolbarViewStates = (function uilayout__updateToolbarViewStates(toolbox)
{
    if (!toolbox || !(toolbox instanceof Element)) {
        // not a toolbox. Note that this can be used as an event listener, in
        // which case the argument is an Event rather than a <toolbox>...
        toolbox = document.getElementById("toolbox_main");
    }

    var buttonSets = toolbox.querySelectorAll("toolbar > toolbaritem > toolbarbutton:first-child");
    for (var i=0;i<buttonSets.length;i++)
    {
        var toolbarItem     = buttonSets[i].parentNode;
        var toolbar         = toolbarItem.parentNode;

        var children = Array.slice(toolbarItem.querySelectorAll(".first-child, .last-child"));
        for each (var child in children) {
            if (child.parentNode == toolbarItem) {
                child.classList.remove("first-child");
                child.classList.remove("last-child");
            }
        }

        children = Array.slice(toolbarItem.querySelectorAll(":not([kohidden='true']):not(toolbarseparator):not(spacer)"));
        children = children.filter(function(child) child.parentNode === toolbarItem && child.parentNode.parentNode.getAttribute("kohidden") !== "true");

        if (children.length > 0) {
            toolbarItem.removeAttribute("kohidden");
            toolbarItem.classList.remove('no-children');
            toolbarItem.classList.add('has-children');
            children[0].classList.add("first-child");
            children[children.length - 1].classList.add("last-child");

            if (i==0) {
                toolbar.classList.add('first-child');
            } else if (typeof previousLastChild != 'undefined') {
                previousLastChild.classList.remove('last-child');
            }
            toolbar.classList.add('last-child');

	    var previousLastChild = toolbar;
        } else {
            toolbarItem.setAttribute("kohidden", "true");
            toolbarItem.classList.add('no-children');
            toolbarItem.classList.remove('has-children');
        }
    }

    // Update toolbar child visibility as otherwise it does not get updated
    // when the visible children have changed but no overflow events
    // were fired
    document.getElementById('main-toolboxrow')._updateChildVisibility();

}).bind(this);

/**
 * Show/hide toolbar separators in response to their surrounding elements being
 * hidden
 */
this._updateToolbarSeparators = (function uilayout__updateToolbarSeparators(toolbox)
{
    // this exists separately because separators often don't have ids; rather
    // than force them to have one, we just call this on startup and when
    // toolbars get customized.
    if (!toolbox || !(toolbox instanceof Element)) {
        // not a toolbox. Note that this can be used as an event listener, in
        // which case the argument is an Event rather than a <toolbox>...
        toolbox = document.getElementById("toolbox_main");
    }
    function checkForSeparators(aFirstElem, aProperty) {
        var hidden = true;
        for (var elem = aFirstElem; elem; elem = elem[aProperty]) {
            if (/separator/.test(elem.localName)) {
                if (hidden) {
                    // everything before this separator was hidden; hide
                    // it too.
                    elem.setAttribute("kohidden", "true");
                } else {
                    // something before this was not hidden; show it.
                    elem.removeAttribute("kohidden");
                }
                // start a new run of (possibly) hidden elements
                hidden = true;
            } else {
                var bounds = elem.getBoundingClientRect();
                if (bounds.width * bounds.height > 0) {
                    // This element is not hidden; look for the next
                    // separator (and skip it).
                    hidden = false;
                    continue;
                }
                // Getting here means this element is hidden, and so are all
                // the ones before it.  Nothing to do here, actually.
            }
        }
    }
    for each (var toolbar in Array.slice(toolbox.childNodes).concat(toolbox.externalToolbars)) {
        checkForSeparators(toolbar.firstChild, "nextSibling");
        checkForSeparators(toolbar.lastChild, "previousSibling");
    }
}).bind(this);

this.populatePreviewToolbarButton = function uilayout_populatePreviewToolbarButton(popup)
{
    // Only do this once.
    // XXX We'll need to remove it's children when prefs are changed.
    if (popup.childNodes.length > 0)
        return;

// #if PLATFORM == "win"
    mi = document.createElementNS(XUL_NS, "menuitem");
    mi.setAttribute("label", _bundle.GetStringFromName("configuredBrowser"));
    mi.setAttribute("tooltiptext", _bundle.GetStringFromName("seePreferencesWebBrowser"));
    mi.setAttribute("oncommand",
                    "ko.views.manager.currentView.viewPreview(); event.stopPropagation();");
    mi.setAttribute("value", "configured");
    popup.appendChild(mi);
// #endif

    mi = document.createElementNS(XUL_NS, "menuitem");
    mi.setAttribute("label", _bundle.GetStringFromName("internalBrowser.menu.label"));
    mi.setAttribute("tooltiptext", _bundle.GetStringFromName("internalBrowser.menu.tooltiptext"));
    mi.setAttribute("oncommand",
                    "ko.views.manager.currentView.viewPreview('komodo'); event.stopPropagation();");
    mi.setAttribute("class", "menuitem-iconic komodo-16x16");
    mi.setAttribute("value", "komodo");
    popup.appendChild(mi);

    var koWebbrowser = Components.classes["@activestate.com/koWebbrowser;1"].
                       getService(Components.interfaces.koIWebbrowser);
    var browsersObj = {};
    var browserTypesObj = {};
    koWebbrowser.get_possible_browsers_and_types(
            {} /* count */, browsersObj, browserTypesObj);
    var browsers = browsersObj.value;
    var browserTypes = browserTypesObj.value;
    var mi;
    var browserURI;
    for (var i = 0; i < browsers.length; i++) {
        mi = document.createElementNS(XUL_NS, "menuitem");
        mi.setAttribute("label", browsers[i]);
        mi.setAttribute("crop", "center");
        mi.setAttribute("tooltiptext", ko.uriparse.baseName(browsers[i]));
        if (browserTypes[i]) {
            mi.setAttribute("value", browserTypes[i]);
            mi.setAttribute("class", "menuitem-iconic browser-"+browserTypes[i]+"-icon");
        }
        browserURI = ko.uriparse.localPathToURI(browsers[i]);
        mi.setAttribute("oncommand",
                        "ko.views.manager.currentView.viewPreview('"+browserTypes[i]+"'); event.stopPropagation();");
        popup.appendChild(mi);
    }
}

this.focusPane = function uilayout_focusPane(paneId)
{
    var pane = document.getElementById(paneId);
    var widgetId = pane.selectedPanel.getAttribute('id');
    ko.uilayout.toggleTab(widgetId, false);
}

this.toggleWidget = /* alias for toggleTab */
this.toggleTab = function uilayout_toggleTab(widgetId, collapseIfFocused /* =true */)
{
    try {
        // if called with collapseIfFocused=false, we will only ensure that
        // the specified tab is focused and will not collapse any panels
        if (typeof(collapseIfFocused) == 'undefined')
            collapseIfFocused = true;
        var widget = ko.widgets.getWidget(widgetId, false);
        if (!widget || !widget.containerPane) {
            throw("Can't find widget " + widgetId);
        }
        if (this.isTabShown(widgetId) && collapseIfFocused) {
            // The widget is currently selected and visible; we want to toggle
            // it so it's not.
            // Before we collapse it, figure out whether the focus is in
            // this widget.  If so, then move it back to the editor
            if (xtk.domutils.elementInFocus(widget.containerPane)) {
                if (ko.views.manager.currentView) {
                    ko.views.manager.currentView.setFocus();
                }
            }
            widget.containerPane.collapsed = true;
            return;
        }
        // If we get here, we want to force show and focus the widget.
        this.ensureTabShown(widgetId, true);
    } catch (e) {
        _log.exception(e);
    }
}


/*
 **
 * updateTabpickerMenu
 * @param {XUL menupopup} menupopup
 *
 * This menu-builder takes a list of menu items that control which tab
 * to show in a given pane.  Each menuitem is expected to have an observes
 * attribute with a value of "show_" followed by the ID of the tab the
 * menuitem controls.
 */
this.updateTabpickerMenu = function uilayout_updateTabpickerMenu(menupopup)
{
    _log.deprecated("ko.uilayout.updateTabpickerMenu is no longer used; " +
                    "popups are now handled by ko.widgets.updateMenu() and " +
                    "ko.widgets.onMenuCommand()");
    ko.widgets.updateMenu(menupopup);
}

this.togglePane = function uilayout_togglePane(paneId, force)
{
    // If force is true, then the toggle happens regardless.
    // If force is false, then the toggle happens only if the
    // current tab is not collapsed and focused.
    try {
        if (typeof(force) == 'undefined') {
            force = false;
        }
        // If the project/toolbox pane is not shown, then show it
        // and focus on the relevant part manager
        var pane = document.getElementById(paneId);
        if (pane.getAttribute("splitterCmdId")) {
            // we got the splitter instead; find the pane
            var broadcaster = document.getElementById(pane.getAttribute("splitterCmdId"));
            if (broadcaster.getAttribute("box")) {
                pane = document.getElementById(broadcaster.getAttribute("box"));
                _log.deprecated("Calling togglePane with the splitter ID as "+
                                "the first argument is deprecated; please use "+
                                "the ID of the pane instead.");
            }
        }
        if (!force && pane.collapsed) {
            var scimoz = null;
            // Following code fixes bug 83545:
            // After we've opened a tab, if the caret was visible before
            // we opened it, get Scintilla to make sure it's visible after.
            // Only do this if the cursor was visible before opening a pane.
            //
            // Scintilla doesn't expose the width of the screen in characters
            // (and this is hard to do in proportional fonts), so if the cursor
            // is scrolled to the left or right of the viewport, we'll bring it into
            // view anyway.
            if (ko.views.manager.currentView
                && !!(scimoz = ko.views.manager.currentView.scimoz)) {
                var firstVisibleLine = scimoz.firstVisibleLine;
                var firstActualLine = scimoz.docLineFromVisible(firstVisibleLine);
                var lastActualLine = scimoz.docLineFromVisible(firstVisibleLine + scimoz.linesOnScreen);
                var currLine = scimoz.lineFromPosition(scimoz.currentPos);
                if (currLine < firstVisibleLine || currLine > lastActualLine) {
                    scimoz = null;
                }
            }
            pane.collapsed = false;
            if (scimoz) {
                // This has to be done in a setTimeout on Windows and OS X.
                // If we try it now, Scintilla thinks the caret is still in
                // view, and doesn't adjust the document's scroll.
                setTimeout(function(selectedTabItem) {
                    scimoz.scrollCaret();
                }, 100, pane.selectedTab);
            }
        } else {
            // Before we collapse it, figure out whether the focus is in this
            // panel.  If so, then move it back to the editor
            if (xtk.domutils.elementInFocus(pane)) {
                if (ko.views.manager.currentView) {
                    ko.views.manager.currentView.setFocus();
                } else {
                    // probably no file open to focus on, need to focus someplace else
                    window.focus();
                }
            }
            pane.collapsed = !pane.collapsed;
        }

        // technically the window resized, so fire the appropriate event
        xtk.domutils.fireEvent(window, "resize");
    } catch (e) {
        _log.exception(e);
    }
}

this.toggleSplitter = function uilayout_toggleSplitter(aCommandID) {
    var elt = document.getElementById(aCommandID);
    if (!elt) {
        _log.error("uilayout_toggleSplitter: couldn't find '" + aCommandID + "'");
        return;
    }
    var boxId = elt.getAttribute('box');
    var box = document.getElementById(boxId)
    if (!box) {
        _log.error("couldn't find " + boxId);
        return;
    }
    box.collapsed = !box.collapsed;
}

/**
 * Update the menubar menu item to reflect whether the window is in full screen
 * mode
 */
this.updateFullScreen = function uilayout_updateFullScreen() {
    var menuitem = document.getElementById('menuitem_fullScreen');
    if (window.fullScreen) {
        menuitem.setAttribute('checked', 'true');
    } else {
        menuitem.removeAttribute('checked');
    }
}

/**
 * Toggle the full screen state of the window
 */
this.fullScreen = function uilayout_FullScreen()
{
  window.fullScreen = !window.fullScreen;
  // We no longer need to do any extra handling; the UI changes are done via
  // CSS.  If we do end up needing logic, we should do so in a "fullscreen"
  // event handler attached to the window.
}

// #if PLATFORM != "darwin"
function _MruMenuItemId(menuitem) {
    return menuitem.getAttribute('id') || menuitem.getAttribute('refid') ||
            ["ref", menuitem.getAttribute("label"), menuitem.getAttribute("oncommand")].join("\u000E");
}

function MruMenusAddItem(menuitem) {
    if ( ! menuitem.hasAttribute('refid') && ! menuitem.hasAttribute('id'))
    {
        menuitem.setAttribute("id", _MruMenuItemId(menuitem));
    }
    ko.mru.add('mruMenuItemList', menuitem.getAttribute('id') || menuitem.getAttribute('refid'));

    // Currently this method can be called twice due to us listening for both
    // command and click events as command events don't properly bubble up the
    // chain. We should properly fix this in a larger release
    setTimeout(UpdateUnifiedMenuMru.bind(this), 0);
}

function UpdateUnifiedMenuMru() {
    var menupopup = document.getElementById('unifiedMenuSecondaryPane');
    var menuSeparator = document.getElementById('unifiedMenuMruSeparator');
	var mruWrapper = document.getElementById('unifiedMenuMru');
    menuSeparator.collapsed = true;

    // Remove old entries
	mruWrapper.innerHTML = ""

	if ( ! _gPrefs.hasPref('mruMenuItemList')) return;

    var mruList = _gPrefs.getPref('mruMenuItemList');
    if ( ! mruList || ! mruList.length) return;

    menuSeparator.collapsed = false;

    for (var i=0; i<mruList.length; i++) {
        let id = mruList.getStringPref(i);
        let menuitem;

        if (id.startsWith("ref\u000E")) {
            let [,label,oncommand] = id.split("\u000E");
            var elems = menupopup.getElementsByAttribute("label", label);
            for (let [,elem] in Iterator(elems)) {
                if (elem.hasAttribute("refid")) continue;
                if (elem.getAttribute('oncommand')== oncommand) {
                    menuitem = elem;
                    break;
                }
            }
        } else {
            menuitem = document.getElementById(id);
        }

        if ( ! menuitem) continue;

        let _item = menuitem.cloneNode(true);
        _item.setAttribute('ordinal', 9999);
        _item.setAttribute('refid', _MruMenuItemId(_item));
        _item.removeAttribute('id');

        mruWrapper.appendChild(_item);
    }
}
// #endif

function _addManageMRUMenuItem(prefName, parentNode, MRUName) {
    var menuitem = document.createElementNS(XUL_NS, 'menuseparator');
    parentNode.appendChild(menuitem);
    menuitem = document.createElementNS(XUL_NS, "menuitem");
    var MRUString = _bundle.GetStringFromName(MRUName);
    var manageLabel = _bundle.formatStringFromName("Manage the X List",
                                                   [MRUString], 1);
    menuitem.setAttribute("label", manageLabel);
    menuitem.setAttribute("accesskey", _bundle.GetStringFromName("mruManageAccessKey"));
    menuitem.setAttribute("oncommand", "ko.mru.manageMRUList('" + prefName + "');");
    parentNode.appendChild(menuitem);
}

function _updateMRUMenu(prefName, limit, addManageItem, MRUName, popupId)
{
    var separatorId;
    if (prefName == "mruProjectList") {
        popupId = popupId || "recentProjects_menupopup";
    } else if (prefName == "mruFileList") {
        popupId = popupId || "popup_mruFiles"; // MRU list is the whole popup.
    } else if (prefName == "mruTemplateList") {
        separatorId = "separator_mruTemplates"; // MRU list is everything after the separator.
        popupId = null;
    } else {
        throw new Error("Unexpected MRU menu to update: prefName='"+prefName+"'");
    }

    if (separatorId) {
        var separators = document.querySelectorAll("#" + separatorId);
        for (let i=0; i<separators.length; i++) {
            _doUpdateMRUMenu(prefName, limit, addManageItem, MRUName, null, separators[i])
        };
    } else {
        var menupopups = document.querySelectorAll("#" + popupId);
        for (let i=0; i<menupopups.length; i++) {
            _doUpdateMRUMenu(prefName, limit, addManageItem, MRUName, menupopups[i])
        };
    }

}

function _doUpdateMRUMenu(prefName, limit, addManageItem, MRUName, menupopup, separator)
{
    // Update a MRU menu popup under the file menu.
    //    "prefName" indicate which MRU menu to update.
    //
    // XXX This code was significantly complitcated just for the special
    //     template MRU menu under File->New. Perhaps that should be
    //     factored out.
    if (typeof(addManageItem) == "undefined") addManageItem = false;
    var prettyName;
    if (prefName == "mruProjectList") {
        prettyName = _bundle.GetStringFromName("Projects");
    } else if (prefName == "mruFileList") {
        prettyName = _bundle.GetStringFromName("Files");
    } else if (prefName == "mruTemplateList") {
        prettyName = _bundle.GetStringFromName("Templates");
    } 

    var mruList = null;
    var menuitem;
    if (_gPrefs.hasPref(prefName)) {
        mruList = _gPrefs.getPref(prefName);
    }

    // Wipe out existing menuitems.
    if (separator) {
        menupopup = separator.parentNode;
        while (separator.nextSibling) {
            menupopup.removeChild(separator.nextSibling);
        }
    } else  {
        while (menupopup.firstChild) {
            menupopup.removeChild(menupopup.firstChild);
        }
    }

    if (mruList && mruList.length) {
        // Add a menuitem like the following for each entry in the MRU:
        //    <menuitem class="menuitem_mru"
        //              oncommand="ko.open.URI('URL');"
        //              label="URL_DISPLAY_NAME"/>
        // For template MRU entries use this instead:
        //    <menuitem class="menuitem_mru"
        //              oncommand="ko.views.manager.newFileFromTemplateOrTrimMRU('URL');"
        //              label="URL_BASENAME"/>
        if (!menupopup) {
            menupopup = separator.parentNode;
        }
        var fileSvc = Components.classes["@activestate.com/koFileService;1"]
                        .createInstance(Components.interfaces.koIFileService);
        var length = mruList.length;
        var labelNum = 1;
        for (var i = 0; i < length; i++) {
            if (limit && i == limit && limit < length - 1) {
                var m1 = document.createElementNS(XUL_NS, "menu");
                var moreLabel = _bundle.GetStringFromName("more");
                m1.setAttribute("label", moreLabel);
                m1.setAttribute("accesskey", moreLabel.substr(0, 1));
                var m2 = document.createElementNS(XUL_NS, "menupopup");
                m2.setAttribute("onpopupshowing", "event.stopPropagation();");
                m1.appendChild(m2);
                menupopup.appendChild(m1);
                if (addManageItem) {
                    _addManageMRUMenuItem(prefName, menupopup, MRUName);
                    addManageItem = false;
                }
                menupopup = m2;
                labelNum = 1;
            }
            var url = mruList.getStringPref(i);
            menuitem = document.createElement("menuitem");
            // Mozilla does not handle duplicate accesskeys, so only putting
            // them on first 10.
            if (labelNum <= 9) {
                menuitem.setAttribute("accesskey", "" + labelNum);
            } else if (labelNum == 10) {
                menuitem.setAttribute("accesskey", "0");
            }
            let koFile = fileSvc.getFileFromURINoCache(url);
            if (!koFile.exists) {
                // Don't put non-existent items in a MRU menu
                mruList.deletePref(i);
                // And update the menu, and redo item i
                length -= 1;
                i -= 1; // gets incremented in the for-loop
                continue;
            }
            if (prefName == "mruTemplateList") {
                // Check the template names
                // Bug 81096: If the "url" is actually a path, and we're on
                // Windows, convert it to a URI to get rid of the backslashes.
                // Otherwise the backslashes get destroyed by the JS parser
                // when it processes the oncommand value.
                // In any case, get the canonical URL
                //
                // This should be done once during startup.
                // And who's writing out the templates as paths anyway?
                //
                // Also make sure the template file exists.  Don't put
                // bad entries in the menu.
// #if PLATFORM == "win"
                if (url != koFile.URI) {
                    url = koFile.URI;
                    mruList.deletePref(i);
                    mruList.insertStringPref(i, url);
                }
// #endif
                menuitem.setAttribute("label", labelNum + " " + koFile.baseName);
            } else {
                let pathPart = ko.views.labelFromPathInfo(koFile.baseName, koFile.dirName);
                if (prefName == "mruProjectList") {
                    // We don't need to show the ".komodoproject" extension.
                    let pos = pathPart.indexOf(".komodoproject");
                    if (pos >= 0) {
                        pathPart = pathPart.slice(0, pos) + pathPart.slice(pos + 14);
                    }
                }
                menuitem.setAttribute("label", labelNum + " " + pathPart);
                menuitem.setAttribute("tooltiptext", koFile.isLocal && koFile.path || koFile.URI);
            }

            menuitem.setAttribute('class', 'menuitem-file-status');
            ko.fileutils.setFileStatusAttributesFromFile(menuitem, koFile);

            labelNum++;
            menuitem.setAttribute("crop", "center");
            // XXX:HACK: For whatever reason, the "observes" attribute is
            // ignored when the menu item is inside a popup, so we call
            // ko.commands.doCommand directly. THIS IS NOT A GOOD THING!
            if (prefName == "mruTemplateList") {
                menuitem.addEventListener("command", function(_url, _prefName, _i, e) {
                    ko.uilayout.newFileFromTemplateOrTrimMRU(_url, _prefName, _i);
                    e.stopPropagation();
                }.bind(null, url, prefName, i));
            } else {
                menuitem.addEventListener("command", function(_url, e) {
                    ko.open.recentURI(_url);
                    e.stopPropagation();
                }.bind(null, url));
            }

            menupopup.appendChild(menuitem);
        }
        if (addManageItem) {
            // We didn't need a "more" item
            _addManageMRUMenuItem(prefName, menupopup, MRUName);
            addManageItem = false;
        }
    }

    // MRU is empty or does not exist
    else {
        // Add an empty one like this:
        //    <menuitem label="No Recent Files" disabled="true"/>
        menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", _bundle.formatStringFromName("No Recent.menuitem", [prettyName], 1));
        menuitem.setAttribute("disabled", true);
        menupopup.appendChild(menuitem);
    }
}


// This is a little wrapper for ko.views.manager.doFileNewFromTemplateAsync()
// that first checks to see if the template file exists, and if not: (1) does
// not call doFileNewFromTemplateAsync and (2) removes the template entry
// from the given MRU. The file/view will be opened asynchronously.
//
// XXX The *right* way to do this is for ko.views.manager.doFileNewFromTemplateAsync
//     to return an error (code or exception) if the template doesn't exist --
//     instead of bringing up an error dialog. Then we'd trap that error,
//     notify the user, and trim the MRU. As it is we (practically) have to
//     assume that the template URL is local.
this.newFileFromTemplateOrTrimMRU = function uilayout_newFileFromTemplateOrTrimMRU(templateURI, mruPrefName,
                                               mruIndex)
{
    var templatePath = null;
    try {
        templatePath = ko.uriparse.URIToLocalPath(templateURI);
    } catch (ex) {
        // Template URI is not local. Hope for the best. :)
    }
    if (templatePath) {
        var osPathSvc = Components.classes["@activestate.com/koOsPath;1"]
            .getService(Components.interfaces.koIOsPath)
        if (!osPathSvc.exists(templatePath)) {
            ko.dialogs.alert(_bundle.GetStringFromName("theTemplatePathCannotBeFound"),
                         templatePath);
            ko.mru.del(mruPrefName, mruIndex);
            return;
        }
    }

    ko.views.manager.doFileNewFromTemplateAsync(templateURI);
}

/**
 * Update the context menu for the toolbox
 */
this.updateToolboxContextMenu = function uilayout_updateToolboxContextMenu()
{
  var source = document.getElementById("popup_toolbars");
  var dest = document.getElementById("context-toolbox-menu");
  while (dest.firstChild) {
    dest.removeChild(dest.firstChild);
  }
  for each (var child in Array.slice(source.childNodes)) {
    var clone = child.cloneNode(true);
    clone.removeAttribute("id");
    for each (var elem in Array.slice(clone.querySelectorAll("[id]"))) {
      elem.removeAttribute("id");
    }
    dest.appendChild(clone);
  }
};


// Flags used to defer (re)building of the MRU menus until necessary.
var _gNeedToUpdateFileMRUMenu = false;
var _gNeedToUpdateProjectMRUMenu = false;
var _gNeedToUpdateTemplateMRUMenu = false;

this.updateMRUMenuIfNecessary = function uilayout_UpdateMRUMenuIfNecessary(mru, limit, popupId, force)
{
    if (typeof(limit) == "undefined") {
        limit = 0;
    }
    // (Re)build the identified MRU menu if necessary.
    //    "mru" is indicates which MRU menu to update.
    // Current possible values: project, file, template, window
    if (mru == "project" && (_gNeedToUpdateProjectMRUMenu || force)) {
        _updateMRUMenu("mruProjectList", limit,
                       true /* addManageItem */,
                       "Most Recent Projects", popupId);
        /*Note: "Most Recent Projects" is a bundle key in library.properties */
        if ( ! force) _gNeedToUpdateProjectMRUMenu = false;
    } else if (mru == "file" && (_gNeedToUpdateFileMRUMenu || force)) {
        _updateMRUMenu("mruFileList", limit, undefined, undefined, popupId);
        if ( ! force) _gNeedToUpdateFileMRUMenu = false;
    } else if (mru == "template" && (_gNeedToUpdateTemplateMRUMenu || force)) {
        _updateMRUMenu("mruTemplateList", limit, undefined, undefined, popupId);
        if ( ! force) _gNeedToUpdateTemplateMRUMenu = false;
    } else if (mru == "window") { // && _gNeedToUpdateTemplateMRUMenu) {
        this._updateMRUClosedWindowMenu(limit);
    }
}

this._updateMRUClosedWindowMenu = function(limit) {
    var menupopup = document.getElementById('popup_mruWindows');
    // Wipe out existing menuitems.
    while (menupopup.firstChild) {
        menupopup.removeChild(menupopup.firstChild);
    }
    this._windowInfoList = ko.workspace.getRecentClosedWindowList();
    var menuitem;
    for (var windowNum in this._windowInfoList) {
        //dump("Found windowNum " + windowNum + " in this._windowInfoList\n");
        menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", ko.uriparse.URIToPath(this._windowInfoList[windowNum].currentFile))
            menuitem.setAttribute("class", "menuitem_mru");
        menuitem.setAttribute("crop", "center");
        menuitem.setAttribute("oncommand",
                              "ko.uilayout._loadRecentWindow(" + windowNum + ");");
        menupopup.appendChild(menuitem);
    }
    if (menupopup.childNodes.length === 0) {
        // MRU is empty or does not exist
        // Add an empty one like this:
        //    <menuitem label="No Recent Files" disabled="true"/>
        menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", _bundle.formatStringFromName("No Recent.menuitem", [_bundle.GetStringFromName("Windows")], 1));
        menuitem.setAttribute("disabled", true);
        menupopup.appendChild(menuitem);
    }
}

this._loadRecentWindow = function(window_MRU_Num) {
    var windowState = this._windowInfoList[window_MRU_Num];
    delete this._windowInfoList;
    if (!windowState) {
        _log.error("_loadRecentWindow: Can't find windowItem " + window_MRU_Num + "\n");
        return;
    }
    ko.launch.newWindowForIndex(windowState.windowNum);
};

var gUilayout_Observer = null;
function _Observer ()
{
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    observerSvc.addObserver(this, "mru_changed",false);
    observerSvc.addObserver(this, "primary_languages_changed",false);
	
	// Progress throbber related events
	observerSvc.addObserver(this, 'status_message', false);
	
    var self = this;
    this.handle_current_view_changed_setup = function(event) {
        self.current_view_changed_common(event.originalTarget);
    };
    this.handle_view_list_closed_setup = function(event) {
        self.handle_view_list_closed(event);
    };
    window.addEventListener('current_view_changed',
                            this.handle_current_view_changed_setup, false);
    window.addEventListener('view_list_closed',
                            this.handle_view_list_closed_setup, false);
    window.addEventListener('current_project_changed',
                            this.handle_project_changed, false);
    window.addEventListener('project_opened',
                            this.handle_project_changed, false);
};
_Observer.prototype.destroy = function()
{
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    observerSvc.removeObserver(this, "mru_changed");
    observerSvc.removeObserver(this, "primary_languages_changed");

    window.removeEventListener('current_view_changed',
                               this.handle_current_view_changed_setup, false);
    window.removeEventListener('view_list_closed',
                               this.handle_view_list_closed_setup, false);
    window.removeEventListener('current_project_changed',
                               this.handle_project_changed, false);
    window.removeEventListener('project_opened',
                               this.handle_project_changed, false);
}
_Observer.prototype.observe = function(subject, topic, data)
{
    _log.info("Observing: " + topic);
    switch(topic) {
    case 'mru_changed':
        // Schedule update "File->Recent Files" and "File->Recent Projects"
        // menus.
        if (data == "mruFileList") {
            _gNeedToUpdateFileMRUMenu = true;
        } else if (data == "mruProjectList") {
            _gNeedToUpdateProjectMRUMenu = true;
        } else if (data == "mruTemplateList") {
            _gNeedToUpdateTemplateMRUMenu = true;
        }
        break;
    case 'primary_languages_changed':
        for (let id of ["statusbar-filetype-menu", "popup_viewAsLanguage"]) {
            let popup = document.getElementById(id);
            if (popup) {
                popup.removeAttribute("komodo_language_menu_already_built");
            }
        }
        break;
    case 'current_project_changed':
    case 'project_opened':
        ko.uilayout.updateTitlebar(ko.views.manager.currentView);
        break;
	case 'status_message':
		if (subject instanceof Ci.koINotificationProgress)
		{
			var throbber = document.getElementById("statusbar-throbber");
			if (subject.maxProgress == Ci.koINotificationProgress.PROGRESS_INDETERMINATE ||
				subject.maxProgress > subject.progress)
			{
				throbber.setAttribute("active", true);
				throbber.setAttribute("tooltiptext", subject.summary);
			}
			else
			{
				throbber.removeAttribute("active");
				throbber.setAttribute("tooltiptext", "");
			}
		}
		break;
    }
}

_Observer.prototype.current_view_changed_common = function(view) {
    if (!ko.views.manager.batchMode) {
        ko.uilayout.updateTitlebar(view);
    }

    ko.uilayout.updateViewDeck();
    ko.uilayout.updateViewRef(view);
}

_Observer.prototype.handle_project_changed = function(event) {
    ko.uilayout.updateTitlebar(ko.views.manager.currentView);
}

_Observer.prototype.handle_view_list_closed = function(event) {
    this.current_view_changed_common(null);
}

// Create and return on tab/window item at the bottom of the Window menu.
//
//  "view" is the view to which this menuitem is attached
//  "index" is the index in the list of views
//  "isCurrent" is a boolean indicating if the view is the current one.
//
function _updateWindowList_createMenuItem(view, index, isCurrent)
{
    try {
        var menuitem = document.createElement('menuitem');
        menuitem.setAttribute('data', 'fileItem');
        menuitem.setAttribute('id', view.uid);
        var labels = ko.views.labelsFromView(view, null, true);
        var label = labels[0];
        if (!label) {
            label = view.title;
        }
        label = (index + 1) + " " + label;
        menuitem.setAttribute("label", label);
        if (index+1 <= 9) {
            menuitem.setAttribute("accesskey", index+1);
        }
        menuitem.setAttribute('type', 'checkbox');
        if (labels[1]) {
            menuitem.setAttribute("tooltiptext", labels[1]);
        }
        if (isCurrent) {
            menuitem.setAttribute('checked', 'true');
            menuitem.setAttribute('class', 'primary_menu_item');
            // No need to switch view oncommand, this view is already current.
            // However we *do* need to ensure that the checkmark stays.
            // See http://bugs.activestate.com/show_bug.cgi?id=26423
            menuitem.setAttribute('oncommand',
                                  'event.target.setAttribute("checked", "true");');
        } else {
            menuitem.setAttribute('checked', 'false');
            menuitem.setAttribute('oncommand', 'this.view.makeCurrent();');
        }
        menuitem.view = view;
        return menuitem;
    } catch(ex) {
        _log.exception(ex, "error generating Window list "+
                                    "menuitem for '"+view.title+"'");
    }
    return null;
}

function _compareView(a, b) {
    var a_title = a.title.toLowerCase();
    var b_title = b.title.toLowerCase();
    if (a_title < b_title)
        return -1
    if (a_title > b_title)
        return 1
    return 0
}

// This updates the list in the Window menu.  The window menu calls
// this when it is being shown to reset itself.
this.updateWindowList = function uilayout_updateWindowList(popup) {
    try {
        var views = ko.views.manager.topView.getDocumentViews(true);
        // clear out checked items first
        var items = popup.getElementsByAttribute('data', 'fileItem');
        var i = 0;
        while (items.length > 0) {
            popup.removeChild(items[0]);
        }
        views.sort(_compareView);
        var mi;
        for (i=0; i < views.length; i++) {
            mi = _updateWindowList_createMenuItem(views[i], i,
                    (views[i] == ko.views.manager.currentView));
            if (mi) popup.appendChild(mi);
        }
    } catch(ex) {
        _log.exception(ex, "error re-generating Window menu list");
    }
}

function _buildMenuTree(hierarchy, toplevel) {
    var menu;
    var menupopup;
    var menuitem;
    var menuitems = [];
    var children = {};
    var i, j;

    if (hierarchy.container == true)  {
        // build menu
        hierarchy.getChildren(children, {} /* count */);
        children = children.value;

        for (i=0;i<children.length;i++)  {
            menuitems.push(_buildMenuTree(children[i], false));
        }
        if (!toplevel)  {
            menu = document.createElementNS(XUL_NS, 'menu');
            menu.setAttribute('label', hierarchy.name);
            menupopup = document.createElementNS(XUL_NS, 'menupopup');
            for (j=0; j < menuitems.length; j++)  {
                menupopup.appendChild(menuitems[j]);
            }
            menu.appendChild(menupopup);
            return menu;
        }
        return menuitems;

    } else {
        var languageNameNospaces = hierarchy.name.replace(' ', '', 'g')

        menuitem = document.createElementNS(XUL_NS, 'menuitem');
        menuitem.setAttribute("anonid", "menu_viewAs" + languageNameNospaces);
        menuitem.setAttribute('label', hierarchy.name);
        menuitem.setAttribute("accesskey", hierarchy.key);
        menuitem.setAttribute("type", "checkbox");
        menuitem.setAttribute("class", "languageicon");
        menuitem.setAttribute("language", hierarchy.name);
        menuitem.setAttribute("oncommand", "ko.views.manager.do_ViewAs('" + hierarchy.name + "');");

        return menuitem;
    }
}

// This updates the list in the View As ... menu.
// Called by uilayout_onload
this.buildViewAsLanguageMenu = function uilayout_buildViewAsLanguageMenu(menupopup) {
    // If we're rebuilding a menu, delete any existing nodes.
    while (menupopup.firstChild) {
        menupopup.removeChild(menupopup.firstChild);
    }

    // Load all the known languages into the menupopup.
    try {
        var langService = Components.classes["@activestate.com/koLanguageRegistryService;1"].
                    getService(Components.interfaces.koILanguageRegistryService);
        var langHierarchy = langService.getLanguageHierarchy();
        var menuitems = _buildMenuTree(langHierarchy, true);
        for (var i=0; i < menuitems.length; i++)  {
            menupopup.appendChild(menuitems[i]);
        }
    } catch (e) {
        _log.exception(e);
    }

    // Add separator and the reset to best guess menuitem.
    var menuitem = document.createElementNS(XUL_NS, 'menuseparator');
    menupopup.appendChild(menuitem);

    menuitem = document.createElementNS(XUL_NS, 'menuitem');
    menuitem.setAttribute("id", "menu_viewAsGuessedLanguage");
    menuitem.setAttribute("label", _bundle.GetStringFromName("resetToBestGuess"));
    menuitem.setAttribute("observes", "cmd_viewAsGuessedLanguage");
    menupopup.appendChild(menuitem);
}

function _setCheckedLanguage(menupopup, language)
{
    _log.info("in _setCheckedLanguage");
    var i;
    var id;
    var child;
    var childnodes = menupopup.getElementsByTagName('menuitem');
    for (i = 0; i < childnodes.length; i++) {
        child = childnodes[i];
        if (child.getAttribute('language') == language) {
            child.setAttribute('checked', 'true');
        } else {
            child.setAttribute('checked', 'false');
        }
    }
}

this.updateViewAsLanguageMenu = function uilayout_updateViewAsLanguageMenu(menupopup, view)
{
    if (!menupopup.hasAttribute("komodo_language_menu_already_built")) {
        // Build the menu;
        ko.uilayout.buildViewAsLanguageMenu(menupopup);
        menupopup.setAttribute("komodo_language_menu_already_built", "true");
    }

    if (!view) {
        view = ko.views.manager.currentView;
        if (!view) {
            return;
        }
    }
    // Mark the current view's language.
    _setCheckedLanguage(menupopup, view.language);
}


this.outputPaneShown = function uilayout_outputPaneShown()
{
    return !window.document.getElementById("workspace_bottom_area").collapsed;
};

this.leftPaneShown = function uilayout_leftPaneShown()
{
    return !window.document.getElementById("workspace_left_area").collapsed;
};

this.rightPaneShown = function uilayout_rightPaneShown()
{
    return !window.document.getElementById("workspace_right_area").collapsed;
};

this.isCodeBrowserTabShown = function uilayout_isCodeBrowserTabShown()
{
    _log.deprecated('ko.uilayout.isCodeBrowserTabShown is just an alias for ' +
                    'ko.uilayout.isTabShown("codebrowserviewbox")');
    return this.isTabShown("codebrowserviewbox");
};

this.ensureOutputPaneShown = function uilayout_ensureOutputPaneShown()
{
    // This is just hilariously badly named
    _log.deprecated('ko.uilayout.ensureOutputPaneShown is unlikely to be ' +
                    'what you wanted to call; try something like ' +
                    '"<your-widget>.containerPane.collapsed = false" instead.');
    ko.widgets.getPaneAt('workspace_bottom_area').collapsed = false;
};

this.ensurePaneForTabHidden = function uilayout_ensurePaneForTabHidden(tabName)
{
    // given a tab id, collapse the pane that the tab is in.
    let widget = ko.widgets.getWidget(tabName);
    if (widget && widget.containerPane) {
        widget.containerPane.collapsed = true;
    }
};

/**
 * Returns whether the given pane is currently opened/visible in Komodo.
 *
 * @param pane {object | id} - The pane element, or the id of the pane element.
 * @returns {boolean} Whether this pane is shown.
 */
this.isPaneShown = function uilayout_isPaneShown(pane) {
    if (typeof(pane) == 'string') {
        // It's the id of the pane.
        var paneId = pane;
        pane = document.getElementById(paneId);
        if (!pane) {
            _log.error("isPaneShown: no pane with the id: " + paneId);
            return false;
        }
    }
    return !pane.collapsed;
};

/**
 * Makes the given pane open/visible in Komodo.
 *
 * @param pane {object | id} - The pane element, or the id of the pane element.
 */
this.ensurePaneShown = function uilayout_ensurePaneShown(aPane) {
    let pane = ko.widgets.getWidget(aPane) || aPane;
    if (pane && pane.containerPane) {
        pane = pane.containerPane;
    }
    if (!pane || !pane.id || (ko.widgets.panes.indexOf(pane.id) < 0)) {
        pane = ko.widgets.getPaneAt(aPane) || aPane;
    }
    if (!pane || !pane.id || (ko.widgets.panes.indexOf(pane.id) < 0)) {
        _log.error("ensurePaneShown: no pane with the id: " + aPane);
    }
    pane.collapsed = false;
};


/**
 * Makes the given pane open/visible in Komodo.
 *
 * @param pane {object | id} - The pane element, or the id of the pane element.
 */
this.ensurePaneShown = function uilayout_ensurePaneShown(aPane) {
    let pane = ko.widgets.getWidget(aPane) || aPane;
    if (pane && pane.containerPane) {
        pane = pane.containerPane;
    }
    if (!pane || !pane.id || (ko.widgets.panes.indexOf(pane.id) < 0)) {
        pane = ko.widgets.getPaneAt(aPane) || aPane;
    }
    if (!pane || !pane.id || (ko.widgets.panes.indexOf(pane.id) < 0)) {
        _log.error("ensurePaneShown: no pane with the id: " + aPane);
    }
    pane.collapsed = false;
};

/**
 * Makes the given pane closed/invisible in Komodo.
 *
 * @param pane {object | id} - The pane element, or the id of the pane element.
 */
this.ensurePaneHidden = function uilayout_ensurePaneHidden(aPane) {
    let pane = ko.widgets.getWidget(aPane) || aPane;
    if (pane && pane.containerPane) {
        pane = pane.containerPane;
    }
    if (!pane || !pane.id || (ko.widgets.panes.indexOf(pane.id) < 0)) {
        pane = ko.widgets.getPaneAt(aPane) || aPane;
    }
    if (!pane || !pane.id || (ko.widgets.panes.indexOf(pane.id) < 0)) {
        _log.error("ensurePaneHidden: no pane with the id: " + aPane);
    }
    pane.collapsed = true;
};

this.isTabShown = function uilayout_isTabShown(widgetId) {
    var widget;
    try {
        var widget;
        if ((typeof(widgetId) == "object") && ("localName" in widgetId)) {
            if ("linkedpanel" in widgetId) {
                // we literally got the <tab>.
                widget = widgetId.linkedpanel;
            } else {
                // we actually got passed the widget instead
                widget = widgetId;
            }
        } else {
            var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                            .getService(Components.interfaces.nsIWindowMediator);
            var mainWindow = wm.getMostRecentWindow('Komodo');
            widget = mainWindow.document.getElementById(widgetId);
            if (!widget) {
                _log.error("ko.uilayout.isTabShown: couldn't find tab: " + widgetId);
                return false;
            }
        }

        return this.isPaneShown(widget.containerPane) &&
               xtk.domutils.containsElement(widget.containerPane.selectedPanel, widget);
    } catch (e) {
        _log.exception(e);
    }
    return false;
};

this.ensureTabShown = function uilayout_ensureTabShown(widgetId, focusToo) {
    try {
        if (typeof(focusToo) == 'undefined') focusToo = false;
        let callback = function (widget) {
            if (!widget) {
                _log.error("ko.uilayout.ensureTabShown: Can't find widget: " + widgetId);
                return;
            }
            // always select the widget
            widget.containerPane.addWidget(widget, {focus: true});
            if (focusToo) {
                // Also focus it...
                if (widget.contentWindow) {
                    widget.contentWindow.focus();
                    // Dispatch an event to say we're programmatically focusing the
                    // widget.
                    var event = widget.contentWindow.document.createEvent("Events");
                    event.initEvent("ko-widget-focus", true, false);
                    widget.contentWindow.dispatchEvent(event);
                } else {
                    // This shouldn't happen... but whatever.
                    widget.focus();
                }
            }
        }
        if ((typeof(widgetId) == "object") && ("localName" in widgetId)) {
            if ("linkedpanel" in widgetId) {
                // we literally got the <tab>.
                callback(widgetId.linkedpanel);
            } else {
                // we actually got passed the widget instead
                callback(widgetId);
            }
        } else {
            var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                            .getService(Components.interfaces.nsIWindowMediator);
            var mainWindow = wm.getMostRecentWindow('Komodo');
            mainWindow.ko.widgets.getWidgetAsync(widgetId, callback);
        }
    } catch (e) {
        _log.exception(e);
    }
}

/* Update the titlebar
   Have to keep in mind debugging state */
this.updateTitlebar = function uilayout_updateTitlebar(view)  {
    var viewPart = "";
    var preProjectPart, projectPart, postProjectPart;
    var postTitlePart = "";
    var projectRootName = ko.projects.manager.projectBaseName();
    if (view == null)  {
        if (projectRootName) {
            preProjectPart = "(";
            postProjectPart = ")";
        } else {
            preProjectPart = postProjectPart = "";
        }
    } else {
        viewPart = view.title;
        if (view.isDirty)  {
            viewPart += "*";
        }
        if (view.koDoc &&
            view.koDoc.file) {
            var fullPath = (view.koDoc.file.isLocal
                            ? view.koDoc.file.dirName
                            : view.koDoc.displayPath);
            viewPart += ' (' + ko.stringutils.contractUser(fullPath);
            if (projectRootName) {
                preProjectPart = ", ";
            }
            postProjectPart = "";
            postTitlePart = ")";
        } else if (projectRootName) {
            preProjectPart = " (";
            postProjectPart = ")";
        }
    }
    if (projectRootName) {
        viewPart += (preProjectPart
                     + _bundle.GetStringFromName("Project")
                     + " "
                     + projectRootName
                     + postProjectPart
                     );
    }
    viewPart += postTitlePart;
    var title = viewPart;

    var branding = '';
//#if PLATFORM == "darwin"
    if (!title) { // No branding in titlebar by default on Mac OS X.
        branding = "PP_KO_TITLE_BAR_NAME";
    }
//#else
    if (title) {
        branding += " - ";
    }
    branding += "PP_KO_TITLE_BAR_NAME";
//#endif

    document.title = title + branding;
}


this.unload = function uilayout_unload()
{
    gUilayout_Observer.destroy();
    gUilayout_Observer = null;
    _prefobserver.destroy();
    // XXX: These prefs should be saved as part of the workspace.
	_gPrefs.setBooleanPref("startupFullScreen", window.fullScreen)
    // nsIDOMChromeWindow STATE_MAXIMIZED = 1
    _gPrefs.setBooleanPref("startupMaximized", window.windowState==1)
}

/**
 * Various UI layout tweaks needed between Komodo versions.
 */
function uilayout_upgrade() {
    // Remove localstore.rdf attributes that were moved into prefs.
    var rdfs = Components.classes["@mozilla.org/rdf/rdf-service;1"]
                         .getService(Components.interfaces.nsIRDFService);
    var ds = rdfs.GetDataSource("rdf:local-store");
    var removePersistAttributes = function(id, persist_attributes) {
        let source = rdfs.GetResource(document.location.href + "#" + id);
        if (!source) {
            return;
        }
        for (let [,attr] in Iterator(persist_attributes)) {
            var prop = rdfs.GetResource(attr);
            var arcs = ds.GetTargets(source, prop, true);
            while (arcs.hasMoreElements()) {
                ds.Unassert(source, prop, arcs.getNext());
            }
        }
    }

    // As of Komodo 8.0 RC1 the toolbox is hidden using the parent wrapper
    // We should therefore remove the collapsed state (if any) on the main toolbox
    // This can probably be removed by Komodo 8.*
    removePersistAttributes("main-toolboxrow",
                            ['collapsed','kohidden', 'hidden']);

    // As of Komodo 8.0, the side pane collapsed states are managed by prefs.
    let workspace_ids = ["workspace_left_area",
                         "workspace_right_area",
                         "workspace_bottom_area"];
    for (let workspace_id of workspace_ids) {
        removePersistAttributes(workspace_id, ['collapsed']);
    }
}

this.onload = function uilayout_onload()
{
    var uilayout_version = 1;
    if (_gPrefs.getLong("uilayout_version", 0) < uilayout_version) {
        uilayout_upgrade();
        _gPrefs.setLong("uilayout_version", uilayout_version);
    }

    ko.uilayout.updateToolbarArrangement();
    _gNeedToUpdateFileMRUMenu = true;
    _gNeedToUpdateProjectMRUMenu = true;
    _gNeedToUpdateTemplateMRUMenu = true;
    gUilayout_Observer = new _Observer();
    _prefobserver = new _PrefObserver();
    _prefobserver.init();
    _updateAccesskeys();
    _updateHiddenToolbars();
    this._updateToolbarViewStates();
    this._updateToolbarSeparators();
    ko.main.addWillCloseHandler(ko.uilayout.unload);

// #if PLATFORM != "darwin"
    function trackMenuItemMru(e) {
        if (e.target.nodeName != 'menuitem') return;
        MruMenusAddItem(e.target);
    }

    document.getElementById('unifiedMenuButton').addEventListener('command', trackMenuItemMru);
    document.getElementById('menubar_main').addEventListener('command', trackMenuItemMru);

    // Also track click events, as not all menuitem's fire a command event
    document.getElementById('unifiedMenuButton').addEventListener('click', trackMenuItemMru);
    document.getElementById('menubar_main').addEventListener('click', trackMenuItemMru);
    
    document.getElementById('unifiedMenuPopup').addEventListener('popupshowing', ko.uilayout.cloneUnifiedMenuItems.bind(ko.uilayout));

    ko.uilayout.setMenubarVisibility();
// #endif

    if ( ! ko.views.manager.getAllViews().length) {
        ko.open.quickStart();
    }
    
    this.updateViewRef();
}

this.updateViewRef = function(view) {
    if ( ! view) {
        view = ko.views.manager.currentView;
    }

    var viewType = "";
    var deck = document.getElementById('editorviewbox');
    deck.selectedPanel = document.getElementById("editorvbox");
    
    var hasViews = tv.currentView.currentView || tv.otherView.currentView;
    if ( ! hasViews) {
        ko.open.quickStart();
    }
 }

this.updateViewDeck = function() {
    var tv = document.getElementById("topview");
    var deck = document.getElementById('editorviewbox');
    var hasViews = tv.currentView.currentView || tv.otherView.currentView;

    if ( ! hasViews) {
        deck.selectedPanel = document.getElementById("quicklaunch");
    } else
    {
        deck.selectedPanel = document.getElementById("editorvbox");
    }
 }

this._setTabPaneLayoutForTabbox = function(layout, pane, position) {
    if (position == "right" && layout != "vertical") {
        pane.removeAttribute("dir");
    }
    switch (layout) {
        case "sidebar":
        case "horizontal":
            if (pane.getAttribute("type") == "vertical") {
                // Ensure to properly unhook the vertical tabs event handlers
                // when switching bindings - otherwise exceptions will be raised
                // when any adding/deleting of nodes occurs.
                pane.tabs.unHookBinding();
            }
            break;
        case "vertical":
            if (position == "left") {
                pane.setAttribute("rotation", "270");
            } else if (position == "right") {
                pane.setAttribute("rotation", "90");
            }
            break;
    }
    pane.setAttribute("type", layout);
}

/**
 * Sets the user's tab pane layout to match the Komodo appearance preferences.
 */
this.setTabPaneLayout = function uilayout_setTabPaneLayout() {
    // Set the tab pane layout.
    var leftTabStyle = _gPrefs.getStringPref("ui.tabs.sidepanes.left.layout");
    var leftTabbox = document.getElementById("workspace_left_area");
    ko.uilayout._setTabPaneLayoutForTabbox(leftTabStyle, leftTabbox, "left");

    var rightTabStyle = _gPrefs.getStringPref("ui.tabs.sidepanes.right.layout");
    var rightTabbox = document.getElementById("workspace_right_area");
    ko.uilayout._setTabPaneLayoutForTabbox(rightTabStyle, rightTabbox, "right");

    var bottomTabStyle = _gPrefs.getStringPref("ui.tabs.sidepanes.bottom.layout");
    var bottomTabbox = document.getElementById("workspace_bottom_area");
    ko.uilayout._setTabPaneLayoutForTabbox(bottomTabStyle, bottomTabbox, "bottom");
}

/**
 * Restore generic window state, fullscreen, maximized and sidepane tab layout.
 *
 * Note: Must be called after the window is fully initialized (i.e. after the
 *       Mozilla window persist has done it's thing).
 */
this.restoreWindowState = function uilayout_restoreWindowState()
{
    try {
        if (_gPrefs.getBooleanPref("startupFullScreen")) {
            window.fullScreen = true;
        }
        else if (_gPrefs.getBooleanPref("startupMaximized")) {
            window.maximize();
        }

        ko.uilayout.setTabPaneLayout();
    } catch (e) {
        _log.exception("Couldn't restore layout:" + e);
    }
}

var _prefobserver;

function _updateAccesskeys() {
    var menus = new Object();
    var count = new Object();
    var menu;
    var menubar;
    var extra_ids = ['open_label', 'find_label'];
    var i;
    var item;

    var enable = ! _gPrefs.getBooleanPref("keybindingDisableAccesskeys");

    menubar = document.getElementById('menubar_main');
    menus = menubar.childNodes;
    for (i = 0; i < menus.length; i++) {
        menu = menus[i];
        _enableAccesskey(menu, enable);
    }
    for (i = 0; i < extra_ids.length; i++) {
        item = document.getElementById(extra_ids[i]);
        if (item) {
            _enableAccesskey(item, enable);
        }
    }
}

function _enableAccesskey(elt, enable) {
    if (enable) {
        if (elt.hasAttribute('_accesskey')) {
            elt.setAttribute('accesskey', elt.getAttribute('_accesskey'));
            elt.removeAttribute('_accesskey');
        }
    } else {
        if (elt.hasAttribute('accesskey')) {
            elt.setAttribute('_accesskey', elt.getAttribute('accesskey'));
            elt.removeAttribute('accesskey');
        }
    }
}

/**
 * Change from use "hidden" attribute to using the "kohidden" attribute.
 *
 * Note: This function can be dropped in Komodo 7.1.
 */
function _updateHiddenToolbars()
{
    var mainToolbox = document.getElementById("toolbox_main");
    var toolbars = mainToolbox.getElementsByTagName('toolbar');
    for (var i=0; i < toolbars.length; i++ ) {
        if (toolbars[i].getAttribute("hidden")) {
            if (toolbars[i].getAttribute("hidden") == "true") {
                toolbars[i].setAttribute("kohidden", "true");
            } else {
                toolbars[i].setAttribute("kohidden", "false");
            }
            toolbars[i].removeAttribute("hidden");
            _log.debug("Migrating hidden toolbar " + toolbars[i].id);
        }
    }
}

// A pref observer to watch for ui-related pref changes.
function _PrefObserver() {};
_PrefObserver.prototype.observe = function(prefSet, prefName, prefSetID)
{
    if (prefName == "keybindingDisableAccesskeys") {
        _updateAccesskeys();

    } else if (prefName == "ui.tabs.sidepanes.left.layout") {
        // Set the tab pane layout.
        var leftTabStyle = _gPrefs.getStringPref("ui.tabs.sidepanes.left.layout");
        var leftTabbox = document.getElementById("workspace_left_area");
        ko.uilayout._setTabPaneLayoutForTabbox(leftTabStyle, leftTabbox, "left");

    } else if (prefName == "ui.tabs.sidepanes.right.layout") {
        var rightTabStyle = _gPrefs.getStringPref("ui.tabs.sidepanes.right.layout");
        var rightTabbox = document.getElementById("workspace_right_area");
        ko.uilayout._setTabPaneLayoutForTabbox(rightTabStyle, rightTabbox, "right");

    } else if (prefName == "ui.tabs.sidepanes.bottom.layout") {
        var bottomTabStyle = _gPrefs.getStringPref("ui.tabs.sidepanes.bottom.layout");
        var bottomTabbox = document.getElementById("workspace_bottom_area");
        ko.uilayout._setTabPaneLayoutForTabbox(bottomTabStyle, bottomTabbox, "bottom");
    }
};

_PrefObserver.topics = [
    "keybindingDisableAccesskeys",
    "ui.tabs.sidepanes.left.layout",
    "ui.tabs.sidepanes.right.layout",
    "ui.tabs.sidepanes.bottom.layout",
];

_PrefObserver.prototype.init = function() {
    _gPrefs.prefObserverService.addObserverForTopics(this, _PrefObserver.topics.length, _PrefObserver.topics, false);
}

_PrefObserver.prototype.destroy = function() {
    _gPrefs.prefObserverService.removeObserverForTopics(this, _PrefObserver.topics.length, _PrefObserver.topics, false);
}



}).apply(ko.uilayout);

