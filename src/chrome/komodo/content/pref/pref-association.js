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

// Dev Notes:
// - REFACTOR: rip out the invocationName stuff from file assoc prefs. It isn't
//   used.


// Constants and global variables
var cellparent, cellparent_value;
var data = {
  associations: null
};
var dialog  = {}; //XXX used both for easy access to named XUL elements and to keep

var gLangRegistry = Components.classes["@activestate.com/koLanguageRegistryService;1"]
        .getService(Components.interfaces.koILanguageRegistryService);

// A handle on functions that we need in PrefAssociation_OkCallback(). Every
// reference to one of these functions that might be called, directly or
// indirectly, from PrefAssociation_OkCallback() must be accessed through
// the dialog object, or this will break.  For consistency, we always call
// these functions through the dialog object.



//---- Association class (one for each file association)
//
// Each Association object has a unique identifier.  This is used to
// establish a relationship between the association object and the
// items in the tree that represent it.

function Association(pattern, language, invocationName) {
  this.pattern = pattern;
  this.language = language;
  this.invocationName = invocationName;
  this.id = Association._generateId();
}

Association._index = 0;  // used for generating ids
Association._generateId = function() {
  return "assoc" + Association._index++;
}



// Handlers

function PrefAssociation_OnLoad() {
    dialog.addPatternTextfield = document.getElementById('addPatternTextfield');
    dialog.addLanguageList = document.getElementById('addLanguageList');
    dialog.addButton = document.getElementById('addButton');
    dialog.associationList = document.getElementById('associationList');
    dialog.languageList = document.getElementById('languageList');

    parent.hPrefWindow.onpageload();
}

function OnPreferencePageInitalize(prefset) {
    data.associations = getAssociationListFromPreference(prefset);
}

function OnPreferencePageLoading(prefset) {
  dialog.languageList.selection = document.getAnonymousNodes(dialog.languageList)[0].firstChild.firstChild.getAttribute('label');

  dialog.addLanguageList.selection = document.getAnonymousNodes(dialog.addLanguageList)[0].firstChild.firstChild.getAttribute('label');

  // fill out the associations tree - should cache this entire tree.
  // adding items while collapsed is:
  // a) much faster, and
  // b) does not crash on Linux (who knows why, but this solves it :)
  for (var i = 0; i < data.associations.length; i++) {
      associationListAddRow(data.associations[i].id,data.associations[i].pattern,data.associations[i].language);
  }
  dialog.associationList.selectedIndex = 0;
}

function OnPreferencePageOK(prefset) {
    var pattern = dialog.addPatternTextfield.value;
    if (pattern) {
        var sampleName = pattern.replace(/\*/g, "sample");
        if (!gLangRegistry.suggestLanguageForFile(sampleName)) {
            var resp = ko.dialogs.yesNoCancel("Would you like to add an association for "
                                              + pattern
                                              + " and language "
                                              + dialog.addLanguageList.selection
                                              + "?",
                                              "Yes", // not current behavior
                                              null, // text field
                                              "Unadded New File Association");
            if (resp == "Yes") {
                onAddAssociation();
            } else if (resp == "Cancel") {
                return false;
            }
        }
    }

    // Save the associations to the prefs.

    var patterns = new Array();
    var languageNames = new Array();
    for (var i=0; i < data.associations.length; i++) {
      patterns.push(data.associations[i].pattern);
      languageNames.push(data.associations[i].language);
    }
    try {
      var assocPref = gLangRegistry.createFileAssociationPrefString(patterns.length,
                                                    patterns,
                                                    languageNames.length,
                                                    languageNames);
      prefset.setStringPref("fileAssociationDiffs", assocPref);
    } catch(ex) {
      var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                         .getService(Components.interfaces.koILastErrorService);
      //XXX This error message isn't really actionable. Offer to throw away
      //    these changes? Use ko.dialogs.internalError?
      ko.dialogs.alert("There was an error saving your file association changes: "
                   +lastErrorSvc.getLastErrorMessage());
    }

    return true;
}

// Return an array of Association objects, built from the fileAssociations
// preference.
// REFACTOR: s/FromPreference//
function getAssociationListFromPreference(prefset) {
  // The language registry provides a sorted list of the current file
  // associations.
  var patternsObj = new Object();
  var languageNamesObj = new Object();
  gLangRegistry.getFileAssociations(new Object(), patternsObj,
                                    new Object(), languageNamesObj);
  var patterns = patternsObj.value;
  var languageNames = languageNamesObj.value;

  var associations = new Array();
  for (var i=0; i < patterns.length; i++) {
    associations.push(new Association(patterns[i], languageNames[i], ""));
  }
  return associations;
}


function associationListAddRow(id, pattern, language) {
    var item = dialog.associationList.appendItem(pattern, language);
    item.id = id;
    return item;
}

function onAddAssociation() {
  var pattern = dialog.addPatternTextfield.value;
  var language = dialog.addLanguageList.selection;
  var invocation = "";
  var association = new Association(pattern, language, invocation);

  data.associations.push(association);

  var newitem = associationListAddRow(association.id,pattern,language);

  dialog.addPatternTextfield.setAttribute('value', '');

  dialog.associationList.ensureElementIsVisible ( newitem );
  dialog.associationList.selectItem ( newitem );
  dialog.addPatternTextfield.focus();
  updateButtonStates();
  dialog.addPatternTextfield.value = '';
}

function onRemoveAssociation() {
  var kids = dialog.associationList;
  var selItem = dialog.associationList.selectedItem;  // treeitem
  var pattern = selItem.getAttribute('label');
  if (!pattern) return;
  var index = getPatternIndex(pattern);
  // remove the item from the association array
  data.associations.splice(index, 1);

  // Remove the item from the tree
  var nextUp;
  if (selItem.nextSibling)
      nextUp = selItem.nextSibling;
  else if (selItem.previousSibling)
      nextUp = selItem.previousSibling;
  kids.removeChild(selItem);
  dialog.associationList.selectedItem = nextUp;
  cellparent = nextUp;
}

function selectAssociation(event)  {
    if (!dialog.associationList || dialog.associationList.selectedIndex < 0) return true;
    var assoc = data.associations[dialog.associationList.selectedIndex];
    dialog.languageList.selection = assoc.language;
    return true;
}

function updateAssociation()  {
      if (dialog.associationList.selectedIndex >= 0)  {
          data.associations[dialog.associationList.selectedIndex].language =
                        dialog.languageList.selection;
      }
}

function updateButtonStates() {
  var pattern = trimString(dialog.addPatternTextfield.value);
  if (!pattern || getPatternIndex(pattern) != null) {
    dialog.addButton.setAttribute('disabled', 'true');
  } else {
    dialog.addButton.removeAttribute('disabled');
  }
}

// DOM construction helpers

function getPatternIndex(pattern) {
  for (var i = 0; i < data.associations.length; i++) {
    if (pattern == data.associations[i].pattern) return i;
  }
  return null;
}

function getIdIndex(id) {
  for (var i = 0; i < data.associations.length; i++) {
    if (id == data.associations[i].id) return i;
  }
  return null;
}

// Remove whitespace from both ends of a string
function trimString(string)
{
  if (!string) return "";
  return string.replace(/(^\s+)|(\s+$)/g, '')
}
