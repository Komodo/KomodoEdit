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

if (typeof(ko) == 'undefined') {
    var ko = {};
}

if (typeof(ko.findtoolbar)!='undefined') {
    ko.logging.getLogger('').warn("ko.findtoolbar was already loaded, re-creating it.\n");
}

/* Support for the Open/Find toolbar
 *  - this toolbar is (for now) showable or not as a whole.  There
 *    is no way to show only the Open or only the Find items.
 *  - Hitting escape in any text field focuses back on the current
 *    editor if there is one.
 *  - There is autocompletion in the Open text field based on the
 *    current working directory for the current file.
 *  - the Find text fields have preference-backed MRUs.
 *  - The find capabilities share 'sessions'
 */
ko.findtoolbar = {};

(function() {

//---- locals

var _findtoolbarlog;
var _findInDocumentContext;
var _findInFilesContext;
var _findInFilesTextbox;
var _osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService();
var _osPathSep = Components.classes["@activestate.com/koOs;1"].getService().pathsep;


//---- routines

this.openTextboxKeyPress = function Findtoolbar_OpenTextboxKeyPress(field, event) {
    try {
        switch (event.keyCode) {
            case event.DOM_VK_RETURN:
                var path = field.value;
                if (!path) return;

                // Normalize and make the path absolute.
                var abspath = null;
                if (path.indexOf("~") == 0) {
                    abspath = _osPathSvc.expanduser(path);
                } else if (!_osPathSvc.isabs(path)) {
                    var cwd = ko.window.getCwd();
                    abspath = _osPathSvc.join(cwd, path);
                } else {
                    abspath = path;
                }
                abspath = _osPathSvc.normpath(abspath);

                // Ctrl+Enter (however Mozilla calls that by platform) opens a
                // filepicker.
                //XXX Does this need to revert the event.ctrlKey on non-MacOSX?
                //    Control+Return on MacOSX results in a literal "Ctrl+M".
                if (event.metaKey) {
                    var dirname, filename;
                    if (_osPathSvc.isdir(abspath)) {
                        dirname = abspath;
                        filename = null;
                    } else {
                        dirname = null;
                        filename = abspath;
                    }
                    var paths = ko.filepicker.browseForFiles(dirname, filename);
                    if (paths) {
                        ko.open.multipleURIs(paths, 'editor');
                    }
                } else {
                    if (_osPathSvc.isdir(abspath)) {
                        if (ko.views.manager.notify_visited_directory(abspath)){
                            return;
                        }
                        // Don't do anything w/ directories, just get ready to
                        // continue.
                        field.setSelectionRange(field.textLength,
                                                field.textLength);
                        return;
                    } else { // It is a filename
                        // It may be a glob -- if yes, then expand it.
                        if (abspath.indexOf('*') != -1 ||
                            abspath.indexOf('?') != -1) {
                            var glob = Components.classes["@activestate.com/koGlob;1"].
                                   getService(Components.interfaces.koIGlob);
                            var paths = new Object();
                            paths = glob.glob(abspath, new Object())
                            for (var i = 0; i < paths.length; i++) {
                                ko.open.URI(paths[i]);
                            }
                        } else {
                            ko.open.URI(abspath);
                        }
                    }
                }
                field.value = '';
                event.stopPropagation();
                event.preventDefault();
                event.cancelBubble = true;
                break;
            case event.DOM_VK_ESCAPE:
                field.value = '';
                ko.views.manager.currentView.setFocus();
                event.stopPropagation();
                break;
        }
    } catch (e) {
        log.exception(e);
    }
}

this.findTextboxKeyPress = function Findtoolbar_FindTextboxKeyPress(field, event) {
    try {
        if (event.type != 'keypress') {
            return;
        }
        if (String.fromCharCode(event.charCode) == 'a') {
            if (event.altKey && ! event.shiftKey && ! event.ctrlKey) {
                ko.find.findAll(window, _findInDocumentContext, field.value);
                event.stopPropagation();
                event.preventDefault();
                return;
            }
        }
        switch (event.keyCode) {
            case event.DOM_VK_RETURN:
                if (! field.value || ko.views.manager.currentView.getAttribute('type') != 'editor') {
                    return;
                }
                
                if (_findInFilesTextbox.value != '') {
                    this.findFilesKeyPress(_findInFilesTextbox, event);
                    return;
                }
                
                ko.mru.addFromACTextbox(field);
                // Ctrl+Enter (however Mozilla calls that by platform) opens
                // this search in the find dialog.
                //XXX Does this need to revert the event.ctrlKey on non-MacOSX?
                //    Control+Return on MacOSX results in a literal "Ctrl+M".
                if (event.metaKey) {
                    ko.launch.find(field.value);
                } else {
                    ko.mru.addFromACTextbox(field);
                    var findSvc = Components.classes["@activestate.com/koFindService;1"].
                           getService(Components.interfaces.koIFindService);
                    if (event.shiftKey) {
                        findSvc.options.searchBackward = true;
                    } else {
                        findSvc.options.searchBackward = false;
                    }
                    ko.find.findNext(window, _findInDocumentContext, field.value,
                                  "find", false, false);
                }
                event.stopPropagation();
                break;
            case event.DOM_VK_ESCAPE:
                ko.views.manager.currentView.setFocus();
                event.stopPropagation();
                break;
        }
    } catch (e) {
        log.exception(e);
    }
}


this.findFilesOnFocus = function Findtoolbar_FindFilesOnFocus(field, event) {
    try {
        field.setSelectionRange(0, field.value.length);
        if (event.target.nodeName == 'html:input') { 
          var textbox = field.parentNode.parentNode.parentNode;
          textbox.searchParam = ko.stringutils.updateSubAttr(
              textbox.searchParam, 'cwd', ko.window.getCwd());
        }
    } catch (e) {
        log.exception(e);
    }
}

this.findFilesKeyPress = function Findtoolbar_FindFilesKeyPress(field, event) {
    try {
        if (event.type != 'keypress') return;
        switch (event.keyCode) {
            case event.DOM_VK_RETURN:
                var findTerm = document.getElementById('textbox_find').value;
                if (!findTerm) return;
                if (!field.value) return;
                var findSvc = Components.classes["@activestate.com/koFindService;1"].
                       getService(Components.interfaces.koIFindService);
                var value = field.value;
                var view = ko.views.manager.currentView;
                var quantifierFound = ((value.indexOf('*') != -1) ||
                                       value.indexOf('?') != -1);
                var lastSlash = Math.max(value.lastIndexOf('/'),
                                         value.lastIndexOf('\\')) + 1;
                // Split out the expression into a directory and a
                // file pattern.
                if (lastSlash == -1) {
                    lastSlash = value.length;
                }
                // We want to map the following:
                // value               dirname    filetypes
                // 'foo/bar'           'foo/bar'  ''
                // 'foo/*.py'          'foo'      '*.py'
                // '../foo/bar/*.py'   '../foo'   '*.py'
                // 'foo'               'foo'      ''
                // '*.py'              ''         '*.py'
                var filetypes, dirname;
                if (quantifierFound) {
                    filetypes = value.slice(lastSlash);
                    if (lastSlash == 0) {
                        dirname = '';
                    } else {
                        dirname = value.slice(0, lastSlash-1);
                    }
                } else {
                    filetypes = '';
                    dirname = value;
                }
                findSvc.options.encodedIncludeFiletypes = filetypes;
                findSvc.options.encodedFolders = dirname;
                if (event.ctrlKey) {
                    ko.launch.findInFiles(findTerm, dirname, filetypes);
                } else {
                    ko.mru.addFromACTextbox(document.getElementById('textbox_find'));
                    ko.mru.addFromACTextbox(field);
                    _findInFilesContext.cwd = ko.window.getCwd();
                    ko.find.findAllInFiles(window,
                                        _findInFilesContext,
                                        findTerm);
                }
                event.stopPropagation();
                break;
            case event.DOM_VK_ESCAPE:
                ko.views.manager.currentView.setFocus();
                event.stopPropagation();
                break;
        }
    } catch (e) {
        log.exception(e);
    }
}

this.gotoOpenTextbox = function Findtoolbar_GotoOpenTextbox() {
    document.getElementById('textbox_open').focus();
}


this.gotoFindTextbox = function Findtoolbar_GotoFindTextbox() {
    document.getElementById('textbox_find').focus();
}


this.addBrowsedDirectory = function Findtoolbar_AddBrowsedDirectory() {
    _findtoolbarlog.debug("ko.findtoolbar.addBrowsedDirectory()");
    try {
        var doReplace = false; // are we replacing the entire field or inserting into it.
        var curDir;
        var os = Components.classes["@activestate.com/koOs;1"].getService();
        var textbox = _findInFilesTextbox;
        var encodedFolders = textbox.value;
        if (textbox.selectionStart == 0 &&
            textbox.selectionEnd == encodedFolders.length) {
            doReplace = true;
            curDir = _osPathSvc.realpath(encodedFolders.split(_osPathSep)[0]);
        } else {
            if (textbox.selectionStart == textbox.selectionEnd) {
                curDir = _osPathSvc.realpath(encodedFolders.split(_osPathSep)[0]);
            } else {
                curDir = _osPathSvc.realpath(encodedFolders.slice(textbox.selectionStart,
                                                                   textbox.selectionEnd).split(_osPathSep)[0]);
            }
        }
        var newDir = ko.filepicker.getFolder(curDir,
                                          "Choose a folder to add to the search list:");
        if (newDir) {
            if (doReplace) {
                textbox.value = newDir;
            } else {
                var oldValue = textbox.value;
                var selStart = textbox.selectionStart;
                var selEnd = textbox.selectionEnd;
                var newFolder = _osPathSep + newDir;
                var newValue = oldValue.slice(0, selStart) + newFolder
                               + oldValue.slice(selEnd, oldValue.length);
                textbox.value = newValue
                textbox.setSelectionRange(selStart, selStart+newFolder.length);
            }
        }
    } catch(ex) {
        _findtoolbarlog.exception(ex);
    }
}

this.initialize = function findtoolbar_onload()
{
    try {
        _findtoolbarlog = ko.logging.getLogger('findtoolbar');
        //_findtoolbarlog.setLevel(ko.logging.LOG_DEBUG);
        _findInDocumentContext = Components.classes["@activestate.com/koFindContext;1"]
                    .createInstance(Components.interfaces.koIFindContext);
        _findInDocumentContext.type = Components.interfaces.koIFindContext.FCT_CURRENT_DOC;

        _findInFilesContext = Components.classes[
            "@activestate.com/koFindInFilesContext;1"]
            .createInstance(Components.interfaces.koIFindInFilesContext);
        _findInFilesContext.type = Components.interfaces.koIFindContext.FCT_IN_FILES;
        _findInFilesContext.cwd = null;

        _findInFilesTextbox = document.getElementById('textbox_findInFiles');
    } catch (e) {
        log.exception(e); // not findtoolbar in case that's what failed.
    }
}

}).apply(ko.findtoolbar);

window.addEventListener("load", ko.findtoolbar.initialize, false);
