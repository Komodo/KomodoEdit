/*
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Initial Developer of the Original Code is
# Davide Ficano.
# Portions created by the Initial Developer are Copyright (C) 2007
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Davide Ficano <davide.ficano@gmail.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
*/
xtk.include("domutils");

var moreKomodo = {

    onLoad : function() {
        var obs = MoreKomodoCommon.getObserverService();
        obs.addObserver(this, "morekomodo_command", false);
        window.controllers.appendController(this);
        if (!('moreKomodo' in ko)) {
            ko.moreKomodo = {};
        }
        if (!('MoreKomodoCommon' in ko.moreKomodo)) {
            ko.moreKomodo.MoreKomodoCommon = MoreKomodoCommon;
        }
        if (!('moreKomodo' in ko.moreKomodo)) {
            ko.moreKomodo.moreKomodo = moreKomodo;
        }

        let tabContextMenu = document.getElementById("tabContextMenu");
        tabContextMenu.addEventListener("popupshowing",
                                        event => this.goUpdateFileMenuItems(event));
        tabContextMenu.addEventListener("popuphiding",
                                        event => this.onPopupHiding(event));
    },

    onUnLoad : function() {
        var obs = MoreKomodoCommon.getObserverService();
        obs.removeObserver(this, "morekomodo_command");
        window.controllers.removeController(this);
    },

    observe : function(subject, topic, data) {
        try {
        switch (topic) {
            case "morekomodo_command":
                this._updateViewsByCommand(subject.wrappedJSObject);
                break;
        }
        } catch (err) {
            alert(topic + "--" + data + "\n" + err);
        }
    },

    _updateViewsByCommand : function(commandInfo) {
        switch (commandInfo.command) {
            case "rename":
            case "move":
                // handle splitted view
                var list = ko.views.manager.topView.findViewsForDocument(commandInfo.document);
                for (var i in list) {
                    var view = list[i];
                    if (view.getAttribute("type") == "editor") {
                        var locationInfo = {};
                        view.saveLocation(locationInfo);
                        view.koDoc = commandInfo.newDocument;
                        this.updateView(view);
                        view.restoreLocation(locationInfo);

                        // /opt/devel/mozilla/komodo/openkomodo/src/chrome/komodo/content/bindings/views-browser.xml
                        // /opt/devel/mozilla/komodo/openkomodo/src/chrome/komodo/content/bindings/views-editor.p.xml
                        if (view.preview) {
                            view.preview.open(view.koDoc.file.URI, false);
                        }
                        // ensure colourise is applied
                        ko.commands.doCommand('cmd_viewAsGuessedLanguage');
                    }
                }

                // update the mru list
                var uriView = commandInfo.document.file.URI;
                var index = MoreKomodoCommon.getMruUriIndex("mruFileList", uriView);
                if (index >= 0) {
                    ko.mru.del("mruFileList", index);
                    ko.mru.addURL("mruFileList", commandInfo.newDocument.file.URI);
                }
                ko.views.manager.currentView.setFocus();
                break;
            case "delete":
                var list = ko.views.manager.topView.findViewsForDocument(commandInfo.document);
                var uriView = commandInfo.document.file.URI;
                for (var i in list) {
                    list[i].closeUnconditionally();
                }

                // update the mru list
                var index = MoreKomodoCommon.getMruUriIndex("mruFileList", uriView);
                if (index >= 0) {
                    ko.mru.del("mruFileList", index);
                }
                break;
        }
    },
    
    onRenameFile : function() {
        var currView = this._getView();
        var viewDoc = currView.koDoc;
        if (!MoreKomodoCommon.dirtyDocCheck(viewDoc)) {
            return;
        }
        var title = MoreKomodoCommon.getLocalizedMessage("rename.title");
        var oldName = viewDoc.file.baseName;
        var extPos = oldName.lastIndexOf('.');
        if (extPos < 0) {
            extPos = oldName.length;
        }
        var newName = ko.dialogs.prompt(oldName, null, oldName, title,
                                    null, //  mruName,
                                    null, //  validator,
                                    null, //  multiline,
                                    null, //  screenX,
                                    null, //  screenY,
                                    null, //  tacType,
                                    null, //  tacParam,
                                    null, //  tacShowCommentColumn,
                                    0, //  selectionStart,
                                    extPos //  selectionEnd
                                    );

        try {
            if (newName && newName != oldName) {
                var newPath = MoreKomodoCommon.renameFile(viewDoc.displayPath, newName);
                if (newPath) {
                    // Reopen file at same tab position
                    var newDoc = MoreKomodoCommon.createDocumentFromURI(newPath);
                    // the observer will set the new document also for this view
                    var data = {document : viewDoc,
                                newDocument : newDoc,
                                command : "rename"
                                };
                    data.wrappedJSObject = data;

                    var obs = MoreKomodoCommon.getObserverService();
                    obs.notifyObservers(data, "morekomodo_command", null);
                }
            }
        } catch (err) {
            alert("Error while renaming " + err);
        }
    },

    onDeleteFile : function() {
        try {
            var view = this._getView();
            var file = view.koDoc.file;
            var msg = MoreKomodoCommon.getLocalizedMessage("confirm.delete.file");

            if (ko.dialogs.yesNo(msg, "No", file.displayPath) == "Yes") {
                MoreKomodoCommon.deleteFile(file.displayPath);
                // the observer will close also calling view
                var data = {document : view.koDoc,
                            command : "delete"
                            };
                data.wrappedJSObject = data;

                var obs = MoreKomodoCommon.getObserverService();
                obs.notifyObservers(data, "morekomodo_command", null);
            }
        } catch (err) {
            alert(err);
        }
    },

    onMakeBackup : function() {
        try {
            var view = this._getView();
            var file = view.koDoc.file;
            var currentPath = MoreKomodoCommon.makeLocalFile(file.path);
            var msg = MoreKomodoCommon.getLocalizedMessage("select.backup.file.title");
            var fp = MoreKomodoCommon.makeFilePicker(window,
                        msg,
                        Components.interfaces.nsIFilePicker.modeSave,
                        currentPath.parent);
            fp.defaultString = currentPath.leafName;
            var res = fp.show();
            var isOk = (res == Components.interfaces.nsIFilePicker.returnOK
                        || res == Components.interfaces.nsIFilePicker.returnReplace);
            if (isOk && fp.file) {
                MoreKomodoCommon.backupFile(currentPath, fp.file);
            }
            view.setFocus();
        } catch (err) {
            alert("Unable to make backup: " + err);
        }
    },

    onCopyFullPath : function() {
        var view = this._getView();
        var file = view.koDoc.displayPath;

        MoreKomodoCommon.copyToClipboard(file);
        view.setFocus();
    },

    onCopyDirectoryPath : function() {
        var view = this._getView();
        var file = view.koDoc.file;
        var dirName = file.dirName;

        if (file.isRemoteFile) {
            dirName = file.scheme + "://" + file.server + dirName;
        }

        MoreKomodoCommon.copyToClipboard(dirName);
        view.setFocus();
    },

    onCopyFileName : function() {
        var view = this._getView();
        var file = view.koDoc.baseName;

        MoreKomodoCommon.copyToClipboard(file);
        view.setFocus();
    },

    openFavorites : function() {
        window.openDialog("chrome://morekomodo/content/favorites/favorites.xul",
                          "_blank",
                          "chrome,modal,resizable=yes,dependent=yes");
    },

    onOpenSortDialog : function() {
        var param = {isOk : false};

        var view = this._getView();
        var scimoz = view.scintilla.scimoz;
        param.sortOptions = new SortOptions();
        param.sortOptions.sortOnlySelection
            = scimoz.selectionStart != scimoz.selectionEnd;
        window.openDialog("chrome://morekomodo/content/sortDialog.xul",
                          "_blank",
                          "chrome,modal,resizable=no,dependent=yes",
                          param);
        if (param.isOk) {
            sortView(view, param.sortOptions);
        }
    },

    initPopupMenuFavorites : function(showAll) {
        var menu = document.getElementById("favorites-toolbarMenuPopup");

        MoreKomodoCommon.removeMenuItems(menu);
        var prefs = new MoreKomodoPrefs();
        var items = prefs.readFavorites();
        if (items.length > 0) {
            var maxItems = prefs.readMaxFavoriteMenuItems();
            if (maxItems <= 0) {
                maxItems = items.length;
            }

            if (typeof(showAll) == "undefined") {
                showAll = false;
            }

            var itemCount;
            var showExpandItem;

            if (showAll) {
                itemCount = items.length;
                showExpandItem = false;
            } else {
                itemCount = Math.min(maxItems, items.length);
                showExpandItem = true;
            }
            for (var i = 0; i < itemCount; i++) {
                var favoriteInfo = items[i];
                if (favoriteInfo.isValid()) {
                    this.appendFavoriteItem(menu, favoriteInfo);
                }
            }
            // No need to append menu when items are less than maxItems
            if (items.length <= maxItems) {
                showExpandItem = false;
            }
            if (showExpandItem) {
                this.appendExpandFavoriteItem(menu);
            }
        } else {
            this.appendEmptyFavoriteItem(menu);
        }
    },

    goUpdateFileMenuItems : function(event) {
        if (!event.originalTarget ||
             event.originalTarget.id != "tabContextMenu")
        {
            // Some other menu is popping open; ignore
            return;
        }
        this._view = null;
        let tab = document.popupNode;
        if (tab && tab.linkedPanel) {
            let panel = document.getElementById(tab.linkedPanel);
            if (panel && panel.firstChild) {
                this._view = panel.firstChild;
            }
        }
        goUpdateCommand("cmd_morekomodo_makeBackup");
        goUpdateCommand("cmd_morekomodo_rename");
        goUpdateCommand("cmd_morekomodo_delete");
        goUpdateCommand("cmd_morekomodo_copyFullPath");
        goUpdateCommand("cmd_morekomodo_copyFileName");
        goUpdateCommand("cmd_morekomodo_copyDirectoryPath");
        goUpdateCommand("cmd_morekomodo_move");
    },

    onPopupHiding: function(event) {
        if (!event.originalTarget ||
             event.originalTarget.id != "tabContextMenu")
        {
            // Some other menu is hiding; ignore
            return;
        }
        this._view = null;
    },

    supportsCommand : function(cmd) {
        switch (cmd) {
            case "cmd_morekomodo_makeBackup":
            case "cmd_morekomodo_rename":
            case "cmd_morekomodo_delete":
            case "cmd_morekomodo_copyFullPath":
            case "cmd_morekomodo_copyFileName":
            case "cmd_morekomodo_copyDirectoryPath":
            case "cmd_morekomodo_move":
                return true;
        }
        return false;
    },

    _getView: function() {
        if (this._view) {
            return this._view;
        }
        if (ko.views.manager) {
            return ko.views.manager.currentView;
        }
        return null;
    },

    isCommandEnabled : function(cmd) {
        // at startup with no file open manager is null
        var view = this._getView();

        switch (cmd) {
            case "cmd_morekomodo_rename":
            case "cmd_morekomodo_delete":
            case "cmd_morekomodo_copyFullPath":
            case "cmd_morekomodo_copyFileName":
            case "cmd_morekomodo_copyDirectoryPath":
                if (view && view.koDoc) {
                    return !(view.koDoc.isUntitled
                            || view.getAttribute("type") != "editor");
                }
                return false;
            case "cmd_morekomodo_move":
            case "cmd_morekomodo_makeBackup":
                // These commands aren't supported on remote
                if (view && view.koDoc) {
                    return !(view.koDoc.isUntitled
                            || view.getAttribute("type") != "editor"
                            || view.koDoc.file.isRemoteFile);
                }
                return false;
        }
        return false;
    },

    doCommand : function(cmd) {
        switch (cmd) {
            case "cmd_morekomodo_rename":
                this.onRenameFile();
                break;
            case "cmd_morekomodo_delete":
                this.onDeleteFile();
                break;
            case "cmd_morekomodo_copyFullPath":
                this.onCopyFullPath();
                break;
            case "cmd_morekomodo_copyFileName":
                this.onCopyFileName();
                break;
            case "cmd_morekomodo_copyDirectoryPath":
                this.onCopyDirectoryPath();
                break;
            case "cmd_morekomodo_move":
                this.onMoveFile();
                break;
            case "cmd_morekomodo_makeBackup":
                this.onMakeBackup();
                break;
        }
    },

    onEvent : function(evt) {
    },

    onMoveFile : function() {
        try {
            var viewDoc = this._getView().koDoc;
            var file = viewDoc.file;
            MoreKomodoCommon.moveFile(file.path);
        } catch (err) {
            alert("Unable to move file: " + err);
        }
    },

    // update title and other stuff
    updateView : function(view) {
        xtk.domutils.fireEvent(view, 'current_view_changed');
    }

};

window.addEventListener("load", function(event) { moreKomodo.onLoad(event); }, false);
window.addEventListener("unload", function(event) { moreKomodo.onUnLoad(event); }, false);
