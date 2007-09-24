/* Copyright (c) 2003-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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


//---- globals

var _findtoolbarlog;
var gFindTextboxContext;
var gFindFilesTextboxContext;
var gFindToolbar_FindInFiles_Textbox;
var _gOsPath = Components.classes["@activestate.com/koOsPath;1"].getService();
var _gOsPathsep = Components.classes["@activestate.com/koOs;1"].getService().pathsep;


//---- routines

function findtoolbar_onload()
{
    try {
        _findtoolbarlog = ko.logging.getLogger('findtoolbar');
        //_findtoolbarlog.setLevel(ko.logging.LOG_DEBUG);
        gFindTextboxContext = Components.classes["@activestate.com/koFindContext;1"]
                    .createInstance(Components.interfaces.koIFindContext);
        gFindTextboxContext.type = Components.interfaces.koIFindContext.FCT_CURRENT_DOC;

        gFindFilesTextboxContext = Components.classes[
            "@activestate.com/koFindInFilesContext;1"]
            .createInstance(Components.interfaces.koIFindInFilesContext);
        gFindFilesTextboxContext.type = Components.interfaces.koIFindContext.FCT_IN_FILES;
        gFindFilesTextboxContext.cwd = window.gFindInFilesCwd;

        gFindToolbar_FindInFiles_Textbox = document.getElementById('textbox_findInFiles');
    } catch (e) {
        log.exception(e); // not findtoolbar in case that's what failed.
    }
}


function Findtoolbar_OpenTextboxKeyPress(field, event) {
    try {
        switch (event.keyCode) {
            case event.DOM_VK_RETURN:
                var path = field.value;
                if (!path) return;

                // Normalize and make the path absolute.
                var abspath = null;
                if (path.indexOf("~") == 0) {
                    abspath = _gOsPath.expanduser(path);
                } else if (!_gOsPath.isabs(path)) {
                    var cwd = ko.window.getCwd();
                    abspath = _gOsPath.join(cwd, path);
                } else {
                    abspath = path;
                }
                abspath = _gOsPath.normpath(abspath);

                // Ctrl+Enter (however Mozilla calls that by platform) opens a
                // filepicker.
                //XXX Does this need to revert the event.ctrlKey on non-MacOSX?
                //    Control+Return on MacOSX results in a literal "Ctrl+M".
                if (event.metaKey) {
                    var dirname, filename;
                    if (_gOsPath.isdir(abspath)) {
                        dirname = abspath;
                        filename = null;
                    } else {
                        dirname = null;
                        filename = abspath;
                    }
                    var paths = ko.filepicker.openFiles(dirname, filename);
                    if (paths) {
                        ko.open.multipleURIs(paths, 'editor');
                    }
                } else {
                    if (_gOsPath.isdir(abspath)) {
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

function Findtoolbar_FindTextboxKeyPress(field, event) {
    try {
        if (event.type != 'keypress') {
            return;
        }
        if (String.fromCharCode(event.charCode) == 'a') {
            if (event.altKey && ! event.shiftKey && ! event.ctrlKey) {
                Find_FindAll(window, gFindTextboxContext, field.value);
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
                ko.mru.addFromACTextbox(field);
                // Ctrl+Enter (however Mozilla calls that by platform) opens
                // this search in the find dialog.
                //XXX Does this need to revert the event.ctrlKey on non-MacOSX?
                //    Control+Return on MacOSX results in a literal "Ctrl+M".
                if (event.metaKey) {
                    ko.launch.find(field.value);
                } else {
                    ko.mru.addFromACTextbox(field);
                    if (event.shiftKey) {
                        findSvc.options.searchBackward = !findSvc.options.searchBackward;
                        Find_FindNext(window, gFindTextboxContext, field.value,
                                      "find", false, false);
                        findSvc.options.searchBackward = !findSvc.options.searchBackward;
                    } else {
                        Find_FindNext(window, gFindTextboxContext, field.value,
                                      "find", false, false);
                    }
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


function Findtoolbar_FindFilesOnFocus(field, event) {
    try {
        document.getElementById('findButton').setAttribute('class', 'findInFiles');
        field.setSelectionRange(0, field.value.length);
        if (event.target.nodeName == 'html:input') { 
          var textbox = field.parentNode.parentNode.parentNode;
          textbox.searchParam = stringutils_updateSubAttr(
              textbox.searchParam, 'cwd', ko.window.getCwd());
        }
    } catch (e) {
        log.exception(e);
    }
}

function Findtoolbar_FindFilesKeyPress(field, event) {
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
                    gFindFilesTextboxContext.cwd = ko.window.getCwd();
                    Find_FindAllInFiles(window,
                                        gFindFilesTextboxContext,
                                        findTerm,
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

function Findtoolbar_GotoOpenTextbox() {
    document.getElementById('textbox_open').focus();
}


function Findtoolbar_GotoFindTextbox() {
    document.getElementById('textbox_find').focus();
}


function Findtoolbar_AddBrowsedDirectory() {
    _findtoolbarlog.debug("Findtoolbar_AddBrowsedDirectory()");
    try {
        var doReplace = false; // are we replacing the entire field or inserting into it.
        var curDir;
        var os = Components.classes["@activestate.com/koOs;1"].getService();
        var textbox = gFindToolbar_FindInFiles_Textbox;
        var encodedFolders = textbox.value;
        if (textbox.selectionStart == 0 &&
            textbox.selectionEnd == encodedFolders.length) {
            doReplace = true;
            curDir = _gOsPath.realpath(encodedFolders.split(_gOsPathsep)[0]);
        } else {
            if (textbox.selectionStart == textbox.selectionEnd) {
                curDir = _gOsPath.realpath(encodedFolders.split(_gOsPathsep)[0]);
            } else {
                curDir = _gOsPath.realpath(encodedFolders.slice(textbox.selectionStart,
                                                                   textbox.selectionEnd).split(_gOsPathsep)[0]);
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
                var newFolder = _gOsPathsep + newDir;
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
