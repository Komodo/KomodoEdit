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

try {
//dump("Loading test_uriparse.js...\n");

function test_library_uriparse() {
    // The name supplied must be the same as the class name!!
    Casper.UnitTest.TestCaseSerialClassAsync.apply(this, ["test_library_uriparse"]);
}
test_library_uriparse.prototype = new Casper.UnitTest.TestCaseSerialClassAsync();
test_library_uriparse.prototype.constructor = test_library_uriparse;

// Setup and teardown procedures, occur before/after all tests are run.
test_library_uriparse.prototype.setup = function() {
}
test_library_uriparse.prototype.tearDown = function() {
}


// Test helpers, simple pref emulator.
function _dummyPrefsClass(string_prefs) {
    this.parent = null;
    if (typeof(string_prefs) == 'undefined')
        string_prefs = {};
    this.string_dict = string_prefs
}
// XXX: What does PrefHere do?
_dummyPrefsClass.prototype.hasPrefHere = function(pref_name) {
    return pref_name in this.string_dict;
}
_dummyPrefsClass.prototype.hasStringPref = function(pref_name) {
    return pref_name in this.string_dict;
}
_dummyPrefsClass.prototype.getStringPref = function(pref_name) {
    return this.string_dict[pref_name];
}


// Test cases.

test_library_uriparse.prototype.test_getMappedURI = function() {
    //this.assertFalse(seqList.length == 0,"bindings on new part did not get applied");
    var mappingdata_for_mappedPaths = {
        "": {
            "file:///tmp/file1.txt":        "file:///tmp/file1.txt",
            "http://server/tmp/file2.txt":  "http://server/tmp/file2.txt",
            "file:///f.c":                  "file:///f.c",
            "sftp://remote/tmp/file3.txt":  "sftp://remote/tmp/file3.txt"
        },
        "http://server/tmp##file:///tmp::sftp://remote##file:///remote": {
            "file:///tmp/file1.txt":        "file:///tmp/file1.txt",
            "http://server/tmp/file2.txt":  "file:///tmp/file2.txt",
            "file:///f.c":                  "file:///f.c",
            "sftp://remote/tmp/file3.txt":  "file:///remote/tmp/file3.txt"
        }
    }

    var mappedPathPref;
    var mappingData;
    var prefs;
    var mapped_uri;
    var uri;
    var expected_uri;

    for (mappedPathPref in mappingdata_for_mappedPaths) {
        mappingData = mappingdata_for_mappedPaths[mappedPathPref];
        prefs = new _dummyPrefsClass({"mappedPaths": mappedPathPref});
        for (uri in mappingData) {
            expected_uri = mappingData[uri];
            mapped_uri = ko.uriparse.getMappedURI(uri, prefs);
            this.failUnlessEqual(mapped_uri, expected_uri,
                                 "Mapped URI was not expected: '" + mapped_uri +
                                 "' != '" + expected_uri + "'");
        }
    }
}

test_library_uriparse.prototype.test_getMappedPath = function() {
    var mappingdata_for_mappedPaths = {
        // Test when using a path for the getMappedPath() call.
        "": {
            "/tmp/file1.txt":         "/tmp/file1.txt",
            "/server/tmp/file2.txt":  "/server/tmp/file2.txt",
            "/f.c":                   "/f.c",
            "/remote/tmp/file3.txt":  "/remote/tmp/file3.txt"
        },
        "http://server/tmp##file:///tmp::sftp://remote##file:///remote": {
            "/tmp/file1.txt":         "http://server/tmp/file1.txt",
            "/server/tmp/file2.txt":  "/server/tmp/file2.txt",
            "/f.c":                   "/f.c",
            "/remote/tmp/file3.txt":  "sftp://remote/tmp/file3.txt"
        },
        // Test when using a URI for the getMappedPath() call.
        "file:///dummy##http://dummy": {
            "file:///tmp/file1.txt":         "file:///tmp/file1.txt",
            "file:///server/tmp/file2.txt":  "file:///server/tmp/file2.txt",
            "file:///f.c":                   "file:///f.c",
            "file:///remote/tmp/file3.txt":  "file:///remote/tmp/file3.txt"
        },
        "http://server/tmp##file:///tmp::sftp://remote##file:///remote::file:///dummy##http://dummy": {
            "file:///tmp/file1.txt":         "http://server/tmp/file1.txt",
            "file:///server/tmp/file2.txt":  "file:///server/tmp/file2.txt",
            "file:///f.c":                   "file:///f.c",
            "file:///remote/tmp/file3.txt":  "sftp://remote/tmp/file3.txt"
        }
    }

    var mappedPathPref;
    var mappingData;
    var prefs;
    var mapped_uri;
    var path;
    var expected_uri;

    for (mappedPathPref in mappingdata_for_mappedPaths) {
        mappingData = mappingdata_for_mappedPaths[mappedPathPref];
        prefs = new _dummyPrefsClass({"mappedPaths": mappedPathPref});
        for (path in mappingData) {
            expected_uri = mappingData[path];
            mapped_uri = ko.uriparse.getMappedPath(path, prefs);
            this.failUnlessEqual(mapped_uri, expected_uri,
                                 "Mapped URI was not expected: '" + mapped_uri +
                                 "' != '" + expected_uri + "'");
        }
    }
}


// Start testing...
var testInstance = new test_library_uriparse();
var suite = new Casper.UnitTest.TestSuite("Library/Uriparse");
suite.add(testInstance);
Casper.UnitTest.testRunner.add(suite);

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}
