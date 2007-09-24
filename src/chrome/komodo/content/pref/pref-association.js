/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Dev Notes:
// - REFACTOR: rip out the invocationName stuff from file assoc prefs. It isn't
//   used.


// Constants and global variables
var cellparent, cellparent_value;
const VK_ENTER = 13;  // the keycode for the "Enter" key
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

function OnPreferencePageClosing(prefset, ok) {
    if (!ok) return;
    var patterns = new Array();
    var languageNames = new Array();
    for (var i=0; i < data.associations.length; i++) {
      patterns.push(data.associations[i].pattern);
      languageNames.push(data.associations[i].language);
    }
    try {
      gLangRegistry.saveFileAssociations(patterns.length, patterns,
          languageNames.length, languageNames);
    } catch(ex) {
      var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                         .getService(Components.interfaces.koILastErrorService);
      //XXX This error message isn't really actionable. Offer to throw away
      //    these changes? Use ko.dialogs.internalError?
      ko.dialogs.alert("There was an error saving your file association changes: "
                   +lastErrorSvc.getLastErrorMessage());
    }
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
