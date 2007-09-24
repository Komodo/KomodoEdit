/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*-
/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Mozilla Communicator client code, released
 * March 31, 1998.
 *
 * The Initial Developer of the Original Code is
 * Netscape Communications Corporation.
 * Portions created by the Initial Developer are Copyright (C) 1998-1999
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *
 * ***** END LICENSE BLOCK ***** */

var gPersonalDict;
var gCurrentLanguage;
var gWordToAdd;

function Startup() {
    // Get the SpellChecker shell
    try {
        var mainSc = window.opener.ko.extensions.spellchecker;
        gPersonalDict = mainSc.getPersonalDictionary();
        gCurrentLanguage = mainSc.getCurrentDictionaryLanguage();
    } catch(ex) {
        dump("koDictionary.js -- Startup: " + ex + "\n");
        gPersonalDict = null;
    }
    if (!gPersonalDict) {
        window.close();
        return;
    }
    
    // The word to add word is passed as the 2nd extra parameter in window.openDialog()
    gWordToAdd = window.arguments[1];
  
    gDialog.WordInput = document.getElementById("WordInput");
    gDialog.DictionaryList = document.getElementById("DictionaryList");
  
    gDialog.WordInput.value = gWordToAdd;
    FillDictionaryList();

    // Select the supplied word if it is already in the list
    SelectWordToAddInList();
    SetTextboxFocus(gDialog.WordInput);
}

function ValidateWordToAdd() {
    gWordToAdd = TrimString(gDialog.WordInput.value);
    return (gWordToAdd.length > 0);
}    

function SelectWordToAddInList() {
    for (var i = 0; i < gDialog.DictionaryList.getRowCount(); i++) {
        var wordInList = gDialog.DictionaryList.getItemAtIndex(i);
        if (wordInList && gWordToAdd == wordInList.label) {
            gDialog.DictionaryList.selectedIndex = i;
            break;
        }
    }
}

function AddWord() {
  if (ValidateWordToAdd()) {
      try {
        gPersonalDict.addWord(gWordToAdd, gCurrentLanguage);
      } catch (e) {
          dump("Exception occured in gPersonalDict.addWord\nWord to add probably already existed:" + ex + "\n");
      }

      // Rebuild the dialog list
      FillDictionaryList();

      SelectWordToAddInList();
      gDialog.WordInput.value = "";
  }
}

function ReplaceWord() {
    if (ValidateWordToAdd()) {
        var selItem = gDialog.DictionaryList.selectedItem;
        if (selItem) {
            try {
              gPersonalDict.removeWord(selItem.label, gCurrentLanguage);
            } catch (e) {}

            try {
                // Add to the dictionary list
              gPersonalDict.addWord(gWordToAdd, gCurrentLanguage);

                // Just change the text on the selected item
                //  instead of rebuilding the list
                selItem.label = gWordToAdd; 
            } catch (e) {
                // Rebuild list and select the word - it was probably already in the list
                dump("Exception occured adding word in ReplaceWord\n");
                FillDictionaryList();
                SelectWordToAddInList();
            }
        }
    }
}

function RemoveWord() {
    var selIndex = gDialog.DictionaryList.selectedIndex;
    if (selIndex >= 0) {
        var word = gDialog.DictionaryList.selectedItem.label;

        // Remove word from list
        gDialog.DictionaryList.removeItemAt(selIndex);

        // Remove from dictionary
        try {
            //Not working: BUG 43348
          gPersonalDict.removeWord(word, gCurrentLanguage);
        } catch (e) {
            dump("Failed to remove word from dictionary\n");
        }
        ResetSelectedItem(selIndex);
    }
}

function FillDictionaryList() {
    var selIndex = gDialog.DictionaryList.selectedIndex;

    // Clear the current contents of the list
    ClearListbox(gDialog.DictionaryList);

    var haveList = false;

    // Get words until an empty string is returned
    var w = gPersonalDict.wordList;
    while (w.hasMore()) {
        var word = w.getNext();
        if (word != "") {
            gDialog.DictionaryList.appendItem(word, "");
            haveList = true;
        }
    }
  
    //XXX: BUG 74467: If list is empty, it doesn't layout to full height correctly
    //     (ignores "rows" attribute) (bug is latered, so we are fixing here for now)
    if (!haveList)
        gDialog.DictionaryList.appendItem("", "");

    ResetSelectedItem(selIndex);
}

function ResetSelectedItem(index) {
    var lastIndex = gDialog.DictionaryList.getRowCount() - 1;
    if (index > lastIndex)
        index = lastIndex;

    // If we didn't have a selected item, 
    //  set it to the first item
    if (index == -1 && lastIndex >= 0)
        index = 0;

    gDialog.DictionaryList.selectedIndex = index;
}

function onClose()
{
  return true;
}
