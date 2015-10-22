
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

/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*-
*/ if (1) {
/* ***** BEGIN LICENSE BLOCK *****

 * ***** END LICENSE BLOCK ***** */}
gDialog = {};

var ko = {
    extensions : {
        spellchecker : {
            instance : null
        }
    }
};

(function() { /* ko.extensions.spellchecker */

    var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"].
                    getService(Components.interfaces.nsIStringBundleService).
                    createBundle("chrome://komodospellchecker/locale/spellcheck.properties");

    function KoSpellCheck(session, args) {
        this.session = session;  // pointer to namespace object
        this.scimoz = args.scimoz;
        this.misspelledWord = null;
        this.spellChecker = (Components.classes['@mozilla.org/spellchecker/engine;1'].
                    getService(Components.interfaces.mozISpellCheckingEngine));
        if (!this.spellChecker) {
            throw new Error("SpellChecker not found!!!\n");
        }

        // Figure out which language to use
        var targetLang = null;
        try {
            var o1 = {};
            this.spellChecker.getDictionaryList(o1, {});
            var dictList = o1.value;
            if (dictList) {
                var prefset = args.view.koDoc.getEffectivePrefs();
                var currDocLang = this.getLastSpellCheckLanguage(prefset);
                if (currDocLang && dictList.indexOf(currDocLang) >= 0) {
                    targetLang = currDocLang;
                } else {
                    targetLang = dictList[0];
                }
            }
        } catch(ex) {
            dump(ex + "\n");
        }
        this.spellChecker.dictionary = this.language = (targetLang || 'en-US');
        if (this.spellChecker.providesPersonalDictionary) {
            this.personalDictionary = this.spellChecker.personalDictionary;
        } else {
            try {
                this.personalDictionary = Components.classes["@mozilla.org/spellchecker/personaldictionary;1"]
                               .getService(Components.interfaces.mozIPersonalDictionary);
            } catch (ex) {
                dump("creating personalDictionary: " + ex + "\n");
                this.personalDictionary = null;
            }
        }
        if (this.personalDictionary) {
            this.personalDictionary.load();
        }
        this.skipBlockQuotes = args.skipBlockQuotes;
        this.enableSelectionChecking = args.enableSelectionChecking;
        this.allowSelectWord = true;
        this.previousReplaceWord = "";
        this.firstTime = true;
        this.lastSelectedLang = null;
        this.cancelled = false;

        this.highBit_re = /[^\x00-\x7f]/;
    }
    
    KoSpellCheck.prototype = {
        // data
        checkUserInputDelay : 100, //msec
        
        standardWidgetNames : [
                "MisspelledWordLabel",
                "ReplaceWordLabel",
                "ReplaceWordInput",
                "CheckWord",
                "SuggestedListLabel",
                "SuggestedList",
                "Ignore",
                "IgnoreAll"
                ],
        
        //helpers        

        do_continue : function(func, args) {
            var self = this;
            setTimeout(function() {
                func.apply(self, args);
            }, 0);
        },

        _byteLengthFromJSString : function _byteLengthFromJSString(s) {
            if (s.match(this.highBit_re)) {
                return Components.classes["@activestate.com/koSysUtils;1"].
                getService(Components.interfaces.koISysUtils).byteLength(s);
            } else {
                return s.length;
            }
        },
        
        _doReplacement : function _doReplacement(word_start, word, repl) {
            var word_end = word_start + this._byteLengthFromJSString(word);
            this.scimoz.targetStart = word_start;
            this.scimoz.targetEnd = word_end;
            return this._doReplacementExtent(word_end - word_start,
                                             this._byteLengthFromJSString(repl),
                                             repl);
        },
        
        _doReplacementExtent : function _doReplacement(oldWord_length, // bytes
                                                       repl_length,   // bytes
                                                       repl) {
            this.scimoz.replaceTarget(repl);
            var delta = repl_length - oldWord_length;
            this.scimozNextStart = this.scimoz.targetEnd + delta;
            this.endPosition += delta;
        },
        
        getStyleExtent : function getStyleExtent(style, startPos, endPos) {
            for (var i = startPos; i < endPos; i++) {
                if ((this.scimoz.getStyleAt(i)) != style) {
                    return i;
                }
            }
            return endPos;
        },
        getTextStylesFromLanguageObj : function getTextStylesFromLanguageObj() {
            function _addStyles(text_styles, list) {
                for (var i in list) {
                    text_styles[list[i]] = true;
                }
            };
            var count_obj = {};
            var langObj = this.view.languageObj;
            // This includes the default style of 0, but in markup(SSL)
            // docs will skip cdata marked sections for now.  These usually
            // contain code, so it's not too painful a decision.
            this.text_styles = {0:1};
            _addStyles(this.text_styles, langObj.getCommentStyles(count_obj));
            _addStyles(this.text_styles, langObj.getStringStyles(count_obj));
            _addStyles(this.text_styles, langObj.getNamedStyles("data sections"));
            return null;
        },

        
        // methods

        FinalInit : function FinalInit() {
            gDialog.MisspelledWordLabel = document.getElementById("MisspelledWordLabel");
            gDialog.MisspelledWord      = document.getElementById("MisspelledWord");
            gDialog.ReplaceButton       = document.getElementById("Replace");
            gDialog.IgnoreButton        = document.getElementById("Ignore");
            gDialog.StopButton          = document.getElementById("Stop");
            gDialog.CloseButton         = document.getElementById("Close");
            gDialog.ReplaceWordInput    = document.getElementById("ReplaceWordInput");
            gDialog.SuggestedList       = document.getElementById("SuggestedList");
            gDialog.LanguageMenulist    = document.getElementById("LanguageMenulist");
            
            // Fill in the language menulist and sync it up
            // with the spellchecker's current language.
          
            this.InitLanguageMenu();
            gDialog.StopButton.hidden = true;
            
            this.getTextStylesFromLanguageObj();
            // Simplified, scintilla-ready regex'es
            // For scintilla, \w => a-zA-Z\x80-\xff (assumes utf-8)
            // bug 72412: Watch out for words that include an
            // apostrophe that's actually the string delimiter.  For now
            // don't bother with words that start or end with an apostrophe.
            // Yes, check for words that are at least two characters long.
            // 
            var word_match = /[\w_][\w\d\.'_\-]*[\w_]/;
            var skip_word_ptns = [/[\._]/, /[a-z].*[A-Z]/, /[\d]/, /'.*'/]; // skip anything containing one of these
            
            function expand_ptn(ptn) {
                var s =  ptn.replace(/\\w/g, 'a-zA-Z\\x80-\\xff').replace(/\\d/g, '0-9');
                //dump("expanded => ptn " + s + "\n");
                return s;
            }
            
            this.word_match_re = expand_ptn(word_match.source);
            this.word_match_len = this.word_match_re.length;
            this.skip_word_ptn_re = {};
            for (var i in skip_word_ptns) {
                var s = expand_ptn(skip_word_ptns[i].source);
                this.skip_word_ptn_re[s] = s.length;
            }
            // JS RE
            this.all_caps_re = /^[A-Z]+$/;
        },
        
        AddToDictionary : function AddToDictionary() {
            if (this.misspelledWord && this.personalDictionary) {
                this.personalDictionary.addWord(this.misspelledWord, this.language);
            }
            this.FindNextWord();
        },
        
        Advance : function Advance(len) {
            this.currPosition += len;
            this.FindNextWord();
        },
        CheckWord : function CheckWord(word) {
            if (this.spellChecker.check(word)) {
                ClearListbox(gDialog.SuggestedList);
                var item = gDialog.SuggestedList.appendItem("(correct spelling)", "");
                if (item) {
                    item.setAttribute("disabled", "true");
                }
                // Suppress being able to select the message text
                this.allowSelectWord = false;
            } else { 
                this.FillSuggestedList(word);
                this.session.SetReplaceEnable();
            }
        },

        Ignore : function Ignore() {
            if (this.misspelledWord) {
                // rely on this.scimozNextStart
                this.FindNextWord();
            } else {
                this.Advance(1);
            }
        },
        
        FindNextWord : function FindNextWord() {
            //dump(">> FindNextWord\n");
            if (this.cancelled) return; // leave
            this.misspelledWord = null;
            this.DoEnabling();
            gDialog.MisspelledWord.setAttribute("value",
                                                _bundle.GetStringFromName("checking"));
            var i;
            if (this.scimozNextStart) {
              i = this.currPosition = this.scimozNextStart;
              this.scimozNextStart = null;
            } else {
              i = this.currPosition;
            }
            var endPos = this.endPosition;
            var startTime = Date.now();
            //dump("startpos = " + this.startPosition
            //     + ", endPos = " + endPos
            //     + ", i = " + i
            //     + "\n");
            // outer loop on the buffer
            while (i < endPos) {
                //dump("Start looking at pos " + i + "/" + endPos + ")...");
                // Need to set this each time
                this.scimoz.targetStart = i;
                this.scimoz.targetEnd = endPos;            
                while (true) {
                    // one-time through loop with a cleanup/check at the end
                    var res = this.scimoz.searchInTarget(this.word_match_len, this.word_match_re);
                    if (res == -1) {
                        //dump("Failed to find a word in "
                        //     + this.scimoz.targetStart
                        //     + ":" + this.scimoz.targetEnd + "\n");
                        i = this.scimoz.targetEnd;
                        break;
                    }
                    var possibleTargetStart = this.scimoz.targetStart;
                    var possibleTargetEnd = this.scimoz.targetEnd;
                    i = possibleTargetEnd;
                    var rej = false;
                    for (var ptn in this.skip_word_ptn_re) {
                        var plen = this.skip_word_ptn_re[ptn];
                        if (this.scimoz.searchInTarget(plen, ptn) != -1) {
                            rej = true;
                            break;
                        }
                    }
                    if (rej) break;
                    var style = this.scimoz.getStyleAt(possibleTargetEnd - 1);
                    if (!this.text_styles[style] || this.scimoz.getStyleAt(possibleTargetStart) != style) {
                        break;
                    }
                    var word = this.scimoz.getTextRange(possibleTargetStart, possibleTargetEnd);
                    if (word.match(this.all_caps_re)
                        || this.session.skip_words[word]
                        || this.spellChecker.check(word)) {
                        // Nothing to do
                    } else if (this.personalDictionary && this.personalDictionary.check(word, this.language)) {
                        //dump("Found word " + word + " in the personal dict\n");
                    } else {
                        this.misspelledWord = word;
                        this.currPosition = possibleTargetStart; // at the start of the word to check
                        // Do this because scintilla works with UTF-8,
                        // JS with UCS-2
                        this.scimozNextStart = this.scimoz.targetEnd;
                        this.SetWidgetsForMisspelledWord();
                        
                        //dump("<<early FindNextWord\n");
                        return;
                    }
                    break;
                }
                if (Date.now() - startTime >= this.checkUserInputDelay) {
                    this.misspelledWord = null;
                    this.currPosition = i; // at the start of the word to check
                    //dump("<<... FindNextWord\n");
                    this.do_continue(this.FindNextWord, []);
                    return;
                }
            }
            this.misspelledWord = null;
            if (this.doWrap) {
                this.doWrap = false;
                this.endPosition = this.startPosition;
                this.startPosition = this.currPosition = 0;
                this.scimoz.colourise(0, this.endPosition);
                this.do_continue(this.FindNextWord);
                return;
            }
            this.currPosition = this.endPosition;
            this.SetWidgetsForMisspelledWord();
            //dump("<<final FindNextWord\n");
        },
        
        DoEnabling : function DoEnabling() {
            //TODO: Do proper state-based analysis
            //dump(">> DoEnabling\n");
            var have_misspelled_word = this.misspelledWord != null;
            if (!have_misspelled_word) {
                // No more misspelled words
                gDialog.MisspelledWord.setAttribute("value", this.firstTime ? _bundle.GetStringFromName("noMisspelledWords") : _bundle.GetStringFromName("completedSpellChecking"));
            
                gDialog.ReplaceButton.removeAttribute("default");
                gDialog.IgnoreButton.removeAttribute("default");
            
                gDialog.CloseButton.setAttribute("default","true");
                // Shouldn't have to do this if "default" is true?
                gDialog.CloseButton.focus();
            }
            for (var i in this.standardWidgetNames) {
                SetElementEnabledById(this.standardWidgetNames[i], have_misspelled_word);
            }
            if (!have_misspelled_word) {
                SetElementEnabledById("Replace", false);
                SetElementEnabledById("ReplaceAll", false);
            } else {            
                gDialog.CloseButton.removeAttribute("default");
                this.session.SetReplaceEnable();
            }
            //TODO: Implement a personal dictionary, including IgnoreAll
            var haveDict = !!this.personalDictionary;
            SetElementEnabledById("AddToDictionary", haveDict);
            SetElementEnabledById("EditDictionary", haveDict);
            SetElementEnabledById("LanguageMenulist", haveDict);
            //dump("<< DoEnabling\n");
        },
        
        FillSuggestedList : function FillSuggestedList() {
            //dump(">> FillSuggestedList\n");
            var misspelledWord = this.misspelledWord;
            if (!misspelledWord) {
                //dump("<<early FillSuggestedList\n");
                return;
            }
            try {
            var list = gDialog.SuggestedList;          
            // Clear the current contents of the list
            this.allowSelectWord = false;
            ClearListbox(list);
            var item;
            // Get suggested words until an empty string is returned
            var suggestions = {value:null};
            var count = {};
            this.spellChecker.suggest(misspelledWord, suggestions, count);
            if (!count.value) {
              // No suggestions - show a message but don't let user select it
              item = list.appendItem(_bundle.GetStringFromName("noSuggestedWords"));
              if (item) item.setAttribute("disabled", "true");
              this.allowSelectWord = false;
            } else {
                //dump("suggestions: " + suggestions.value + "\n");
                for (var idx in suggestions.value) {
                    var newWord = suggestions.value[idx];
                    list.appendItem(newWord);
                }
                this.allowSelectWord = true;
                // Initialize with first suggested list by selecting it
                gDialog.SuggestedList.selectedIndex = 0;
            }
            }catch(ex) { dump("FillSuggestedList: " + ex + "\n");
                }
            //dump("<< FillSuggestedList\n");
        },

        getLastSpellCheckLanguage : function getLastSCLanguage(prefset) {
            var lastLangID;
            if (!prefset.hasStringPref("spellcheckLangID")) {
                return null;
            } else {
                return prefset.getStringPref("spellcheckLangID");
            }
        },

        setLastSpellCheckLanguage : function getLastSCLanguage(prefset, langID) {
          if (prefset) {
              prefset.setStringPref("spellcheckLangID", langID);
          }
        },

        getGlobalPrefs : function getGlobalPrefs() {
          return Components.classes["@activestate.com/koPrefService;1"].
              getService(Components.interfaces.koIPrefService).prefs;
        },

        InitLanguageMenu: function InitLanguageMenu() {
            // First get the list of dictionary names
            // Then look at the current document's last spellcheck-language.
            // If it has one, or use the global spellcheck language (which
            // is set the first time the spellchecker is used, and every
            // time after that.
            // If this language is in the list, use it.
            // Otherwise settle for the first language in the list.
          
            var o1 = {};
            var o2 = {};
          
            // Get the list of dictionaries from
            // the spellchecker.
          
            try {
                this.spellChecker.getDictionaryList(o1, o2);
            } catch(ex) {
                dump("Failed to get DictionaryList!" + ex + "\n");
                return;
            }
          
            var dictList = o1.value;
            var dictLangHash = {};
            var count    = o2.value;
          
            var isoStrArray;
            var defaultItem = null;
            var langId;
            var i;
            var prefset = this.koDoc.getEffectivePrefs();
            var currDocLang = this.getLastSpellCheckLanguage(prefset);
            var needToSetDictionary = true;
            for (i = 0; i < dictList.length; i++) {
                try {
                    langId = dictList[i];
                    //dump("Read langId = " + langId + "\n");
                    dictLangHash[langId] = 1;
                    isoStrArray = dictList[i].split("-");
              
                    dictList[i] = new Array(2); // first subarray element - pretty name
                    dictList[i][1] = langId;    // second subarray element - language ID
                    
              
                    if (dictList[i][0] && isoStrArray.length > 2 && isoStrArray[2])
                        dictList[i][0] += " (" + isoStrArray[2] + ")";
              
                    if (!dictList[i][0])
                        dictList[i][0] = dictList[i][1];
                    //dump("Setting dictList[" + i + "] = " + dictList[i].join(":") + "\n");
                } catch (ex) {
                    // GetString throws an exception when
                    // a key is not found in the bundle. In that
                    // case, just use the original dictList string.
            
                    dictList[i][0] = dictList[i][1];
                    dump("Exc (" + ex + "): Setting dictList[" + i + "] = " + dictList[i][0] + "\n");
                }
            }
            
            // note this is not locale-aware collation, just simple ASCII-based sorting
            // we really need to add loacel-aware JS collation, see bug XXXXX
            dictList.sort();
    
            var curLang = null;
            if (currDocLang && dictLangHash[currDocLang]) {
                //dump("using the document lang of " + currDocLang + "\n");
                curLang = currDocLang;
            } else if (dictList.length) {
                //dump("using default first read lang of " + dictList[0][1] + "\n");
                curLang = dictList[0][1];
                this.setLastSpellCheckLanguage(prefset, curLang);
                this.setLastSpellCheckLanguage(this.getGlobalPrefs(), curLang);
            }
            if (curLang) {
                this.spellChecker.dictionary = curLang;
            }
            
            for (i = 0; i < dictList.length; i++) {
                var item = gDialog.LanguageMenulist.appendItem(dictList[i][0], dictList[i][1]);
                if (curLang) {
                    if (dictList[i][1] == curLang) {
                        defaultItem = item;
                        //dump("found defaultItem = " + curLang+ "\n");
                    } else if (!defaultItem && dictList[i][1].indexOf(curLang) == 0){
                        defaultItem = item;
                    }
                } else {
                    //dump("curLang = " + curLang + ", dictList[" + i + "][1] = " + dictList[i][1] + "\n");
                }
            }
          
            // Now make sure the correct item in the menu list is selected.
          
            if (defaultItem) {
                gDialog.LanguageMenulist.selectedItem = defaultItem;
                this.lastSelectedLang = defaultItem;
            }
        },

        onClose : function onClose() {
            if (this.personalDictionary) {
                try {
                    this.personalDictionary.save();
                } catch(ex) {
                    dump("onClose: " + ex + "\n");
                }
            }
            this.cancelled = true;
            this.spellChecker = null;
        },
        
        Replace : function Replace(newWord) {
            this._doReplacement(this.currPosition, this.misspelledWord, newWord);
            this.currPosition += newWord.length;
            this.FindNextWord();
        },
        
        ReplaceAll : function Replace(newWord) {
            // This probably won't work for high-bit chars
            var scintillaPtn = '\\<' + this.misspelledWord + '\\>';
            var oldWordUnicodeLen = this.misspelledWord.length;
            var scinPtnLen = 4 + oldWordUnicodeLen; // length of '\\<' + '\\>'
            var oldWordLen = this._byteLengthFromJSString(this.misspelledWord);
            var delta = newWordLen - oldWordLen;
            
            var newWordLen = this._byteLengthFromJSString(newWord);
            var finalNextStart = this.scimoz.targetStart + newWordLen;
            this.scimoz.targetStart = this.currPosition;
            
            // Position the final next-start after the end of the first change
            // This is where we start if there are no changes
            while (true) {
                this.scimoz.targetEnd = this.endPosition;
                var res = this.scimoz.searchInTarget(scinPtnLen, scintillaPtn);
                if (res == -1) {
                    this.scimozNextStart = finalNextStart;
                    break;
                } else {
                    this._doReplacementExtent(oldWordLen, newWordLen, newWord);
                    this.scimoz.targetStart = this.scimozNextStart;
                }
            }
            // this.scimoz.targetEnd = this.endPosition;
            this.FindNextWord();
        },

        SetWidgetsForMisspelledWord : function SetWidgetsForMisspelledWord() {
            
            //dump(">> SetWidgetsForMisspelledWord\n");
            gDialog.MisspelledWord.setAttribute("value",
                                                TruncateStringAtWordEnd(this.misspelledWord, 30, true));
            // Initial replace word is misspelled word
            gDialog.ReplaceWordInput.value = this.misspelledWord;
            this.previousReplaceWord = this.misspelledWord;
          
            // This sets gDialog.ReplaceWordInput to first suggested word in list
            this.FillSuggestedList(this.misspelledWord);
            this.DoEnabling();
            this.firstTime = false;
            if (this.misspelledWord) {
              SetTextboxFocus(gDialog.ReplaceWordInput); //EdDialogCommon.js
              var i = this.currPosition;
              var scimozEndPos = this.scimozNextStart || i + this.misspelledWord.length;
              this.scimoz.gotoPos(i);
              this.scimoz.setSel(i, scimozEndPos);              
            }
            //dump("<< SetWidgetsForMisspelledWord\n");
              
        },

        __END__ : null
    };
    this.AddToDictionary = function AddToDictionary() {
        this.instance.AddToDictionary();
    };
    
    this.AllowSelectWord = function AllowSelectWord() {
        return this.instance.allowSelectWord;
    };
    
    this.CancelSpellCheck = function CancelSpellCheck() {
        if (this.instance) {
            this.instance.onClose();
        }
        window.opener.cancelSendMessage = false;
        return true;
    };
    this.ChangeReplaceWord = function ChangeReplaceWord() {
      // Calling this triggers SelectSuggestedWord(),
      //  so temporarily suppress the effect of that
      var saveAllow = this.AllowSelectWord();
      this.instance.allowSelectWord = false;
    
      // Select matching word in list
      var newIndex = -1;
      var newSelectedItem;
      var replaceWord = TrimString(gDialog.ReplaceWordInput.value);
      if (replaceWord)
      {
        for (var i = 0; i < gDialog.SuggestedList.getRowCount(); i++)
        {
          var item = gDialog.SuggestedList.getItemAtIndex(i);
          if (item.getAttribute("label") == replaceWord)
          {
            newSelectedItem = item;
            break;
          }
        }
      }
      gDialog.SuggestedList.selectedItem = newSelectedItem;
    
      this.instance.allowSelectWord = saveAllow;
    
      // Remember the new word
      this.instance.previousReplaceWord = gDialog.ReplaceWordInput.value;
    
      this.SetReplaceEnable();
    }
    
    this.CheckWord = function CheckWord() {
        var word = gDialog.ReplaceWordInput.value;
        if (word) {
            this.instance.CheckWord(word);
        }
    };
    

    this.doDefault = function doDefault() {
        if (gDialog.ReplaceButton.getAttribute("default") == "true")
            this.Replace(gDialog.ReplaceWordInput.value);
        else if (gDialog.IgnoreButton.getAttribute("default") == "true")
            this.instance.Ignore();
        else if (gDialog.CloseButton.getAttribute("default") == "true")
            this.onClose();    
        return false;
    };
    
    this.EditDictionary = function EditDictionary() {
        if (this.instance.misspelledWord
            && this.instance.personalDictionary) {
            window.openDialog("chrome://komodospellchecker/content/koDictionary.xul",
                              "_blank", "chrome,close,titlebar,modal", "",
                              this.instance.misspelledWord);
        }
    }

    this.Ignore = function Ignore() {
      return this.instance.Ignore();
    }
    this.IgnoreAll = function Ignore() {
      if (this.instance.misspelledWord) {
        if (false && this.instance.personalDictionary) {
            // Not too sure how this works for ignoreWord...
            this.instance.personalDictionary.ignoreWord(this.instance.misspelledWord);
        } else {
            this.skip_words[this.instance.misspelledWord] = true;
        }
      }
      return this.instance.Ignore();
    }

    
    this.onClose = function onClose() {
        try {
        this.CancelSpellCheck();
        } catch(ex) {}
        if (this.instance) {
            this.instance.scimoz.targetStart = 0;
            this.instance.scimoz.targetEnd = this.instance.scimoz.textLength;
        }
        window.close();
    };
    
    // Recheck the page
    this.Recheck = function Recheck() {
        this.instance.currPosition = this.instance.startPosition;
        this.instance.FindNextWord();
    };
    
    this._ReplaceNone = function _ReplaceNone(newWord) {
        this.instance.Advance(newWord.length);
        this.instance.FindNextWord();
    };

    this.Replace = function Replace(newWord) {
        //dump(">> this.Replace\n");
        if (!newWord)
            return;    
        if (this.instance.misspelledWord && this.instance.misspelledWord != newWord) {
            this.instance.Replace(newWord);
        } else {
            this._ReplaceNone(newWord);
        }
        //dump("<< this.Replace\n");
    };
    
    this.ReplaceAll = function ReplaceAll() {
        var newWord = gDialog.ReplaceWordInput.value;
        if (this.instance.misspelledWord && this.instance.misspelledWord != newWord) {
            this.instance.ReplaceAll(newWord);  
        } else {
            this._ReplaceNone(newWord);
        }
    };

    this.SelectLanguage = function SelectLanguage() {
        try {
            var item = gDialog.LanguageMenulist.selectedItem;
            if (item && item.value) {
                var oldDictName = this.instance.spellChecker.dictionary;
                var inst = this.instance;
                inst.spellChecker.dictionary = item.value;
                if (oldDictName != item.value) {
                    // dump("About to change from " + oldDictName + " to " + item.value + "\n");
                    inst.setLastSpellCheckLanguage(inst.koDoc.getEffectivePrefs(), item.value);
                    inst.setLastSpellCheckLanguage(inst.getGlobalPrefs(), item.value);
                    inst.FindNextWord();
                }
            }
        } catch (ex) {
            dump(ex + "\n");
        }
    };
    
    this.SelectSuggestedWord = function SelectSuggestedWord() {
        if (this.AllowSelectWord()) {
            var selectedItem;
            if (gDialog.SuggestedList.selectedItem) {
                var selValue = gDialog.SuggestedList.selectedItem.getAttribute("label");
                gDialog.ReplaceWordInput.value = selValue;
                this.instance.previousReplaceWord = selValue;
            } else {
                gDialog.ReplaceWordInput.value = this.instance.previousReplaceWord;
            }
            this.SetReplaceEnable();
        }
    };
    
    this.SetReplaceEnable = function SetReplaceEnable() {
      //dump(">> SetReplaceEnable\n");
      // Enable "Change..." buttons only if new word is different than misspelled
      var newWord = gDialog.ReplaceWordInput.value;
      var enable = newWord.length > 0 && newWord != this.instance.misspelledWord;
      //dump("SetReplaceEnable: newWord = "
      //     + newWord + ", this.misspelledWord = "
      //     + this.misspelledWord + ", enable = "
      //     + enable + "\n");
      SetElementEnabledById("Replace", enable);
      SetElementEnabledById("ReplaceAll", enable);
      if (enable) {
        gDialog.ReplaceButton.setAttribute("default","true");
        gDialog.IgnoreButton.removeAttribute("default");
      } else {
        gDialog.IgnoreButton.setAttribute("default","true");
        gDialog.ReplaceButton.removeAttribute("default");
      }
      //dump("<< SetReplaceEnable\n");
    };

    this.finishStartup = function finishStartup(obj) {
        try {
          var sc = new KoSpellCheck(this, obj);
          sc.koDoc = obj.view.koDoc;
          sc.view = obj.view;
          sc.FinalInit();
          this.instance = sc;
        } catch(ex) {
          dump(ex + "\n");
          window.close();
          return;
        }
        var scimoz = sc.scimoz;
        var selStart = scimoz.selectionStart;
        var selEnd = scimoz.selectionEnd;
        sc.inSelection = (selStart < selEnd);
        if (!sc.inSelection) {
          selEnd = scimoz.textLength;
          sc.doWrap = (selStart > 0);
        } else {
          sc.doWrap = false;
        }
        // synchronize so the selections are both on white-space
        var lineStartPos = scimoz.positionFromLine(scimoz.lineFromPosition(selStart))
        var text = scimoz.getTextRange(lineStartPos, scimoz.positionAfter(selStart));
        var idx = text.length - 1;
        var ch;
        while (idx >= 0) {
            ch = text[idx];
            idx -= 1;
            if (ch == ' ' || ch == '\t' || ch == '\r') {
                break;
            }
        }
        selStart = lineStartPos + idx + 1;        
        sc.startPosition = sc.currPosition = selStart;
        
        if (selEnd != scimoz.textLength) {
            var lineEndPos = scimoz.getLineEndPosition(scimoz.lineFromPosition(selEnd));
            // This one's always safe because the lineEndPos char is always
            // CR or LF.
            text = scimoz.getTextRange(selEnd, lineEndPos + 1);
            idx = 0;
            while (idx < text.length) {
                ch = text[idx];
                idx += 1;
                if (ch == ' ' || ch == '\t') {
                    break;
                }
            }
        }
        sc.endPosition = selEnd;
        sc.scimozNextStart = null; // Used for continuing
        // force recoloring
        // dump("Colorise from " + sc.startPosition + " to " + sc.endPosition + "\n");
        scimoz.colourise(lineStartPos, sc.endPosition);
        scimoz.searchFlags = scimoz.SCFIND_REGEXP|scimoz.SCFIND_MATCHCASE;
        // We need a healthy delay here on Linux
        setTimeout(function() {
          sc.FindNextWord();
        }, 1000);
    };
    
    // Sort of an API
    this.getSpellChecker = function spellChecker() {
        return this.instance.spellChecker;
    };
    
    this.getPersonalDictionary = function getPersonalDictionary() {
        return this.instance.personalDictionary;
    };
    
    this.getCurrentDictionaryLanguage = function getCurrentDictionaryLanguage() {
        return this.instance.language;
    };
}).apply(ko.extensions.spellchecker);

function spellchecker_Startup() {
    var obj = window.arguments[0];
    var koGlobal = obj.ko;
    if (!('spellcheck_skippedWords' in koGlobal)) {
        koGlobal.spellcheck_skippedWords = {};
    }
    obj.koDoc = obj.view.koDoc;
    obj.scimoz = obj.view.scimoz;
    if (obj.koDoc) {
      var currDocName = obj.koDoc.displayPath;
      if (!(currDocName in koGlobal.spellcheck_skippedWords)) {
        koGlobal.spellcheck_skippedWords[currDocName] = {};
      }
      ko.extensions.spellchecker.skip_words = koGlobal.spellcheck_skippedWords[currDocName];
    } else {
      // Skipped words won't be remembered until the doc has a name
      ko.extensions.spellchecker.skip_words = {};
    }
    ko.extensions.spellchecker.finishStartup(obj);
}
    

if (1) {
//dump("loading edspellcheck.js...");
//dump("ko.extensions.spellchecker = ...")
//dump(ko.extensions.spellchecker + "\n");
//var x = ko.extensions.spellchecker;
//var s = [];
//for (var p in x) {
//    var obj;
//    try { obj = x[p]; } catch(ex) { obj = null; }
//    if (!obj) {
//        s.push(p);
//    } else if (typeof(obj) == "function") {
//        s.push(p + ":function");
//    } else {
//        s.push(p + ":" + obj);
//    }
//    
//}
//dump("ko.extensions.spellchecker.Startup parts = " + s.join(" ") + "\n");
//dump("ko.extensions.spellchecker.Startup = ...")
//dump(ko.extensions.spellchecker.Startup + "\n");
}
