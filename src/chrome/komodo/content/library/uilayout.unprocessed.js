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
var XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

var _log = ko.logging.getLogger('uilayout');

// Toggle the visibility of the specified toolbar,
// along with the corresponding broadcaster if it exists.
this.toggleToolbarVisibility = function uilayout_toggleToolbarVisibility(toolbarId)
{
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
    if (toolbar.hidden) {
        toolbar.setAttribute("hidden", "false");
        broadcaster.setAttribute("checked", "true");
    } else {
        toolbar.setAttribute("hidden", "true");
        broadcaster.setAttribute("checked", "false");
        // reflow the toolbars now that we removed a toolbar
        document.getElementById('toolbox_main').update(true);
    }
}

// XRE toolbar does not have toolbar.update.  this is duplicated
// from the xpfe toolbar widget, and will make our stuff work
// with either XRE or XPFE
function _updateToolbarButtonText(tbElt,tag,style) {
    var elements = tbElt.getElementsByTagName(tag);
    for (var i = 0; i < elements.length; i++) {
        elements[i].setAttribute("buttonstyle", style);
    }
}

// 'toolbarId' is the id of the toolbar that should be affected
// 'show' is a boolean -- true means show the text.
function _setToolbarButtonText(toolbarId, buttonTextShowing)
{
    var toolbar = document.getElementById(toolbarId);
    if (!toolbar) {
        _log.error("Could not find toolbar with id: " + toolbarId);
    }
    try {
        if (buttonTextShowing) {
            toolbar.removeAttribute('buttonstyle');
            _updateToolbarButtonText(toolbar, 'toolbarbutton', null);
        } else {
            toolbar.setAttribute('buttonstyle','pictures');
            _updateToolbarButtonText(toolbar, 'toolbarbutton', 'pictures');
        }
    } catch(e) {
        _log.error(e);
    }
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
    _setToolbarButtonText('standardToolbar', buttonTextShowing);
    _setToolbarButtonText('debuggerToolbar', buttonTextShowing);
    _setToolbarButtonText('workspaceToolbar', buttonTextShowing);
    ko.uilayout.updateToolbarArrangement(buttonTextShowing);
    document.persist('cmd_toggleButtonText', 'checked');
}

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
    var toolbars = document.getElementsByTagName('toolbar');
    var i;
    for (i = 0; i < toolbars.length; i++ ) {
        // Note: this can include custom toolbars
        _setToolbarButtonText(toolbars[i].id, buttonTextShowing);
    }
    // be sure the toolbars reflow
    document.getElementById('toolbox_main').update(true);
}


this.populatePreviewToolbarButton = function uilayout_populatePreviewToolbarButton(popup)
{
    // Only do this once.
    // XXX We'll need to remove it's children when prefs are changed.
    if (popup.childNodes.length > 0)
        return;

    var koWebbrowser = Components.classes["@activestate.com/koWebbrowser;1"].
                       getService(Components.interfaces.koIWebbrowser);
    var browsers = koWebbrowser.get_possible_browsers(new Object());
    var mi;

// #if PLATFORM == "win"
    mi = document.createElementNS(XUL_NS, "menuitem");
    mi.setAttribute("label", "Configured Browser");
    mi.setAttribute("tooltiptext", "See Preferences | Web & Browser");
    mi.setAttribute("oncommand",
                    "ko.views.manager.currentView.viewPreview(); event.stopPropagation();");
    popup.appendChild(mi);
// #endif

    var browserURI;
    for (var i = 0; i < browsers.length; i++) {
        mi = document.createElementNS(XUL_NS, "menuitem");
        mi.setAttribute("label", browsers[i]);
        mi.setAttribute("crop", "center");
        mi.setAttribute("tooltiptext", ko.uriparse.baseName(browsers[i]));
        browserURI = ko.uriparse.localPathToURI(browsers[i]);
        mi.setAttribute("oncommand",
                        "ko.views.manager.currentView.viewPreview('"+browserURI+"'); event.stopPropagation();");
        popup.appendChild(mi);
    }
}

this.focusPane = function uilayout_focusPane(tabsId)
{
    var tabs = document.getElementById(tabsId);
    var tabId = tabs.selectedItem.getAttribute('id');
    ko.uilayout.toggleTab(tabId, false);
}

this.toggleTab = function uilayout_toggleTab(tabId, collapseIfFocused /* =true */)
{
    try {
        // if called with collapseIfFocused=false, we will only ensure that
        // the specified tab is focused and will not collapse any panels
        if (typeof(collapseIfFocused) == 'undefined')
            collapseIfFocused = true;
        var tab = document.getElementById(tabId);
        var tabs = tab.parentNode;
        var splitterId = tabs.getAttribute('splitterId');
        var splitterWidget = document.getElementById(splitterId);
        // If the pane in question is not shown and focused, then show it and
        // focus the relevant widget. The "focusHandlingWidget" must maintain
        // a .focused attribute.
        var focusHandlingWidget = null;
        switch (tabId) {
            case 'project_tab':
                focusHandlingWidget = document.getElementById('projectview').tree;
                break;
            case 'toolbox_tab':
                focusHandlingWidget = document.getElementById('toolboxview').tree;
                break;
            case 'codebrowser_tab':
                focusHandlingWidget = document.getElementById('codebrowser-tree');
                break;
        }
        var cmdId = splitterWidget.getAttribute('splitterCmdId');
        if (splitterWidget.hasAttribute('collapsed') &&
            splitterWidget.getAttribute('collapsed') == 'true') {
            ko.uilayout.toggleSplitter(cmdId);
            tabs.selectedItem = tab;
            focusHandlingWidget.focus();
        } else {
            if (collapseIfFocused) {
                // Before we collapse it, figure out whether the focus is in this
                // panel.  If so, then move it back to the editor
                if (xtk.domutils.elementInFocus(tabs.parentNode)) {
                    if (ko.views.manager.currentView) {
                        ko.views.manager.currentView.setFocus();
                    }
                }
                ko.uilayout.toggleSplitter(cmdId);
            } else {
                tabs.parentNode.selectedTab = tab;
                if (focusHandlingWidget)
                    focusHandlingWidget.focus();
                else
                    tabs.parentNode.selectedTab.focus();
            }
        }
    } catch (e) {
        log.exception(e);
    }
}


this.updateTabpickerMenu = function uilayout_updateTabpickerMenu(menupopup)
{
    try {
        var ids = [// left pane tabs
                   'project_tab',
                   'toolbox_tab',
                   // bottom pane tabs
                   'findresults1_tab',
                   'findresults2_tab', 'runoutput_tab',
                   ];
        var id, tab, menuitem, pane;
        for (var i = 0; i < ids.length; i++) {
            id = ids[i];
            tab = document.getElementById(id);
            pane = tab.parentNode.parentNode.parentNode;
            menuitem = document.getElementById('show_' + id);
            if (!tab || tab.collapsed) {
                menuitem.setAttribute('collapsed', 'true');
                menuitem.setAttribute('hidden', 'true');
                continue;
            }
            if (!menuitem) {
                log.error("Couldn't find menuitem with id: " + 'show_'+id);
                return;
            }
            //ko.trace.get().dumpDOM(pane);
            //ko.trace.get().dumpDOM(tab.parentNode);
            menuitem.removeAttribute('collapsed');
            menuitem.removeAttribute('hidden');
            if (tab.selected && ! pane.collapsed) {
                menuitem.setAttribute('checked', 'true');
            } else {
                menuitem.removeAttribute('checked');
            }
        }
    } catch (e) {
        log.exception(e);
    }
}

this.togglePane = function uilayout_togglePane(splitterId, tabsId, cmdId, force)
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
        var splitterWidget = document.getElementById(splitterId);
        var tabs = document.getElementById(tabsId);
        if (!force &&
            splitterWidget.hasAttribute('collapsed') &&
            splitterWidget.getAttribute('collapsed') == 'true') {
            ko.uilayout.toggleSplitter(cmdId);
            tabs.selectedItem.focus();
        } else {
            // Before we collapse it, figure out whether the focus is in this
            // panel.  If so, then move it back to the editor
            if (xtk.domutils.elementInFocus(tabs.parentNode)) {
                if (ko.views.manager.currentView) {
                    ko.views.manager.currentView.setFocus();
                } else {
                    // probably no file open to focus on, need to focus someplace else
                    window.focus();
                }
            }
            ko.uilayout.toggleSplitter(cmdId);
        }
    } catch (e) {
        log.exception(e);
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
    var splitterId = elt.getAttribute('splitter')
    var splitter = document.getElementById(splitterId)
    if (!splitter) {
        _log.error("couldn't find " + splitterId);
        return;
    }

    if (! box.hasAttribute('collapsed') || box.getAttribute("collapsed") == "false") {
        box.setAttribute('collapsed','true');
        splitter.setAttribute('collapsed','true');
        elt.removeAttribute('checked');
    } else {
        box.setAttribute('collapsed','false');
        splitter.setAttribute('collapsed','false');
        elt.setAttribute('checked', 'true');
    }
}

this.updateSplitterBroadcasterState = function uilayout_updateSplitterBroadcasterState(aCommandID) {
    var elt = document.getElementById(aCommandID);
    if (!elt) {
        _log.error("ko.uilayout.toggleSplitter: couldn't find '" + aCommandID + "'");
        return;
    }
    var boxId = elt.getAttribute('box');
    var box = document.getElementById(boxId)
    if (!box) {
        _log.error("couldn't find " + boxId);
        return;
    }
    var splitterId = elt.getAttribute('splitter')
    var splitter = document.getElementById(splitterId)
    if (!splitter) {
        _log.error("couldn't find " + splitterId);
        return;
    }

    if (! box.hasAttribute('collapsed') ||
        box.getAttribute("collapsed") == "false") {
        elt.setAttribute('checked', 'true');
    } else {
        elt.removeAttribute('checked');
    }
}

this.updateFullScreen = function uilayout_updateFullScreen() {
// #if PLATFORM != "darwin"
    // Update whether the checkbox for full screen is checked or not.
    var menuitem = document.getElementById('menuitem_fullScreen');
    if (window.fullScreen) {
        menuitem.setAttribute('checked', 'true');
    } else {
        menuitem.removeAttribute('checked');
    }
// #endif
}

this.fullScreen = function uilayout_FullScreen()
{
// #if PLATFORM != "darwin"
    window.fullScreen = !window.fullScreen;
    var windowControls = document.getElementById('window-controls');
    if (window.fullScreen) {
        window.maximize();
        windowControls.removeAttribute('hidden');
    } else {
        window.restore();
        windowControls.setAttribute('hidden', 'true');
    }
// #endif
}

this.onFullScreen = function uilayout_onFullScreen()
{
// #if PLATFORM != "darwin"
  FullScreen.toggle();
// #endif
}

// for whatever reason, toolkit/content/fullScreen.js is not included
// in the base mozilla builds.  this is take from there (firefox browser
// also copies this into its own sources).
var FullScreen = 
{
  toggle: function()
  {
    // show/hide all menubars, toolbars, and statusbars (except the full screen toolbar)
    this.showXULChrome("menubar", window.fullScreen);
    this.showXULChrome("toolbar", window.fullScreen);
    this.showXULChrome("statusbar", window.fullScreen);
  },
  
  showXULChrome: function(aTag, aShow)
  {
    var XULNS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
    var els = document.getElementsByTagNameNS(XULNS, aTag);
    
    var i;
    for (i = 0; i < els.length; ++i) {
      // XXX don't interfere with previously collapsed toolbars
      if (els[i].getAttribute("fullscreentoolbar") == "true") {
        this.setToolbarButtonMode(els[i], aShow ? "" : "small");
      } else {
        // use moz-collapsed so it doesn't persist hidden/collapsed,
        // so that new windows don't have missing toolbars
        if (aShow)
          els[i].removeAttribute("moz-collapsed");
        else
          els[i].setAttribute("moz-collapsed", "true");
      }
    }

// #if PLATFORM != "darwin"
    var controls = document.getElementsByAttribute("fullscreencontrol", "true");
    for (i = 0; i < controls.length; ++i)
      controls[i].hidden = aShow;
// #endif
  },
  
  setToolbarButtonMode: function(aToolbar, aMode)
  {
    aToolbar.setAttribute("toolbarmode", aMode);
    this.setToolbarButtonModeFor(aToolbar, "toolbarbutton", aMode);
    this.setToolbarButtonModeFor(aToolbar, "button", aMode);
    this.setToolbarButtonModeFor(aToolbar, "textbox", aMode);
  },
  
  setToolbarButtonModeFor: function(aToolbar, aTag, aMode)
  {
    var XULNS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
    var els = aToolbar.getElementsByTagNameNS(XULNS, aTag);

    for (var i = 0; i < els.length; ++i) {
      els[i].setAttribute("toolbarmode", aMode);
    }
  }
  
};

function _updateMRUMenu(prefName)
{
    // Update a MRU menu popup under the file menu.
    //    "prefName" indicate which MRU menu to update.
    //
    // XXX This code was significantly complitcated just for the special
    //     template MRU menu under File->New. Perhaps that should be
    //     factored out.
    var popupId, separatorId, prettyName;
    if (prefName == "mruProjectList") {
        popupId = "popup_mruProjects"; // MRU list is the whole popup.
        separatorId = null;
        prettyName = "Projects";
    } else if (prefName == "mruFileList") {
        popupId = "popup_mruFiles"; // MRU list is the whole popup.
        separatorId = null;
        prettyName = "Files";
    } else if (prefName == "mruTemplateList") {
        popupId = null;
        separatorId = "separator_mruTemplates"; // MRU list is everything after the separator.
        prettyName = "Templates";
    } else {
        throw("Unexpected MRU menu to update: prefName='"+prefName+"'");
    }

    var menupopup = popupId ? document.getElementById(popupId) : null;
    var separator = separatorId ? document.getElementById(separatorId) : null;
    var mruList = null;
    var menuitem;
    if (gPrefs.hasPref(prefName)) {
        mruList = gPrefs.getPref(prefName);
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
        //              oncommand="ko.views.manager.doFileNewFromTemplate('URL');"
        //              label="URL_BASENAME"/>
        if (!menupopup) {
            menupopup = separator.parentNode;
        }
        var length = mruList.length;
        for (var i = 0; i < length; i++) {
            var url = mruList.getStringPref(i);
            menuitem = document.createElement("menuitem");
            // Mozilla does not handle duplicate accesskeys, so only putting
            // them on first 10.
            if ((i+1) <= 9) {
                menuitem.setAttribute("accesskey", "" + (i+1));
            } else if ((i+1) == 10) {
                menuitem.setAttribute("accesskey", "0");
            }
            if (prefName == "mruTemplateList") {
                menuitem.setAttribute("label", (i+1)+" "+ko.uriparse.baseName(url));
            } else {
                menuitem.setAttribute("label", (i+1)+" "+ko.uriparse.displayPath(url));
            }
            menuitem.setAttribute("class", "menuitem_mru");
            menuitem.setAttribute("crop", "center");
            // XXX:HACK: For whatever reason, the "observes" attribute is
            // ignored when the menu item is inside a popup, so we call
            // ko.commands.doCommand directly. THIS IS NOT A GOOD THING!
            if (prefName == "mruTemplateList") {
                menuitem.setAttribute("oncommand",
                    "ko.uilayout.newFileFromTemplateOrTrimMRU('"+url+"', '"+prefName+"',"+i+");");
            } else {
                menuitem.setAttribute("oncommand",
                                      "ko.open.URI('" + url + "')");
            }

            menupopup.appendChild(menuitem);
        }
    }

    // MRU is empty or does not exist
    else {
        // Add an empty one like this:
        //    <menuitem label="No Recent Files" disabled="true"/>
        menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", "No Recent "+prettyName);
        menuitem.setAttribute("disabled", true);
        menupopup.appendChild(menuitem);
    }
}


// This is a little wrapper for ko.views.manager.doFileNewFromTemplate() that first
// checks to see if the template file exists, and if not: (1) does not
// call doFileNewFromTemplate and (2) removes the template entry from the
// given MRU.
//
// XXX The *right* way to do this is for ko.views.manager.doFileNewFromTemplate
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
            ko.dialogs.alert("The template path cannot be found. The entry in your "
                         +"'Recent Templates' list will be removed.",
                         templatePath);
            ko.mru.del(mruPrefName, mruIndex);
            return null;
        }
    }
    
    return ko.views.manager.doFileNewFromTemplate(templateURI);
}


// Flags used to defer (re)building of the MRU menus until necessary.
var _gNeedToUpdateFileMRUMenu = false;
var _gNeedToUpdateProjectMRUMenu = false;
var _gNeedToUpdateTemplateMRUMenu = false;

this.updateMRUMenuIfNecessary = function uilayout_UpdateMRUMenuIfNecessary(mru)
{
    // (Re)build the identified MRU menu if necessary.
    //    "mru" is either "project" or "file", indicating which MRU menu
    //        to update.
    if (mru == "project" && _gNeedToUpdateProjectMRUMenu) {
        _updateMRUMenu("mruProjectList");
        _gNeedToUpdateProjectMRUMenu = false;
    } else if (mru == "file" && _gNeedToUpdateFileMRUMenu) {
        _updateMRUMenu("mruFileList");
        _gNeedToUpdateFileMRUMenu = false;
    } else if (mru == "template" && _gNeedToUpdateTemplateMRUMenu) {
        _updateMRUMenu("mruTemplateList");
        _gNeedToUpdateTemplateMRUMenu = false;
    }
}

var gUilayout_Observer = null;
function _Observer ()
{
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    observerSvc.addObserver(this, "mru_changed",false);
    observerSvc.addObserver(this, "view_opened",false);
    observerSvc.addObserver(this, "view_closed",false);
    observerSvc.addObserver(this, "current_view_changed",false);
    observerSvc.addObserver(this, "current_view_language_changed",false);
};
_Observer.prototype.destroy = function()
{
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    observerSvc.removeObserver(this, "mru_changed");
    observerSvc.removeObserver(this, "view_opened");
    observerSvc.removeObserver(this, "view_closed");
    observerSvc.removeObserver(this, "current_view_changed");
    observerSvc.removeObserver(this, "current_view_language_changed");
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
    case 'current_view_changed':
        if (!ko.views.manager.batchMode) {
            _updateCurrentLanguage(subject);
            ko.uilayout.updateTitlebar(subject);
        }
        // fall through
    case 'view_opened':
    case 'view_closed':
        _gNeedToUpdateWindowMenu = true;
        break;
    case 'current_view_language_changed':
        _log.info("GOT current_view_language_changed");
        _updateCurrentLanguage(subject);
        break;
    }
}

function _updateCurrentLanguage(view)
{
    if (! _viewAsMenuIsBuilt) {
        // If we haven't built the menu yet, don't bother.
        return;
    }
    if (! view || !view.document || !view.document.language) {
        // If we don't have a current language, don't bother either
        return;
    }
    _setCheckedLanguage(view.document.language);
}

function _setCheckedLanguage(language)
{
    _log.info("in _updateCurrentLanguage");
    var languageNameNospaces = language.replace(' ', '', 'g');
    var id1 = "menu_viewAs" + languageNameNospaces
    var id2 = "contextmenu_viewAs" + languageNameNospaces
    var i;
    var id;
    var child;
    var childnodes = document.getElementById('popup_viewAsLanguage').getElementsByTagName('menuitem');
    for (i = 0; i < childnodes.length; i++) {
        child = childnodes[i];
        id = child.getAttribute('id');
        if (id == id1) {
            child.setAttribute('checked', 'true');
        } else {
            child.setAttribute('checked', 'false');
        }
    }
    childnodes = document.getElementById('context-filetype-menu').getElementsByTagName('menuitem');
    for (i = 0; i < childnodes.length; i++) {
        child = childnodes[i];
        id = child.getAttribute('id');
        if (id == id2) {
            child.setAttribute('checked', 'true');
        } else {
            child.setAttribute('checked', 'false');
        }
    }
}

var _gNeedToUpdateWindowMenu = false;
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
        menuitem.setAttribute("label", (index + 1) + " " + view.title);
        if (index+1 <= 9) {
            menuitem.setAttribute("accesskey", index+1);
        }
        menuitem.setAttribute('type', 'checkbox');
        if (isCurrent) {
            menuitem.setAttribute('checked', 'true');
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
        if (!_gNeedToUpdateWindowMenu) return;
        _gNeedToUpdateWindowMenu = false;

        var separator = document.getElementById('window-menu-separator');
        var views = ko.views.manager.topView.getDocumentViews(true);
        // clear out checked items first
        var items = popup.getElementsByAttribute('data', 'fileItem');
        var i = 0;
        while (items.length > 0) {
            popup.removeChild(items[0]);
        }
        if (views.length == 0) {
            // re-enable this for first item
            separator.setAttribute('collapsed','true');
        } else {
            separator.removeAttribute('collapsed');
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

var _viewAsMenuIsBuilt = false;
this.updateViewAsMenuIfNecessary = function uilayout_UpdateViewAsMenuIfNecessary()
{
    if (_viewAsMenuIsBuilt) return;
    ko.uilayout.buildViewAsLanguageMenu();
    _viewAsMenuIsBuilt = true;
}

function _getHierarchy(hdata) {
    var langService = Components.classes["@activestate.com/koLanguageRegistryService;1"].
                getService(Components.interfaces.koILanguageRegistryService);
    var langHierarchy = langService.getLanguageHierarchy();
    var items = _buildMenuTree(hdata, langHierarchy, true);
    for (var i=0;i<items[0].length;i++)  {
        hdata.viewAsMenu.appendChild(items[0][i]);
        hdata.statusbarContextMenu.appendChild(items[1][i]);
    }
}


function _buildMenuTree(hdata, hierarchy, toplevel) {
    var menu, menu2;
    var menupopup, menupopup2;
    var viewAs_menuitems = new Array();
    var context_menuitems = new Array();
    var cmd, menuitem, menuitem2;
    var children = new Object();
    var count = new Object();
    var i, j;

    if (hierarchy.container == true)  {
        // build menu
        hierarchy.getChildren(children, count);
        children = children.value;

        for (i=0;i<children.length;i++)  {
            var a = _buildMenuTree(hdata, children[i], false);
            viewAs_menuitems.push(a[0]);
            context_menuitems.push(a[1]);
        }
        if (!toplevel)  {
            menu = document.createElementNS(XUL_NS, 'menu');
            menupopup = document.createElementNS(XUL_NS, 'menupopup');
            menu.setAttribute('label', hierarchy.name);
            menu2 = document.createElementNS(XUL_NS, 'menu');
            menupopup2 = document.createElementNS(XUL_NS, 'menupopup');
            menu2.setAttribute('label', hierarchy.name);

            for (j=0;j<viewAs_menuitems.length;j++)  {
                menupopup.appendChild(viewAs_menuitems[j]);
                menupopup2.appendChild(context_menuitems[j]);
            }
            menu.appendChild(menupopup);
            menu2.appendChild(menupopup2);
            return [menu, menu2];
        }
        return [viewAs_menuitems, context_menuitems];
    }
    else  {
        var languageNameNospaces = hierarchy.name.replace(' ', '', 'g')

        menuitem = document.createElementNS(XUL_NS, 'menuitem');
        menuitem.setAttribute("id", "menu_viewAs" + languageNameNospaces);
        menuitem.setAttribute('label', hierarchy.name);
        menuitem.setAttribute("accesskey", hierarchy.key);
        menuitem.setAttribute("type", "checkbox");
        menuitem.setAttribute("name", "current_language");
        menuitem.setAttribute("observes", "cmd_viewAs"+languageNameNospaces);

        menuitem2 = document.createElementNS(XUL_NS, 'menuitem');
        menuitem2.setAttribute("accesskey", hierarchy.key);
        menuitem2.setAttribute("label", hierarchy.name);
        menuitem2.setAttribute("type", "checkbox");
        menuitem2.setAttribute("name", "current_language");
        menuitem2.setAttribute("observes", "cmd_viewAs"+languageNameNospaces);
        menuitem2.setAttribute("name", "current_language_statusbar");
        menuitem2.setAttribute("id", "contextmenu_viewAs" + languageNameNospaces);

        if (hierarchy.name == hdata.language) {
            menuitem.setAttribute('checked', 'true');
            menuitem2.setAttribute('checked', 'true');
        }

        // create the commandset
        cmd = document.createElementNS(XUL_NS, 'command');
        cmd.setAttribute("id", "cmd_viewAs"+languageNameNospaces);
        if (hdata.language == null) {
            cmd.setAttribute("disabled", "true");
        }
        cmd.setAttribute("oncommand", "ko.views.manager.do_ViewAs('" + hierarchy.name + "');");
        hdata.commandset.appendChild(cmd);

        return [menuitem, menuitem2];
    }
}

// This updates the list in the View As ... menu.
// Called by uilayout_onload
this.buildViewAsLanguageMenu = function uilayout_buildViewAsLanguageMenu() {
    ko.trace.get().enter('ko.uilayout.buildViewAsLanguageMenu');
    // We may already have a language, let's find out:

    var hdata = {};
    var cmd, menuitem, menuitem2;
    hdata.commandset = document.getElementById("cmdset_viewAs");
    hdata.viewAsMenu = document.getElementById("popup_viewAsLanguage");
    hdata.statusbarContextMenu = document.getElementById('context-filetype-menu');
    hdata.language = null;
    if (ko.views.manager.currentView &&
        ko.views.manager.currentView.document &&
        ko.views.manager.currentView.document.language) {
        hdata.language = ko.views.manager.currentView.document.language;
    }
    try {
    _getHierarchy(hdata);
    } catch (e) {
        log.exception(e);
    }
    cmd = document.createElementNS(XUL_NS, 'command');
    cmd.setAttribute("id", "cmd_viewAsGuessedLanguage");
    cmd.setAttribute("disabled", "true");
    cmd.setAttribute("oncommand", "ko.views.manager.do_ViewAs('');");
    hdata.commandset.appendChild(cmd);
    menuitem = document.createElementNS(XUL_NS, 'menuseparator');
    hdata.viewAsMenu.appendChild(menuitem);
    menuitem2 = document.createElementNS(XUL_NS, 'menuseparator');
    hdata.statusbarContextMenu.appendChild(menuitem2);
    menuitem = document.createElementNS(XUL_NS, 'menuitem');
    menuitem.setAttribute("id", "menu_viewAsGuessedLanguage");
    menuitem.setAttribute("label", "Reset to best guess");
    menuitem.setAttribute("observes", "cmd_viewAsGuessedLanguage");
    hdata.viewAsMenu.appendChild(menuitem);
    menuitem2 = document.createElementNS(XUL_NS, 'menuitem');
    menuitem2.setAttribute("id", "menu_viewAsGuessedLanguage");
    menuitem2.setAttribute("label", "Reset to best guess");
    menuitem2.setAttribute("observes", "cmd_viewAsGuessedLanguage");
    hdata.statusbarContextMenu.appendChild(menuitem2);
    ko.trace.get().leave('ko.uilayout.buildViewAsLanguageMenu');
}


this.outputPaneShown = function uilayout_outputPaneShown()
{
    var splitter = window.document.getElementById("bottom_splitter");
    if (!splitter.hasAttribute('collapsed')) {
        return true;
    }
    var collapsed = splitter.getAttribute('collapsed') == 'true';
    return !collapsed;
}

this.leftPaneShown = function uilayout_leftPaneShown()
{
    var splitter = window.document.getElementById("workspace_left_splitter");
    if (!splitter.hasAttribute('collapsed')) {
        return true;
    }
    var collapsed = splitter.getAttribute('collapsed') == 'true';
    return !collapsed;
}

this.rightPaneShown = function uilayout_rightPaneShown()
{
    var splitter = window.document.getElementById("workspace_right_splitter");
    if (!splitter.hasAttribute('collapsed')) {
        return true;
    }
    var collapsed = splitter.getAttribute('collapsed') == 'true';
    return !collapsed;
}

this.isCodeBrowserTabShown = function uilayout_isCodeBrowserTabShown()
{
    var splitter = window.document.getElementById("workspace_left_splitter");
    if (splitter.hasAttribute("collapsed")
        && splitter.getAttribute("collapsed") == "true") {
        return false;
    }
    var tabs = window.document.getElementById("project_toolbox_tabs");
    var tab = window.document.getElementById("codebrowser_tab");
    if (tabs.selectedItem != tab) {
        return false;
    }
    return true;
}


this.ensureOutputPaneShown = function uilayout_ensureOutputPaneShown()
{
    if (!ko.uilayout.outputPaneShown()) {
        ko.uilayout.toggleSplitter('cmd_viewBottomPane');
    }
}


this.ensurePaneForTabHidden = function uilayout_ensurePaneForTabHidden(tabName)
{
    // given a tab id, collapse the pane that the tab is in.
    var tab = document.getElementById(tabName);
    var tabs = tab.parentNode;
    if (! tabs.hasAttribute('splitterId')) {
        log.error("Tab " + tabName + " isn't in a tabs element with a splitterId");
        return;
    }
    if (ko.uilayout.isPaneShown(tabs)) {
        var splitterId = tabs.getAttribute('splitterId');
        var splitterWidget = document.getElementById(splitterId);
        var splitterCmdId = splitterWidget.getAttribute('splitterCmdId');
        ko.uilayout.toggleSplitter(splitterCmdId);
    }
}


this.isPaneShown = function uilayout_isPaneShown(tabs) {
    var splitterId = tabs.getAttribute('splitterId');
    var splitterWidget = document.getElementById(splitterId);
    if (splitterWidget.hasAttribute('collapsed') &&
        splitterWidget.getAttribute('collapsed') == 'true') {
        return false;
    } else {
        return true;
    }
}

this.ensurePaneShown = function uilayout_ensurePaneShown(tabs) {
    var splitterId = tabs.getAttribute('splitterId');
    var splitterWidget = document.getElementById(splitterId);
    var splitterCmdId = splitterWidget.getAttribute('splitterCmdId');
    if (splitterWidget.hasAttribute('collapsed') &&
        splitterWidget.getAttribute('collapsed') == 'true') {
        ko.uilayout.toggleSplitter(splitterCmdId);
    }
}

this.ensureTabShown = function uilayout_ensureTabShown(tabId, focusToo) {
    try {
        if (typeof(focusToo) == 'undefined') focusToo = false;
        var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                        .getService(Components.interfaces.nsIWindowMediator);
        var mainWindow = wm.getMostRecentWindow('Komodo');
        var tab = mainWindow.document.getElementById(tabId);
        if (!tab) {
            log.error("ko.uilayout.ensureTabShown: couldn't find tab: " + tabId);
            return;
        }
        var tabs = tab.parentNode;
        // First make sure that the pane the tab is in is visible
        ko.uilayout.ensurePaneShown(tabs);
        tabs.selectedItem = tab;
        if (focusToo) {
            tab.focus();
        }
    } catch (e) {
        log.exception(e);
    }
}

/* Update the titlebar
   Have to keep in mind debugging state */
this.updateTitlebar = function uilayout_updateTitlebar(view)  {
    var title = "";
    if (view != null)  {
        title = view.title;
        if (view.isDirty)  {
            title = title.concat("*");
        } else  {
            title = title.replace(/\*$/, "");
            title = title.replace(/(\s)+$/, "");
        }
        if (view.document &&
            view.document.file &&
            view.getAttribute("type") != "startpage") {
            if (view.document.file.isLocal) {
                title = title + ' (' + view.document.file.dirName + ')';
            } else {
                title = view.document.displayPath;
            }
        }
    } else {
        title="";
    }

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
    ko.uilayout.saveTabSelections();
    gUilayout_Observer.destroy();
    gUilayout_Observer = null;
    _prefobserver.destroy();
    gPrefs.setBooleanPref("startupFullScreen", window.fullScreen)
    // nsIDOMChromeWindow STATE_MAXIMIZED = 1
    gPrefs.setBooleanPref("startupMaximized", window.windowState==1)
}

this.onload = function uilayout_onload()
{
    ko.trace.get().enter("ko.uilayout.onload");
    ko.uilayout.updateToolbarArrangement();
    addEventListener("fullscreen", ko.uilayout.onFullScreen, false);
    ko.uilayout.updateSplitterBroadcasterState('cmd_viewRightPane');
    ko.uilayout.updateSplitterBroadcasterState('cmd_viewLeftPane');
    ko.uilayout.updateSplitterBroadcasterState('cmd_viewBottomPane');
    _gNeedToUpdateFileMRUMenu = true;
    _gNeedToUpdateProjectMRUMenu = true;
    _gNeedToUpdateTemplateMRUMenu = true;
    gUilayout_Observer = new _Observer();
    _prefobserver = new _PrefObserver();
    _prefobserver.init();
    _updateAccesskeys();
    ko.main.addUnloadHandler(ko.uilayout.unload);
    ko.trace.get().leave("ko.uilayout.onload");
}

this.onloadDelayed = function uilayout_onloadDelayed()
{
    if (gPrefs.getBooleanPref("startupFullScreen")) {
        ko.uilayout.fullScreen();
    }
    else if (gPrefs.getBooleanPref("startupMaximized")) {
        window.maximize()
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

    var enable = ! gPrefs.getBooleanPref("keybindingDisableAccesskeys");

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

// A pref observer to watch if the user turns the access keys pref on or off.
function _PrefObserver() {};
_PrefObserver.prototype.observe = function(prefSet, prefSetID, prefName)
{
    _updateAccesskeys();
};

_PrefObserver.prototype.init = function() {
    gPrefs.prefObserverService.addObserver(this, "keybindingDisableAccesskeys", false);
}

_PrefObserver.prototype.destroy = function() {
    if (gPrefSvc && gPrefs) {
        gPrefs.prefObserverService.removeObserver(this, "keybindingDisableAccesskeys");
    }
}

this.saveTabSelections = function uilayout_SaveTabSelections() {
    try {
        var tabbox;
        var selectedTabId;
        tabbox = document.getElementById('leftTabBox');
        selectedTabId = tabbox.selectedTab.id;
        gPrefs.setStringPref('uilayout_leftTabBoxSelectedTabId', selectedTabId);
        tabbox = document.getElementById('rightTabBox');
        selectedTabId = tabbox.selectedTab.id;
        gPrefs.setStringPref('uilayout_rightTabBoxSelectedTabId', selectedTabId);
        tabbox = document.getElementById('output_area');
        selectedTabId = tabbox.selectedTab.id;
        gPrefs.setStringPref('uilayout_bottomTabBoxSelectedTabId', selectedTabId);
    } catch (e) {
        _log.exception("Couldn't save selected tab preferences");
    }
}

this.restoreTabSelections = function uilayout_RestoreTabSelections() {
    try {
        var selectedTabId;
        var tabbox;
        var tab;
        if (gPrefs.hasStringPref('uilayout_leftTabBoxSelectedTabId')) {
            selectedTabId = gPrefs.getStringPref('uilayout_leftTabBoxSelectedTabId');
            tabbox = document.getElementById('leftTabBox');
            tab = document.getElementById(selectedTabId);
            if (tab && !(tab.getAttribute('collapsed') == 'true')) {
                tabbox.selectedTab = tab;
            }
        }
        if (gPrefs.hasStringPref('uilayout_rightTabBoxSelectedTabId')) {
            selectedTabId = gPrefs.getStringPref('uilayout_rightTabBoxSelectedTabId');
            tabbox = document.getElementById('rightTabBox');
            tab = document.getElementById(selectedTabId);
            if (tab && !(tab.getAttribute('collapsed') == 'true')) {
                tabbox.selectedTab = tab;
            }
        }
        if (gPrefs.hasStringPref('uilayout_bottomTabBoxSelectedTabId')) {
            selectedTabId = gPrefs.getStringPref('uilayout_bottomTabBoxSelectedTabId');
            tabbox = document.getElementById('output_area');
            tab = document.getElementById(selectedTabId);
            if (tab && !(tab.getAttribute('collapsed') == 'true')) {
                tabbox.selectedTab = tab;
            }
        }
    } catch (e) {
        _log.exception("Couldn't restore selected tab");
    }
}

}).apply(ko.uilayout);

// backwards compatibility api
var uilayout_toggleToolbarVisibility = ko.uilayout.toggleToolbarVisibility;
var uilayout_toggleButtons = ko.uilayout.toggleButtons;
var uilayout_updateToolbarArrangement = ko.uilayout.updateToolbarArrangement;
var uilayout_populatePreviewToolbarButton = ko.uilayout.populatePreviewToolbarButton;
var uilayout_focusPane = ko.uilayout.focusPane;
var uilayout_toggleTab = ko.uilayout.toggleTab;
var uilayout_updateTabpickerMenu = ko.uilayout.updateTabpickerMenu;
var uilayout_togglePane = ko.uilayout.togglePane;
var uilayout_toggleSplitter = ko.uilayout.toggleSplitter;
var uilayout_updateSplitterBroadcasterState = ko.uilayout.updateSplitterBroadcasterState;
var uilayout_updateFullScreen = ko.uilayout.updateFullScreen;
var uilayout_FullScreen = ko.uilayout.fullScreen;
var uilayout_onFullScreen = ko.uilayout.onFullScreen;
var uilayout_newFileFromTemplateOrTrimMRU = ko.uilayout.newFileFromTemplateOrTrimMRU;
var uilayout_UpdateMRUMenuIfNecessary = ko.uilayout.updateMRUMenuIfNecessary;
var uilayout_updateWindowList = ko.uilayout.updateWindowList;
var uilayout_UpdateViewAsMenuIfNecessary = ko.uilayout.updateViewAsMenuIfNecessary;
var uilayout_buildViewAsLanguageMenu = ko.uilayout.buildViewAsLanguageMenu;
var uilayout_outputPaneShown = ko.uilayout.outputPaneShown;
var uilayout_leftPaneShown = ko.uilayout.leftPaneShown;
var uilayout_rightPaneShown = ko.uilayout.rightPaneShown;
var uilayout_isCodeBrowserTabShown = ko.uilayout.isCodeBrowserTabShown;
var uilayout_ensureOutputPaneShown = ko.uilayout.ensureOutputPaneShown;
var uilayout_ensurePaneForTabHidden = ko.uilayout.ensurePaneForTabHidden;
var uilayout_isPaneShown = ko.uilayout.isPaneShown;
var uilayout_findMainWindow = ko.windowManager.getMainWindow;
var uilayout_ensurePaneShown = ko.uilayout.ensurePaneShown;
var uilayout_ensureTabShown = ko.uilayout.ensureTabShown;
var uilayout_updateTitlebar = ko.uilayout.updateTitlebar;
var uilayout_unload = ko.uilayout.unload;
var uilayout_onload = ko.uilayout.onload;
var uilayout_onloadDelayed = ko.uilayout.onloadDelayed;
var uilayout_SaveTabSelections = ko.uilayout.saveTabSelections;
var uilayout_RestoreTabSelections = ko.uilayout.restoreTabSelections;
