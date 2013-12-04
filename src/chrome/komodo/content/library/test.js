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

/*
 * Interface to the unit-test system
 */

function test_startUIUnitTests()
{
    var _TestSvc = Components.classes["@activestate.com/koTestSvc;1"].getService();
    _TestSvc.runAllTests();
}

function test_editGlobalPrefs()
{
    var obj = new Object();
    obj.prefs = gPrefs;
    obj.title = 'Global Preferences';
    window.openDialog('chrome://komodo/content/library/prefs_control.xul',
                    obj.title,
                    'titlebar,chrome,resizable,close,dialog',
                    obj);
}

function test_editCurrentViewPrefs()
{
    if (! gViewMgr.currentView) {
        alert('no current view');
    } else {
        var obj = new Object();
        obj.prefs = gViewMgr.currentView.prefs;
        obj.title = 'View Preferences for: ' + gViewMgr.currentView.koDoc.file.leafName;
        window.openDialog('chrome://komodo/content/library/prefs_control.xul',
                        obj.title,
                        'titlebar,chrome,resizable,close,dialog',
                        obj);
    }
}

function test_dialog_prompt()
{
    dump("\n-------------------\nQuery String Dialog with 'prompt': using multiline\n");
    var result = ko.dialogs.prompt("this is my prompt",
                                   null, null, null, null, null,
                                   true, // multiline
                                   30, 500);  // screenX,screenY
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nQuery String Dialog using all options (except validator):\n");
    result = ko.dialogs.prompt(
        "this is my prompt, the first line of which is a very very very "
            +"very very very long line of text\nthis is line2 of the "
            +"prompt\n",
        "a label",
        "a default value",
        "this is my title",
        "test_dialog_prompt_mru");
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nQuery String Dialog using validator:\n");
    result = ko.dialogs.prompt(
        null, // prompt
        "Enter a number:", // label
        "0",  // default value
        "Ask for a Number", // title
        null, // mru prefix
        _test_validate_isNumber); // validator
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nQuery String Dialog using crashing validator:\n");
    result = ko.dialogs.prompt(
        null, // prompt
        "Enter a number:", // label
        "0",  // default value
        "Ask for a Number", // title
        null, // mru prefix
        _test_validate_crash); // validator
    dump("\tresult: "+result+"\n");
}

function test_dialog_progress()
{
    dump("\n-------------------\nProgress dialog\n");

    var processor = {
        controller: null,
        set_controller: function(controller) {
            this.controller = controller;
            this.controller.set_progress_mode("determined");
            this.ticks = 0;
            this.ticker = window.setInterval(function(me) { me.tick();}, 500, this);
        },
        tick: function() {
            if (this.ticks == 0) {
                this.controller.set_stage("first half stage");
            } else if (this.ticks == 5) {
                this.controller.set_stage("second half stage");
            } else if (this.ticks >= 10) {
                window.clearInterval(this.ticker);
                this.controller.done();
            }
            this.controller.set_desc((10-this.ticks)+" bottles of beer on the wall");
            this.controller.set_progress_value(this.ticks * 10);
            this.ticks += 1;
        },
        cancel: function() {
            window.clearInterval(this.ticker);
            window.setTimeout(
                function (me) { me.controller.done(); },
                3000, this);
        }
    };

    var result;
    result = ko.dialogs.progress(processor,
                                 "Drink some beer. Drink some beer. Drink some beer. Drink some beer. Drink some beer. Drink some beer. Drink some beer.",
                                 "Octoberfest",
                                 true,
                                 "Actung!");
    dump("\tresult: "+result+"\n");

    result = ko.dialogs.progress(processor,
                                 "Drink some beer. (can't cancel this one)",
                                 "Mandatory Octoberfest",
                                 false,
                                 "Actung!");
    dump("\tresult: "+result+"\n");
}

function test_dialog_editEnvVar()
{
    dump("\n-------------------\nEdit Env Var dialog: no args\n");
    var result = ko.dialogs.editEnvVar();
    dump("\tresult: "+result+"\n");
    if (result) {
        dump("\t  result.name:  "+result.name+"\n");
        dump("\t  result.value: "+result.value+"\n");
    }

    dump("\n-------------------\nEdit Env Var dialog: all args\n");
    result = ko.dialogs.editEnvVar("FOO", "BAR", "my title",
                                   "test_dialog_editEnvVar");
    dump("\tresult: "+result+"\n");
    if (result) {
        dump("\t  result.name:  "+result.name+"\n");
        dump("\t  result.value: "+result.value+"\n");
    }
}

function test_dialog_internalError()
{
    dump("\n-------------------\nInternal Error Dialog:\n");
    ko.dialogs.internalError("this is my error", "quote this");
}

function _test_validate_isNumber(window, s) {
    if (Number(s) == Number(s)) { // NaN != NaN
        // valid number
    } else {
        window.alert("'"+s+"' is not a number.");
        return false;
    }
    return true;
}

function _test_validate_crash(window, s) {
    throw new Error("boom!");
}

function test_dialog_yesNoCancel()
{
    var result;
    dump("\n-------------------\nSimple Yes/No/Cancel Dialog:\n");
    result = ko.dialogs.yesNoCancel("this is my prompt", null, null,
                                    "this is my title");
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nYes/No/Cancel Dialog with some 'text':\n");
    result = ko.dialogs.yesNoCancel("this is my prompt", null,
                                    "this\nis\nsome text",
                                    "this is my title");
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nYes/No/Cancel Dialog with 'Don't ask again':\n");
    result = ko.dialogs.yesNoCancel("this is my prompt", null, null,
                                    "this is my title",
                                    "test"); // doNotAskPref
    dump("\tresult: "+result+"\n");
}


function test_dialog_yesNo()
{
    var result;
    dump("\n-------------------\nSimple Yes/No Dialog:\n");
    result = ko.dialogs.yesNo("this is my prompt", null, null,
                              "this is my title");
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nYes/No Dialog with some 'text':\n");
    result = ko.dialogs.yesNo("this is my prompt", null,
                              "this\nis\nsome text",
                              "this is my title");
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nYes/No Dialog with 'Don't ask again':\n");
    result = ko.dialogs.yesNo("this is my prompt", null, null,
                              "this is my title",
                              "test"); // doNotAskPref
    dump("\tresult: "+result+"\n");
}


function test_dialog_okCancel()
{
    var result;
    dump("\n-------------------\nSimple OK/Cancel Dialog:\n");
    result = ko.dialogs.okCancel("this is my prompt", null);
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nOK/Cancel Dialog with some 'text':\n");
    result = ko.dialogs.okCancel("this is my prompt", null,
                                 "this\nis\nsome text",
                                 "this is my title");
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nOK/Cancel Dialog with 'Don't ask again':\n");
    result = ko.dialogs.okCancel("this is my prompt", null, null,
                                 "this is my title",
                                 "test"); // doNotAskPref
    dump("\tresult: "+result+"\n");
}


function test_dialog_customButtons()
{
    var result;

    result = ko.dialogs.customButtons("one button", ["Foo"]);
    dump("\tresult: "+result+"\n");
    result = ko.dialogs.customButtons("two buttons", ["Foo", "Bar"]);
    dump("\tresult: "+result+"\n");
    result = ko.dialogs.customButtons("three buttons", ["Foo", "Bar", "Baz"]);
    dump("\tresult: "+result+"\n");
    result = ko.dialogs.customButtons("three buttons and cancel, default is Bar",
                                      ["Foo", "Bar", "Baz", "Cancel"], "Bar");
    dump("\tresult: "+result+"\n");
    result = ko.dialogs.customButtons("three buttons and cancel, default is Cancel",
                                      ["Foo", "Bar", "Baz", "Cancel"], "Cancel");
    dump("\tresult: "+result+"\n");
    result = ko.dialogs.customButtons("with some text and a title",
                                      ["Foo", "Bar", "Baz", "Cancel"], "Bar",
                                      "this\nis some\ntext", "a new title");
    dump("\tresult: "+result+"\n");
    result = ko.dialogs.customButtons("with don't ask me again",
                                      ["Foo", "Bar", "Baz", "Cancel"], "Bar",
                                      "this\nis some\ntext", "a new title",
                                      "test"); // doNotAskPref
    dump("\tresult (with doNotAskPref usage): "+result+"\n");
}


function test_dialog_alert()
{
    var result;
    dump("\n-------------------\nplain standard alert()\n");
    result = alert("this is a plain standard alert()");
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\ndialog_alert()\n");
    result = ko.dialogs.alert("this is Komodo's ko.dialogs.alert()");
    dump("\tresult: "+result+"\n");

    dump("\n-------------------\nfancy ko.dialogs.alert()\n");
    var text = "blah blah\nblah blah\nblah blah\nblah blah\nblah blah\n"
               +"blah blah\nblah blah\nblah blah\nblah blah\nblah blah\n";
    result = ko.dialogs.alert("There was a problem executing the macro: foobar",
                              text, "this is my title",
                              "test"); // doNotAskPref
    dump("\tresult: "+result+"\n");
}


function test_dialog_authenticate()
{
    dump("\n-------------------\ndialog_authenticate()\n");
    var result = ko.dialogs.authenticate2("this is my prompt",
                                          "ftp://ftp.myserver.com/",
                                          "trentm", // username
                                          false); // allowAnonymous
    dump("    result: "+result+"\n");
    if (result != null) {
        for (var attr in result) {
            try {
                dump("\tattr '"+attr+"': "+result[attr]+"\n");
            } catch(ex) {
                dump("\tattr '"+attr+"': "+ex+"\n");
            }
        }
    }
}


function test_dialog_pickPreview()
{
    dump("\n-------------------\ndialog_pickPreview(): HTML file\n");
    var result = ko.dialogs.pickPreview("file:///C:/trentm/tmp/foo.html");
    dump("    result: "+result+"\n");

    dump("\n-------------------\ndialog_pickPreview(): CSS file\n");
    result = ko.dialogs.pickPreview("file:///C:/trentm/tmp/foo2.css");
    dump("    result: "+result+"\n");
}

function test_dialog_pickicon()
{
    dump("\n-------------------\ndialog_pickIcon(): \n");
    try {
        var result = ko.dialogs.pickIcon();
    } catch (e) {
        log.exception(e);
    }
    dump("    result: "+result+"\n");
}

function test_dialog_waitfortermination()
{
    dump("\n-------------------\nlaunch waitfortermination dialog:\n");
    obj = new Object();
    obj.process = null;
    obj.command = "python foo.py";
    ko.windowManager.openOrFocusDialog(
        "chrome://komodo/content/run/waitfortermination.xul",
        "komodo_waitfortermination",
        "chrome,modal=yes,resizable=yes", obj);
    //dump("    result: "+result+"\n");
}

function test_dialog_selectFromList()
{
    var filenames, result, attr, i;

    dump("\n-------------------\ndialog_selectFromList()\n");
    filenames = ["file:///D:/trentm/as/Apps/Komodo-devel/src/version.txt",
                 "file:///D:/trentm/as/Apps/Komodo-devel/Construct",
                 ];
    result = ko.dialogs.selectFromList(
        "this is my title",
        "Select from list: using ko.uriparse.displayPath as stringifier",
        filenames,
        null,
        ko.uriparse.displayPath);
    dump("\tresult: "+result+"\n");
    attr = null;
    for (attr in result) {
        dump("attr '"+attr+"': "+result[attr]+"\n");
    }

    dump("\n-------------------\ndialog_selectFromList()\n");
    filenames = ["file:///D:/trentm/as/Apps/Komodo-devel/src/version.txt",
                 "file:///D:/trentm/as/Apps/Komodo-devel/Construct",
                 ];
    result = ko.dialogs.selectFromList(
        "this is my title",
        "Select from list: as a Yes/No/Cancel dialog",
        filenames,
        "zero-or-more", // selectionCondition
        null, // stringifier
        "test", // doNotAskPref
        true); // yesNoCancel
    dump("\tresult: "+result+"\n");
    attr = null;
    for (attr in result) {
        dump("attr '"+attr+"': "+result[attr]+"\n");
    }

    dump("\n-------------------\ndialog_selectFromList() with 'doNotAsk'\n");
    filenames = ["file:///D:/trentm/as/Apps/Komodo-devel/src/version.txt",
                 "file:///D:/trentm/as/Apps/Komodo-devel/Construct",
                 ];
    result = ko.dialogs.selectFromList(
        "this is my title",
        "Select from list: using doNotAskPref and 'zero-or-more' selection",
        filenames,
        "zero-or-more", // selectionCondition
        null, // stringifier
        "test"); // doNotAskPref
    dump("\tresult: "+result+"\n");
    attr = null;
    for (attr in result) {
        dump("attr '"+attr+"': "+result[attr]+"\n");
    }

    dump("\n-------------------\ndialog_selectFromList() with 'one'\n");
    filenames = ["file:///D:/trentm/as/Apps/Komodo-devel/src/version.txt",
                 "file:///D:/trentm/as/Apps/Komodo-devel/Construct",
                 ];
    result = ko.dialogs.selectFromList(
        "this is my title",
        "Select from list: using 'one' selection",
        filenames,
        "one"); // selectionCondition
    dump("\tresult: "+result+"\n");
    attr = null;
    for (attr in result) {
        dump("attr '"+attr+"': "+result[attr]+"\n");
    }

    dump("\n-------------------\ndialog_selectFromList() with 'one' and items are objects and use doNotAskPref\n");
    filenames = ["file:///D:/trentm/as/Apps/Komodo-devel/src/version.txt",
                 "file:///D:/trentm/as/Apps/Komodo-devel/Construct"];
    var fileObj;
    var fileObjs = [];
    for (i = 0; i < filenames.length; ++i) {
        fileObj = {"text": filenames[i],
                   "id": ko.uriparse.baseName(filenames[i])};
        fileObjs.push(fileObj);
    }
    result = ko.dialogs.selectFromList(
        "this is my title",
        "Select from list: using 'one' selection",
        fileObjs,
        "one", // selectionCondition
        null, // stringifier
        "test"); // doNotAskPref
    attr = null;
    if (result != null) {
        for (i = 0; i < result.length; ++i) {
            dump("\tfile '"+i+"': "+result[i]+"\n");
            if (typeof(result) == "object") {
                for (attr in result[i]) {
                    dump("\t  attr '"+attr+"': "+result[i][attr]+"\n");
                }
            }
        }
    }

    dump("\n-------------------\ndialog_selectFromList()\n");
    filenames = ["file:///D:/trentm/as/Apps/Komodo-devel/src/version.txt",
                 "file:///D:/trentm/as/Apps/Komodo-devel/Construct",
                 "file:///D:/trentm/as/Apps/Komodo-devel/1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/a1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/a2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/a3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/b1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/b2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/b3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/c1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/c2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/c3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/a1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/a2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/a3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/b1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/b2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/b3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/c1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/c2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/c3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/a1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/a2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/a3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/b1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/b2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/b3",
                 "file:///D:/trentm/as/Apps/Komodo-devel/c1",
                 "file:///D:/trentm/as/Apps/Komodo-devel/c2",
                 "file:///D:/trentm/as/Apps/Komodo-devel/c3",
                 ];
    result = ko.dialogs.selectFromList("this is my title",
                                       "Select files to import:",
                                       filenames);
    dump("\tresult: "+result+"\n");
    attr = null;
    for (attr in result) {
        dump("attr '"+attr+"': "+result[attr]+"\n");
    }
}



function _get_platform()
{
    var infoSvc = Components.classes['@activestate.com/koInfoService;1'].
                  getService(Components.interfaces.koIInfoService);
    return infoSvc.platform;
}


function test_uriparse()
{
    var file = ko.dialogs.prompt(
        "Enter a URI or local path with which to test uriparse.js's "+
            "conversion routines.",
        "File:",
        "file:///D:/trentm/as/Apps/Komodo-devel/Construct",
        "Test 'uriparse' Module",
        "test_ko.uriparse.mru");
    var results = "";
    results += "file: "+file+"\n";
    var methods = ["ko.uriparse.localPathToURI", ko.uriparse.localPathToURI,
                   "ko.uriparse.pathToURI", ko.uriparse.pathToURI,
                   "ko.uriparse.URIToLocalPath", ko.uriparse.URIToLocalPath,
                   "ko.uriparse.displayPath", ko.uriparse.displayPath,
                   "ko.uriparse.baseName", ko.uriparse.baseName,
                   "ko.uriparse.dirName", ko.uriparse.dirName,
                   "ko.uriparse.ext", ko.uriparse.ext,
                   ];
    for (var i = 0; i < methods.length; i += 2) {
        var name = methods[i];
        var method = methods[i+1];
        try {
            results += "  "+name+"(file): "+method(file)+"\n";
        } catch(ex) {
            results += "  "+name+"(file): error"+ex+"\n";
        }
    }
    ko.dialogs.alert("Here are the results:", results, "'uriparse' Results");
}


function test_filepicker_raw()
{
    /* Cut 'n paste that is safe for Firefox JS Console stupidities:
     *
    var fp = Components.classes["@mozilla.org/filepicker;1"].createInstance(Components.interfaces.nsIFilePicker);
    fp.init(window, "the title", Components.interfaces.nsIFilePicker.modeOpen);
    var localFile = Components.classes["@mozilla.org/file/local;1"].createInstance(Components.interfaces.nsILocalFile);
    var foo1 = localFile.initWithPath("/tmp");
    var foo2 = fp.displayDirectory = localFile;
    var rv = fp.show();
     */

    try {
        var nsIFilePicker = Components.interfaces.nsIFilePicker;
        var fp = Components.classes["@mozilla.org/filepicker;1"].createInstance(nsIFilePicker);
        var title = "this is a test: openFile";
        var mode = nsIFilePicker.modeOpen;
        log.debug("fp.init("+window+", '"+title+"', mode="+mode+")");
        fp.init(window, title, mode);

        var localFile = Components.classes["@mozilla.org/file/local;1"].createInstance(Components.interfaces.nsILocalFile);
        localFile.initWithPath("/Users/trentm/Documents");
        fp.displayDirectory = localFile;

        var rv = fp.show();
        log.debug("fp.show() returned "+rv);
        if (rv == nsIFilePicker.returnOK) {
            log.debug("fp.file: "+fp.file);
            log.debug("fp.file.path: "+fp.file.path);
            fp.file.reveal();
        }
    } catch (ex) {
        log.error("error in test_filepicker_raw: "+ex);
    }
}



function test_filepicker_openExeFile()
{
    var platform = _get_platform();
    var exe;
    if (platform == "win32") {
        exe = "C:\\Python24\\python.exe";
    } else {
        exe = "/usr/bin/grep";
    }
    var result = ko.filepicker.openExeFile(null, exe);
    dump("ko.filepicker.openExeFile() returned: "+result+"\n");
}

function test_filepicker_openFile()
{
    var platform = _get_platform();
    var folder;
    if (platform == "win32") {
        folder = "C:\\Program Files";
    } else {
        folder = "/tmp";
    }
    var result;
    dump("\n---------- ko.filepicker.openFile: all the defaults\n");
    result = ko.filepicker.openFile();
    dump("\tresult: "+result+"\n");

    dump("\n---------- ko.filepicker.openFile: specify all but limited filter set\n");
    result = ko.filepicker.openFile(folder, // default directory
                        "foo.txt", // default file
                        "this is my title", // title
                        "SQL", // default filter name
                        null); // filter names
    dump("\tresult: "+result+"\n");

    dump("\n---------- ko.filepicker.openFile: specify all options\n");
    result = ko.filepicker.openFile(folder, // default directory
                        "foo.txt", // default file
                        "this is my title", // title
                        "SQL", // default filter name
                        ["JavaScript", "Python", "SQL"]); // filter names
    dump("\tresult: "+result+"\n");

    dump("\n---------- ko.filepicker.openFile: specify all but default filter name\n");
    result = ko.filepicker.openFile(folder, // default directory
                        "foo.txt", // default file
                        "this is my title", // title
                        null, // default filter name
                        ["JavaScript", "Python", "All"]); // filter names
    dump("\tresult: "+result+"\n");

    dump("\n---------- ko.filepicker.openFile: specify bogus default filter name\n");
    result = ko.filepicker.openFile(folder, // default directory
                        "foo.txt", // default file
                        "this is my title", // title
                        "SQL", // default filter name
                        ["JavaScript", "Python", "All"]); // filter names
    dump("\tresult: "+result+"\n");
}

function test_filepicker_getFolder()
{
    var platform = _get_platform();
    var folder;
    if (platform == "win32") {
        folder = "C:\\Program Files";
    } else {
        folder = "/tmp";
    }
    var result;
    result = ko.filepicker.getFolder(folder, // default directory
                        "Please select a folder."); // prompt
    dump("\tresult: "+result+"\n");
}

function test_filepicker_saveFile()
{
    var platform = _get_platform();
    var folder;
    if (platform == "win32") {
        folder = "C:\\Program Files";
    } else {
        folder = "/tmp";
    }
    var result;
    result = ko.filepicker.saveFile(folder, // default directory
                        "foo", // default file
                        "this is my title", // title
                        "Python", // default filter name
                        ["JavaScript", "Python", "Perl", "All"]);
    dump("\tresult: "+result+"\n");

    result = ko.filepicker.saveFile(folder, // default directory
                        "foo", // default file
                        "Save Project As", // title
                        "Komodo Project"); // default filter name
    dump("\tresult: "+result+"\n");
}


function test_filepicker_openFiles()
{
    var i, files;
    dump("\n---------- ko.filepicker.openFiles: all the defaults\n");
    files = ko.filepicker.openFiles();
    if (files == null) {
        dump("\tresult: "+files+"\n");
    } else {
        dump("\tresult: "+files+"\n");
        for (i = 0; i < files.length; ++i) {
            dump("\t  file "+i+": "+files[i]+"\n");
        }
    }
}

function test_templates()
{
    var obj = new Object();
    window.openDialog("chrome://komodo/content/templates/new.xul",
                      "_blank",
                      "chrome,modal,titlebar",
                      obj);
    for (var attr in obj) {
        try {
            dump("XXX obj attr '"+attr+"': "+obj[attr]+"\n");
        } catch(ex) {
            dump("XXX obj attr '"+attr+"': "+ex+"\n");
        }
    }
}


function _reverseSortByDelta(a,b) {
    if (a.delta < b.delta) return 1;
    if (a.delta > b.delta) return -1;
    return 0;
}

function _test_TimeCommand(command)
{
    var N = 100;
    var start;
    start = new Date();
    for (j = 0; j < N; j++ ) {
        ko.commands.updateCommand(command);
    }
    delta = new Date() - start;
    return delta/N;
}

function test_TimeCommands() {
    try {
        // We'll do two sets of timing runs.  First we'll go through _each_
        // command, find its controller, and time how long it takes to
        // check whether it should be updated or not (N times).
        var commands = document.getElementsByTagName("command");
        var command, start, delta;
        var data = [];
        var datum, j;
        for (var i = 0; i < commands.length; i++) {
            command = commands[i].id;
            dump("Updating " + command + ' ' + String(N) + ' times took:')
            delta = _test_TimeCommand(command);
            datum = new Object();
            datum.id = command;
            datum.delta = delta;
            data.push(datum);
            dump(String(delta) + '\n')
        }
        // Now sort the data by time
        data.sort(_reverseSortByDelta);
        for (i = 0; i < data.length; i++) {
            dump(data[i].delta + 'msec');
            dump('\t');
            dump(data[i].id);
            dump('\n');
        }
    } catch (e) {
        log.error(e);
    }
}

function _test_TimeEvent(event)
{
    var M = 20;
    start = new Date();
    for (j = 0; j < M; j++ ) {
        window.updateCommands(event);
    }
    delta = new Date() - start;
    return delta / M;
}

function test_TimeEvents() {
    try {
        var commands = document.getElementsByTagName("command");
        var command, start, delta;
        var data = [];
        var datum, j;

        // Then we'll go over the list of known 'events' and time how
        // long it takes to update all of the resulting commands.
        var commandsets = document.getElementsByTagName("commandset");
        var commandset, events, event, child;
        var children;
        var event2commands = {};
        event2commands['ANY'] = [];
        var allevents = {};
        dump("there are " + commandsets.length + " commandsets\n");
        for (i = 0; i < commandsets.length; i++) {
            commandset = commandsets[i];
            events = commandset.getAttribute('events');
            events = events.split(',');
            for (j = 0; j < events.length; j++) {
                event = events[j];
                if (event && !(event in allevents)) {
                    allevents[event] = true;
                }
            }
        }

        for (event in allevents) {
            dump("Updating " + event + ' ' + String(M) + ' times took:')
            delta = _test_TimeEvent(event);
            datum = new Object();
            datum.id = event;
            datum.delta = delta;
            data.push(datum);
            dump(String(delta) + '\n')
        }
        // Now sort the data by time
        data.sort(_reverseSortByDelta);
        for (i = 0; i < data.length; i++) {
            dump(data[i].delta + ' msec');
            dump('\t');
            dump(data[i].id);
            dump('\n');
        }
    } catch (e) {
        log.error(e);
    }
}

function test_createEventCommandMap() {
    try {
        var i, j, k;
        var commandsets = document.getElementsByTagName("commandset");
        var commandset, events, event, child;
        var children;
        var event2commands = {};
        event2commands['ANY'] = [];
        dump("there are " + commandsets.length + " commandsets\n");
        for (i = 0; i < commandsets.length; i++) {
            commandset = commandsets[i];
            events = commandset.getAttribute('events');
            dump("events = " + events + '\n');
            events = events.split(',');
            dump("events = " + events + '\n');
            children = commandset.childNodes;
            for (j = 0; j < children.length; j++) {
                child = children[j];
                if (!events || events.length == 0 || events[0] == '*') {
                    events['ANY'].push(child.id);
                } else {
                    for (k = 0; k < events.length; k++) {
                        event = events[k];
                        dump("got event : '" + event + "'\n");
                        if (! (event in event2commands)) {
                            event2commands[event] = [];
                        }
                        event2commands[event].push(child.id);
                    }
                }
            }
        }
        var eventTime, commandTime, command;
        var data;
        for (event in event2commands) {
            if (event == 'ANY') continue; // Skip those.
            eventTime = _test_TimeEvent(event);
            dump("Updating '"+ event + "' took " + eventTime + ' msec\n');
            data = [];
            for (j = 0; j < event2commands[event].length; j++) {
                command = event2commands[event][j];
                datum = new Object();
                datum.id = command;
                commandTime = _test_TimeCommand(command)
                datum.delta = commandTime;
                data.push(datum);
            }
            data.sort(_reverseSortByDelta);
            for (i = 0; i < data.length; i++) {
                dump('\t' + data[i].delta + ' msec');
                dump('\t');
                dump(data[i].id);
                dump('\n');
            }
        }
    } catch (e) {
        log.error(e);
    }
}


function test_firefoxAutoComplete()
{
    dump("\n--------------------------------------------------\n");
    dump("test_firefoxAutoComplete()\n");
    try {
        window.open("chrome://komodo/content/test/test_firefoxAutoComplete.xul",
                    "Test Firefox AutoComplete",
                    "chrome,close=yes,resizable=yes");
    } catch(ex) {
        log.exception(ex);
    }
}


function test_debugSessionTab()
{
    dump("\n--------------------------------------------------\n");
    dump("test_debugSessionTab()\n");
    try {
        gOutputTabManager.showNewTab();
    } catch(ex) {
        log.exception(ex);
    }
}


function test_scimoz()
{
    try {
        window.openDialog("chrome://komodo/content/test/test_scimoz.xul",
                          "Komodo:TestSciMoz",
                          "titlebar,chrome,resizable,close,dialog");
    } catch(ex) {
        log.exception(ex);
    }

}

function test_auto_indent_scimoz()
{
    try {
        window.openDialog("chrome://komodo/content/test/test_auto_indent_scimoz.xul",
                          "Komodo:TestAutoIndentSciMoz",
                          "titlebar,chrome,resizable,close,dialog",
                          ko);
    } catch(ex) {
        log.exception(ex);
    }

}

function test_soft_chars()
{
    try {
        window.openDialog("chrome://komodo/content/test/test_soft_chars.xul",
                          "Komodo:TestSoftCharsSciMoz",
                          "titlebar,chrome,resizable,close,dialog",
                          ko);
    } catch(ex) {
        log.exception(ex);
    }

}
