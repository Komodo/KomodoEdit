/* Copyright (c) 2000-2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var log = ko.logging.getLogger("pref.pref-syntax-checking");
var dialog = {};
var currentView;

var languageSetup = {}; // Map language names to functions
var languageInfo = {}; // Map language names to objects
// Make these available to extensions
var cachedAppInfo = {}; // Map languages to whatever.  Avoid hitting appinfo during each session.
var loadContext;
var g_prefset;

var bundleLang = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
function docSyntaxCheckingOnLoad() {
    try {
        if (!('lint' in ko)) { ko.lint = {}; }
        ko.lint.languageSetup = languageSetup;
        ko.lint.languageInfo = languageInfo;
        dialog.lintEOLs = document.getElementById("lintEOLs");
        dialog.lintShowResultsInline = document.getElementById("lintShowResultsInline");
        dialog.lintClearOnTextChange = document.getElementById("lintClearOnTextChange");
        dialog.lintDelay = document.getElementById("lintDelay");
        dialog.editUseLinting = document.getElementById("editUseLinting");
        dialog.langlist = document.getElementById("languageList");
        dialog.deck = document.getElementById("docSyntaxCheckByLang");
        dialog.deckNoLinterFallback = document.getElementById("langSyntaxCheckFallback_NoLinter");
        dialog.genericLinterFallback = document.getElementById("langSyntaxCheckFallback_GenericLinter");
        dialog.html_perl_html_tidy = document.getElementById("lintHTML-CheckWith-Perl-HTML-Tidy");
        dialog.html_perl_html_lint = document.getElementById("lintHTML-CheckWith-Perl-HTML-Lint");
        parent.initPanel();
    } catch(e) {
        log.exception(e);
    }
}

function OnPreferencePageLoading(prefset) {
    g_prefset = prefset;
    loadContext = parent.prefInvokeType;
    pref_lint_doEnabling();
    currentView = getKoObject('views').manager.currentView;
    var languageName;
    dialog.langlist.rebuildMenuTree(loadContext === "view", currentView);
    if (!currentView || !currentView.koDoc) {
        if (loadContext === "project") {
            var project = getKoObject('projects').manager.currentProject;
            var urls = {};
            project.getAllContainedURLs(urls, {});
            //TODO: Get the language name here.
        }
        languageName = dialog.langlist.selection || null;
    } else  {
        // Figure out if there are language-specific prefs we should be showing
        languageName = currentView.koDoc.language;
        dialog.langlist.selection = languageName;
    }
    showLanguageNamePanel(languageName);
}

function OnPreferencePageOK(prefset) {
    if (dialog.deck.selectedPanel === dialog.genericLinterFallback) {
        var languageName = dialog.langlist.selection;
        if (languageName) {
            var linterPrefName = "genericLinter:" + languageName;
            if (!prefset.hasPref(linterPrefName)) {
                // Track changes to this pref.
                getKoObject('lint').addLintPreference(linterPrefName, [languageName]);
            } else if (!prefset.hasPrefHere(linterPrefName)) {
                getKoObject('lint').updateDocLintPreferences(prefset, linterPrefName);
            }
            prefset.setBooleanPref(linterPrefName,
                                   document.getElementById("generic_linter_for_current_language").checked);
        }
    }
    return true;       
}

/* Three parts to having the pref panel for one language working with another language:
 * 1. Add an entry in the _mappedNames object
 * 2. Point languageSetup[aliasLanguage] to the <actualLanguage>_setup function.
 * 3. Update UI in the <actualLanguage>_setup function to reflect prefs for whichever
 *    language we're showing prefs for.
 */
var _mappedNames = {
    "HTML5": "HTML",
    "Node.js": "JavaScript"
};
function getMappedName(languageName) {
    return (languageName in _mappedNames
            ? _mappedNames[languageName]
            : null);
}

function setPanel(langDeck) {
    dialog.deck.selectedPanel.removeAttribute('active');
    dialog.deck.selectedPanel = langDeck;
    dialog.deck.selectedPanel.setAttribute('active', 'true');
}

function showLanguageNamePanel(languageName) {
    var deckID = null;
    if (languageName) {
        if (languageName in languageSetup) {
            languageSetup[languageName](languageName);
        }
        deckID = document.getElementById("langSyntaxCheck-" + languageName);
        if (deckID) {
            setPanel(deckID);
        }
    }
    if (deckID === null) {
        var mappedName = getMappedName(languageName);
        if (mappedName) {
            deckID = document.getElementById("langSyntaxCheck-" + mappedName);
            if (deckID) {
               setPanel(deckID);
                return;
            }
        }
        var descr, linterCID = null, msg;
        if (languageName) {
            linterCID = Components.classes["@activestate.com/koLintService;1"].
                getService(Components.interfaces.koILintService).
                getLinter_CID_ForLanguage(languageName);
        }
        if (!linterCID) {
            setPanel(dialog.deckNoLinterFallback)
            descr = dialog.deckNoLinterFallback;
            descr = descr.firstChild;
            while (descr.firstChild) {
                descr.removeChild(descr.firstChild);
            }
            if (!languageName) {
                languageName = "<unknown>";
            }
            msg = bundleLang.formatStringFromName("Komodo does no syntax-checking on X documents", [languageName], 1);
            var textNode = document.createTextNode(msg);
            descr.appendChild(textNode);
        } else {
            setPanel(dialog.genericLinterFallback);
            descr = dialog.genericLinterFallback;
            var checkbox = document.getElementById("generic_linter_for_current_language");
            checkbox.setAttribute("label",
                                  bundleLang.formatStringFromName("Check syntax for X", [languageName], 1));
            var linterPrefName = "genericLinter:" + languageName;
            
            if (g_prefset.hasPref(linterPrefName)) {
                checkbox.checked = g_prefset.getBooleanPref(linterPrefName);
            } else {
                checkbox.checked = true;
            }
        }
    }
}

function pref_setElementEnabledState(elt, enabled) {
    if (enabled) {
        if (elt.hasAttribute('disabled')) {
            elt.removeAttribute('disabled');
        }
    } else {
        elt.setAttribute('disabled', true);
    }
}

function pref_lint_doEnabling() {
    var enabled = dialog.editUseLinting.checked;
    pref_setElementEnabledState(dialog.lintDelay, enabled);
    pref_setElementEnabledState(dialog.lintEOLs, enabled);
    pref_setElementEnabledState(dialog.lintShowResultsInline, enabled);
    pref_setElementEnabledState(dialog.lintClearOnTextChange, enabled);
}

function changeLanguage(langList) {
    // Give overlays a chance to load.
    setTimeout(showLanguageNamePanel, 0, langList.selection);
}

function common_loadTextboxFromFilepicker(textbox, prompt) {
    var currentValue = textbox.value;
    var defaultDirectory = null, defaultFilename = null;
    if (currentValue) {
        var koFileEx = Components.classes["@activestate.com/koFileEx;1"]
            .createInstance(Components.interfaces.koIFileEx);
        koFileEx.path = currentValue;
        defaultDirectory = koFileEx.dirName;
        defaultFilename = koFileEx.baseName;
    }
    var title = bundleLang.GetStringFromName(prompt);
    var rcpath = ko.filepicker.browseForFile(defaultDirectory,
                                             defaultFilename, title);
    if (rcpath !== null) {
        textbox.value = rcpath;
    }
}

function coffeeScript_setup() {
    if (!('CoffeeScript' in dialog)) {
        dialog.CoffeeScript = {};
        [
         "lint_coffee_script",
         "lint_coffee_failure"].forEach(function(name) {
            dialog.CoffeeScript[name] = document.getElementById(name);
        });
        languageInfo.CoffeeScript = CoffeeScriptInfo();
    }
    languageInfo.CoffeeScript.updateUI();
}

languageSetup.CoffeeScript = coffeeScript_setup;
function CoffeeScriptInfo() {
    return {
      hasCS: null,
      
      updateUI: function() {
            if (this.hasCS === null) {
                var koSysUtils = Components.classes["@activestate.com/koSysUtils;1"].getService(Components.interfaces.koISysUtils);
                var coffeeScript = koSysUtils.Which("coffee");
                this.hasCS = !!coffeeScript;
            }
            var checkbox = dialog.CoffeeScript.lint_coffee_script;
            var failureNode = dialog.CoffeeScript.lint_coffee_failure;
            if (this.hasCS) {
                failureNode.setAttribute("class", "pref_hide");
                checkbox.disabled = false;
            } else {
                checkbox.checked = false;
                checkbox.disabled = true;
                if (!failureNode.firstChild) {
                    var text = bundleLang.GetStringFromName("Cant find CoffeeScript, update the PATH to include it, and restart Komodo");
                    var textNode = document.createTextNode(text);
                    failureNode.appendChild(textNode);
                }
                failureNode.setAttribute("class", "pref_show");
            }
        }
    };
}


function django_setup() {
    // Nothing to do
}

languageSetup.Django = django_setup;        

function htmlSetup(languageName) {
    if (!('HTML' in dialog)) {
        dialog.HTML = {};
        ["lintHTMLTidy",
         "lintHTML_CheckWith_Perl_HTML_Tidy",
         "lintHTML_CheckWith_Perl_HTML_Lint",
         "lintHTMLTidy_Details_vbox",
         "lintHTML5Lib",
         "lint_html5lib_groupbox",
         "lint_html_perl_html_tidy_groupbox",
         "lint_html_perl_html_lint_groupbox",
         "tidy_configpath"                  
         ].forEach(function(name) {
            dialog.HTML[name] = document.getElementById(name);
        });
        languageInfo.HTML = htmlInfo();
    }
    var cachedAppInfo = languageInfo.HTML.cachedAppInfo;
    if (!("Perl" in cachedAppInfo)) {
        setTimeout(function() {
                cachedAppInfo.Perl = {};
                var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Perl;1"].
                        getService(Components.interfaces.koIPerlInfoEx);
                cachedAppInfo.Perl.htmlLint = appInfoEx.haveModules(1, ["HTML::Lint"]);
                cachedAppInfo.Perl.htmlTidy = appInfoEx.haveModules(1, ["HTML::Tidy"]);
                languageInfo.HTML.htmlSetupFinish(languageName);
            }, 100);
    } else {
        languageInfo.HTML.htmlSetupFinish(languageName);
    }
}
languageSetup.HTML = htmlSetup;
function htmlInfo() {
    return {
        cachedAppInfo: {},
        htmlSetupFinish: function(languageName) {
            pref_setElementEnabledState(dialog.HTML.lintHTML_CheckWith_Perl_HTML_Tidy, this.cachedAppInfo.Perl.htmlTidy);
            pref_setElementEnabledState(dialog.HTML.lintHTML_CheckWith_Perl_HTML_Lint, this.cachedAppInfo.Perl.htmlLint);
            dialog.HTML.lint_html5lib_groupbox.collapsed = languageName === "HTML";
            dialog.HTML.lint_html_perl_html_tidy_groupbox.collapsed = languageName === "HTML5";
            dialog.HTML.lint_html_perl_html_lint_groupbox.collapsed = languageName === "HTML5";
        },
        loadTidyConfigFile: function() {
            var textbox = dialog.HTML.tidy_configpath;
            var currentDir = getDirectoryFromTextObject(textbox);
            var file = ko.filepicker.browseForFile(currentDir);
            if (file !== null) {
                textbox.value = file;
            }
        },
        updateHTMLTidySyntaxChecking: function(checkbox) {
            dialog.HTML.lintHTMLTidy_Details_vbox.collapsed = !checkbox.checked;
        },

        __END__: null
    };
}
languageSetup.HTML5 = htmlSetup;

// JavaScript functions

function javaScript_setup(languageName) {
    var djs;
    if (!('JavaScript' in dialog)) {
        djs = dialog.JavaScript = {};
        ["lintJavaScript_SpiderMonkey",
         "lintJavaScriptEnableWarnings",
         "lintJavaScriptEnableStrict",
         "jshintGroupbox",
         "jshintOptions",
         "jslintOptions",
         "jshintPrefsVbox",
         "jslintPrefsVbox",
         "lintWithJSHint",
         "lintWithJSLint",
         "jslint_linter_specific",
         "jslint_linter_chooser",
         "jshint_linter_specific",
         "jshint_linter_chooser",
         "jslint_linter_specific_version"
         ].forEach(function(name) {
            djs[name] = document.getElementById(name);
        });
        languageInfo.JavaScript = javaScriptInfo('JavaScript');
    } else {
        djs = dialog.JavaScript;
    }
    if (!djs.lintJavaScript_SpiderMonkey.checked) {
        pref_setElementEnabledState(djs.lintJavaScriptEnableWarnings, false);
        pref_setElementEnabledState(djs.lintJavaScriptEnableStrict, false);
    } else {
        pref_setElementEnabledState(djs.lintJavaScriptEnableWarnings, true);
        pref_setElementEnabledState(djs.lintJavaScriptEnableStrict, djs.lintJavaScriptEnableWarnings.checked);
    }
    languageInfo.JavaScript.doWarningEnabling(djs.lintWithJSLint);
    languageInfo.JavaScript.doWarningEnabling(djs.lintWithJSHint);
    languageInfo.JavaScript.updateJSLinter_selectedVersionField(djs.jslint_linter_specific.value,
                                                                djs.jslint_linter_specific_version);
}

languageSetup.JavaScript = languageSetup['Node.js'] = javaScript_setup;
function javaScriptInfo(languageName) {
    // languageName could be "JavaScript" or "Node.js"
    // Just use "JavaScript"
    languageName = "JavaScript";
    // IDs for jshint/jslint
    // 0:  jshint; 2: jshint;
    var jslintIds = {
      optionsId: [ 'jshintOptions', 'jslintOptions'],
      linterChooserId: ['jshint_linter_chooser',
                        'jslint_linter_chooser'],
      linterSpecificId: ['jshint_linter_specific',
                        'jslint_linter_specific'],
      linterSpecificVersionId: [null, 
                                'jslint_linter_specific_version'],
      defaultLinterName: ["jshint.js", "fulljslint.js"],
    };

    var getIdxFor_linter_language = function(isJSHint) {
        return (isJSHint ? 0 : 1);
    };
      
    return {        
      launchJSHintOptionGetter: function(isJSHint) {
            var djs = dialog[languageName];
            var currentValues = {};
            var m;
            var pattern = /(\w+)\s*=\s*((?:\[.*?\]|[\w\d]+))/g;
            var idx = getIdxFor_linter_language(isJSHint);
            var currentValuesText = djs[jslintIds.optionsId[idx]].value;
            while (!!(m = pattern.exec(currentValuesText))) {
                var name = m[1];
                var value = m[2];
                if (value[0] === '[') {
                    // stringify this
                    // ["ko","Components","window"]  => "ko, Components, window" for cleaner input.
                    currentValues[name] = value.substring(1, value.length - 1).split(/\s*,\s*/).map(function(s) s.replace(/[\"\']/g, '')).join(", ");
                } else {
                    // Just add the stringified value
                    currentValues[name] = value;
                }
            }
            var path;
            if (djs[jslintIds.linterChooserId[idx]].selectedIndex === 0
                || !(path = djs[jslintIds.linterSpecificId[idx]].value)) {
                var koDirs = Components.classes["@activestate.com/koDirs;1"]
                            .getService(Components.interfaces.koIDirs);
                var osPathSvc = Components.classes["@activestate.com/koOsPath;1"]
                            .getService(Components.interfaces.koIOsPath);
                var parts = [koDirs.supportDir, "lint", "javascript",
                             jslintIds.defaultLinterName[idx]];
                path = osPathSvc.joinlist(parts.length, parts);
            }
            var obj = {
                isJSHint: isJSHint,
                path: path,
                currentValues: currentValues
            };
            window.openDialog("chrome://komodo/content/pref/pref-jshint-options.xul",
                              "_blank",
                              "chrome,modal,titlebar,resizable=yes,centerscreen",
                              obj);
            if (obj.result) {
                var predef = null;
                var newValues = obj.newValues, predef;
                if ('predef' in newValues) {
                    // remove extra quotes, and then reformat
                    predef = newValues.predef.replace(/[\[\]\"\']/g, '').split(/\s*,\s*/);
                    delete newValues.predef;
                }
                var newValuesA = [];
                for (var p in newValues) {
                    newValuesA.push(p + '=' + newValues[p]);
                }
                if (predef) {
                    newValuesA.push('predef=['
                                    + predef.map(function(s) '"' + s + '"').join(',')
                                    + ']');
                }
                djs[jslintIds.optionsId[idx]].value = newValuesA.join(" ");
            }
        },
        
        doWarningEnabling: function(checkbox) {
            var djs = dialog[languageName];
            var isChecked = checkbox.checked;
            switch (checkbox) {
            case djs.lintJavaScript_SpiderMonkey:
                pref_setElementEnabledState(djs.lintJavaScriptEnableWarnings, isChecked);
                pref_setElementEnabledState(djs.lintJavaScriptEnableStrict, isChecked && djs.lintJavaScriptEnableWarnings.checked);
                break;
            case djs.lintJavaScriptEnableWarnings:
                pref_setElementEnabledState(djs.lintJavaScriptEnableStrict, isChecked);
                break;
            case djs.lintWithJSLint:
                pref_setElementEnabledState(djs.jslintOptions, isChecked);
                djs.jslintPrefsVbox.collapsed = !isChecked;
                break;
            case djs.lintWithJSHint:
                pref_setElementEnabledState(djs.jshintOptions, isChecked);
                djs.jshintPrefsVbox.collapsed = !isChecked;
                break;
            }
        },
        updateJSLinter_selectedVersionField: function(path, labelField) {
            var specificText;
            if (!path) {
                specificText = "";
            } else {
                var koFileEx = Components.classes["@activestate.com/koFileEx;1"]
                    .createInstance(Components.interfaces.koIFileEx);
                try {
                    dump("updateJSLinter_selectedVersionField(path:  " + path + ")\n");
                    koFileEx.path = path;
                    if (!koFileEx.exists) {
                        specificText = bundleLang.GetStringFromName("No such file");
                    } else {
                        koFileEx.open('r');
                        var s = koFileEx.read(512, {}, {}).map(function(c) String.fromCharCode(c)).join("");
                        koFileEx.close();
                        var p = /(?:^|\n)\s*\/\/\s*(\d\d\d\d-\d\d-\d\d)/;
                        var m = p.exec(s);
                        if (!m) {
                            // Modern jshint form:
                            // /*! 2.5.10
                            p = /(?:^|\n)\s*(?:\/\/|\/\*)[\s\!]*([\d\.]+)/;
                            m = p.exec(s);
                        }
                        if (m) {
                            specificText = bundleLang.formatStringFromName("Selected Version X", [m[1]], 1);
                        } else {
                            specificText = bundleLang.formatStringFromName("Selected Version X", [bundleLang.GetStringFromName("Unknown")], 1);
                        }
                    }
                } catch(ex) {
                    specificText = bundleLang.formatStringFromName("Trying to get version X", [ex], 1);
                    log.exception(ex, "Failed to read linter file: ");
                }
            }
            labelField.value = specificText;
        },
        
        browseForJSLinter: function(isJSHint) {
            var idx = getIdxFor_linter_language(isJSHint);
            var djs = dialog[languageName];
            var jslint_linter_specific = djs[jslintIds.linterSpecificId[idx]];
            var currentPath = jslint_linter_specific.value;
            var path = ko.filepicker.browseForExeFile(null, currentPath || "");
            if (path) {
                jslint_linter_specific.value = path;
                djs[jslintIds.linterChooserId[idx]].selectedIndex = 1;
                if (!isJSHint) {
                    this.updateJSLinter_selectedVersionField(path,
                                                             djs[jslintIds.linterSpecificVersionId[idx]]);
                }
            }
        },
        
        handleChangedJSLinter: function(isJSHint) {
            var idx = getIdxFor_linter_language(isJSHint);
            var djs = dialog[languageName];
            var jslint_linter_specific = djs[jslintIds.linterSpecificId[idx]];
            var selectedIndex = jslint_linter_specific.value ? 1 : 0;
            djs[jslintIds.linterChooserId[idx]].selectedIndex = selectedIndex;
            this.updateJSLinter_selectedVersionField(jslint_linter_specific.value,
                                                     djs[jslintIds.linterSpecificVersionId[idx]]);
        },
        
        __EOD__: null
    };
}

function Less_setup() {
    if (!('Less' in dialog)) {
        dialog.Less = {};
        [
         "lessLinterType",
         "lessDefaultInterpreter",
         "browseLess"].forEach(function(name) {
            dialog.Less[name] = document.getElementById(name);
        });
        languageInfo.Less = Less_Info();
    }
    languageInfo.Less.populateInterpreters();
    languageInfo.Less.updateUI((dialog.Less.lessLinterType.selectedItem || {value:"builtin"}).value);
}

languageSetup.Less = Less_setup;
function Less_Info() {
    return {
      updateLessLinterType: function(event) {
        if (event.originalTarget.nodeName != "radio") {
            // Ignore these
            return;
        }
        var radioButtonValue = event.originalTarget.value;
        this.updateUI(radioButtonValue);
      },
      
      updateUI: function(radioButtonValue) {
        var disabled = radioButtonValue !== "path";
        dialog.Less.lessDefaultInterpreter.disabled = disabled;
        dialog.Less.browseLess.disabled = disabled;
      },
      
      load_Less_Executable: function() {
        loadExecutableIntoInterpreterList("lessDefaultInterpreter");
      },
      
      populateInterpreters: function() {
        var availInterpList = dialog.Less.lessDefaultInterpreter;
    
        availInterpList.removeAllItems();
        var selectedIndex = 0;
        var findOnPathLabel = bundleLang.GetStringFromName("findOnPath.label");
        availInterpList.appendItem(findOnPathLabel, '');
        var preferredPath = g_prefset.getStringPref("lessDefaultInterpreter");
        if (preferredPath && preferredPath !== findOnPathLabel) {
            availInterpList.appendItem(preferredPath, preferredPath);
            selectedIndex = 1;
        }
        
        // get a list of installed Less interpreters
        var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
            getService(Components.interfaces.koISysUtils);
        var availInterps = sysUtils.WhichAll("lessc", {});
        availInterps = availInterps.filter(function(less_path)
                                                less_path != preferredPath);
        availInterps.forEach(function(less_path) {
            availInterpList.appendItem(less_path, less_path);
        });
        dialog.Less.lessDefaultInterpreter.selectedIndex = selectedIndex;
      }
    };
}


function perl_setup() {
    if (!('Perl' in dialog)) {
        dialog.Perl = {};
        ["perl_lintOption",
         "perl_lintOption_perlCriticLevel",
         "perl_lintOptions_perlCriticBox_label",
         "perl_lintOption_perlCriticEnableNote",
         "perlcritic_vbox_rcfile",
         "perlcritic_checking_rcfile",
         ].forEach(function(name) {
            dialog.Perl[name] = document.getElementById(name);
        });
        languageInfo.Perl = perlInfo();
    }
    var perlCriticStatusByExecutable = languageInfo.Perl.perlCriticStatusByExecutable;
    var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Perl;1"].
        getService(Components.interfaces.koIPerlInfoEx);
    var perlExe = appInfoEx.executablePath;
    if (!(perlExe in perlCriticStatusByExecutable)) {
        setTimeout(function() {
                var res = appInfoEx.isPerlCriticInstalled(/*forceCheck=*/true);
                perlCriticStatusByExecutable[perlExe] = res;
                languageInfo.Perl.setPerlCriticSection(res);
        }, 300);
    } else {
        languageInfo.Perl.setPerlCriticSection(perlCriticStatusByExecutable[perlExe]);
    }
}

languageSetup.Perl = perl_setup;

function perlInfo() {
    return {
      perlCriticStatusByExecutable: {},
            
      setPerlCriticSection: function(havePerlCritic) {
            dialog.Perl.perl_lintOptions_perlCriticBox_label.disabled = !havePerlCritic;
            dialog.Perl.perl_lintOption_perlCriticLevel.disabled = !havePerlCritic;
            if (havePerlCritic) {
                dialog.Perl.perl_lintOption_perlCriticEnableNote.setAttribute('collapsed', true);
                this.onPerlCriticLevelChanged(dialog.Perl.perl_lintOption_perlCriticLevel);
            } else {
                dialog.Perl.perl_lintOption_perlCriticEnableNote.removeAttribute('collapsed');
                dialog.Perl.perlcritic_vbox_rcfile.setAttribute('collapsed', true);
            }
        },
        loadPerlcriticRcfile: function() {
            var textbox = dialog.Perl.perlcritic_checking_rcfile;
            var prompt = bundleLang.GetStringFromName("Find a .perlcriticrc file");
            return common_loadTextboxFromFilepicker(textbox, prompt);
        },
        onPerlCriticLevelChanged: function(perlCriticLevelMenuList) {
            var data = perlCriticLevelMenuList.selectedItem.getAttribute("data");
            dialog.Perl.perlcritic_vbox_rcfile.setAttribute('collapsed', data == "off");
            
        },
        __EOD__:null
    };
}

function python_setup() {
    if (!('Python' in dialog)) {
        dialog.Python = {};
        [
         "lint_python_with_pychecker",
         "lint_python_with_pep8",
         "lint_python_with_pylint",
         "lint_python_with_pyflakes",
         "pychecker_browse_rcfile",
         "pychecker_browse_wrapper_location",
         "pychecker_checking_rcfile",
         "pychecker_dangerous",
         "pychecker_info_vbox",
         "pychecker_failure",
         "pychecker_wrapper_location",
         "pyflakes_failure",
         "pylint_browse_rcfile",
         "pylint_checking_rcfile",
         "pylint_failure",
         "pylint_checking_vbox_rcfile",
         "pep8_browse_rcfile",
         "pep8_checking_rcfile",
         "pep8_failure",
         "pep8_checking_vbox_rcfile",
         "python_lintOption"
         ].forEach(function(name) {
            dialog.Python[name] = document.getElementById(name);
        });
        languageInfo.Python = pythonInfo();
    }
    var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Python;1"].
        getService(Components.interfaces.koIAppInfoEx);
    var pythonExe = appInfoEx.executablePath;
    var pylintStatusByExecutable = languageInfo.Python.pylintStatusByExecutable;
    var pep8StatusByExecutable = languageInfo.Python.pep8StatusByExecutable;
    var pyflakesStatusByExecutable = languageInfo.Python.pyflakesStatusByExecutable;
    if (!(pythonExe in pylintStatusByExecutable)
        || !(pythonExe in pep8StatusByExecutable)
        || !(pythonExe in pyflakesStatusByExecutable)) {
        setTimeout(function() {
                var res;
                try {
                    if (!(pythonExe in pylintStatusByExecutable)) {
                        res = appInfoEx.haveModules(1, ['pylint']);
                        pylintStatusByExecutable[pythonExe] = res;
                    }
                    if (!(pythonExe in pep8StatusByExecutable)) {
                        pep8StatusByExecutable[pythonExe] = appInfoEx.haveModules(1, ['pep8']);
                    }
                    if (!(pythonExe in pyflakesStatusByExecutable)) {
                        res = null;
                        try {
                            res = sysUtils.Which("pyflakes");
                        } catch(ex) {
                            log.debug("which(pyflakes) failed: " + ex);
                        }
                        if (!res) {
                            res = appInfoEx.haveModules(1, ['pyflakes']);
                        }
                        pyflakesStatusByExecutable[pythonExe] = res;
                    }
                    languageInfo.Python.updateUI(pythonExe);
                } catch(e) {
                    log.exception(ex, "python_setup failed in setTimeout")
                }
            }, 300);
    } else {
        languageInfo.Python.updateUI(pythonExe);
    }
}
languageSetup.Python = python_setup;
function pythonInfo() {
    return {
        pylintStatusByExecutable: {},
        pep8StatusByExecutable: {},
        pyflakesStatusByExecutable: {},
        
        _updateFailureBox: function(failureNode, pythonExe, linterName) {
            if (!pythonExe) {
                failureNode.setAttribute("class", "pref_hide");
            } else {
                var text = bundleLang.formatStringFromName("The current Python instance X doesnt have X installed", [pythonExe, linterName], 2);
                var textNode = document.createTextNode(text);
                while (failureNode.firstChild) {
                    failureNode.removeChild(failureNode.firstChild);
                }
                failureNode.appendChild(textNode);
                failureNode.setAttribute("class", "pref_show");
            }
        },
    
        updateUI: function(pythonExe) {
            // Update UI for pylint
            var checkbox = dialog.Python.lint_python_with_pylint;
            var failureNode = dialog.Python.pylint_failure;
            if (pythonExe && this.pylintStatusByExecutable[pythonExe]) {
                failureNode.setAttribute("class", "pref_hide");
                checkbox.disabled = false;
            } else {
                checkbox.checked = false;
                checkbox.disabled = true;
                this._updateFailureBox(failureNode, pythonExe, "pylint");
            }
            this.onTogglePylintChecking(checkbox);
            
            // pep8
            var checkbox = dialog.Python.lint_python_with_pep8;
            var failureNode = dialog.Python.pep8_failure;
            if (pythonExe && this.pep8StatusByExecutable[pythonExe]) {
                failureNode.setAttribute("class", "pref_hide");
                checkbox.disabled = false;
            } else {
                checkbox.checked = false;
                checkbox.disabled = true;
                this._updateFailureBox(failureNode, pythonExe, "pep8");
            }
            this.onTogglePep8Checking(checkbox);
            
            // pyflakes
            checkbox = dialog.Python.lint_python_with_pyflakes;
            failureNode = dialog.Python.pyflakes_failure;
            if (pythonExe && this.pyflakesStatusByExecutable[pythonExe]) {
                checkbox.disabled = false;
            } else {
                checkbox.checked = false;
                checkbox.disabled = true;
                this._updateFailureBox(failureNode, pythonExe, "pyflakes");
            }
            
            // Update UI for pychecker
            checkbox = dialog.Python.lint_python_with_pychecker;
            if (checkbox.checked && !dialog.Python.pychecker_wrapper_location.value) {
                
                var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
                    getService(Components.interfaces.koISysUtils);
                var path = sysUtils.Which("pychecker");
                if (path) {
                    dialog.Python.pychecker_wrapper_location.value = path;
                }
            }
            this.onTogglePycheckerChecking(checkbox);
        },
            
        onTogglePylintChecking: function(checkbox) {
            dialog.Python.pylint_checking_vbox_rcfile.collapsed = !checkbox.checked;
        },
            
        onTogglePep8Checking: function(checkbox) {
            dialog.Python.pep8_checking_vbox_rcfile.collapsed = !checkbox.checked;
        },

        onTogglePycheckerChecking: function(checkbox) {
            var pycheckerEnabled = checkbox.checked;
            dialog.Python.pychecker_info_vbox.collapsed = !pycheckerEnabled;
            this.updatePycheckerPathStatus();
            var pychecker_dangerous = dialog.Python.pychecker_dangerous;
            if (pycheckerEnabled) {
                pychecker_dangerous.setAttribute("class", "pref_show");
            } else {
                pychecker_dangerous.setAttribute("class", "pref_hide");
            }
        },
        
        updatePycheckerPathStatus: function() {
            var failureNode = dialog.Python.pychecker_failure;
            if (dialog.Python.lint_python_with_pychecker.checked) {
                var hasPath = dialog.Python.pychecker_wrapper_location.value.length > 0;
                if (hasPath) {
                    failureNode.setAttribute("class", "pref_hide");
                } else {
                    failureNode.setAttribute("class", "pref_show");
                }
            } else {
                failureNode.setAttribute("class", "pref_hide");
            }
        },
    
        loadTextboxFromFilepicker: function(eltID, prompt) {
           return common_loadTextboxFromFilepicker(dialog.Python[eltID], prompt);
        },
       
        loadPylintRcfile: function() {
            this.loadTextboxFromFilepicker("pylint_checking_rcfile",
                                           "Find a .pylintrc file");
        },
       
        loadPep8Rcfile: function() {
            this.loadTextboxFromFilepicker("pep8_checking_rcfile",
                                           "Find a pep8 config file");
        },

        loadPycheckerRcFile: function() {
            this.loadTextboxFromFilepicker("pychecker_checking_rcfile",
                                           "Find a .pycheckrc file");
        },
        
        loadPycheckerWrapperFile: function() {
            this.loadTextboxFromFilepicker("pychecker_wrapper_location",
                                           "Find a pychecker script");
            this.updatePycheckerPathStatus();
        },

        __EOD__:null
    };
}

function python3_setup() {
    if (!('Python3' in dialog)) {
        dialog.Python3 = {};
        [
         "lint_python3_with_pychecker3",
         "lint_python3_with_pylint3",
         "lint_python3_with_pep83",
         "lint_python3_with_pyflakes3",
         "pychecker3_browse_rcfile",
         "pychecker3_browse_wrapper_location",
         "pychecker3_checking_rcfile",
         "pychecker3_dangerous",
         "pychecker3_info_vbox",
         "pychecker3_failure",
         "pychecker3_wrapper_location",
         "pyflakes3_failure",
         "pylint3_browse_rcfile",
         "pylint3_checking_rcfile",
         "pylint3_failure",
         "pylint3_checking_vbox_rcfile",
         "pep83_browse_rcfile",
         "pep83_checking_rcfile",
         "pep83_failure",
         "pep83_checking_vbox_rcfile",
         "python3_lintOption"
         ].forEach(function(name) {
            dialog.Python3[name] = document.getElementById(name);
        });
        languageInfo.Python3 = python3Info();
    }
    var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Python3;1"].
        getService(Components.interfaces.koIAppInfoEx);
    var python3Exe = appInfoEx.executablePath;
    var pylint3StatusByExecutable = languageInfo.Python3.pylint3StatusByExecutable;
    var pep83StatusByExecutable = languageInfo.Python3.pep83StatusByExecutable;
    var pyflakes3StatusByExecutable = languageInfo.Python3.pyflakes3StatusByExecutable;
    if (!(python3Exe in pylint3StatusByExecutable)
        || !(python3Exe in pep83StatusByExecutable)
        || !(python3Exe in pyflakes3StatusByExecutable)) {
        setTimeout(function() {
                var res;
                try {
                    if (!(python3Exe in pylint3StatusByExecutable)) {
                        res = appInfoEx.haveModules(1, ['pylint']);
                        pylint3StatusByExecutable[python3Exe] = res;
                    }
                    if (!(python3Exe in pep83StatusByExecutable)) {
                        pep83StatusByExecutable[python3Exe] = appInfoEx.haveModules(1, ['pep8']);
                    }
                    if (!(python3Exe in pyflakes3StatusByExecutable)) {
                        res = appInfoEx.haveModules(1, ['pyflakes']);
                        pyflakes3StatusByExecutable[python3Exe] = res;
                    }
                    languageInfo.Python3.updateUI(python3Exe);
                } catch(ex) {
                    log.exception(ex, "python3_setup failed in setTimeout")
                }
            }, 300);
    } else {
        languageInfo.Python3.updateUI(python3Exe);
    }
}
languageSetup.Python3 = python3_setup;
function python3Info() {
    return {
        pylint3StatusByExecutable: {},
        pep83StatusByExecutable: {},
        pyflakes3StatusByExecutable: {},
        
        _updateFailureBox: function(failureNode, python3Exe, linterName) {
            if (!python3Exe) {
                failureNode.setAttribute("class", "pref_hide");
            } else {
                var text = bundleLang.formatStringFromName("The current Python3 instance X doesnt have X installed", [python3Exe, linterName], 2);
                var textNode = document.createTextNode(text);
                while (failureNode.firstChild) {
                    failureNode.removeChild(failureNode.firstChild);
                }
                failureNode.appendChild(textNode);
                failureNode.setAttribute("class", "pref_show");
            }
        },
    
        updateUI: function(python3Exe) {
            // Update UI for pylint3
            var checkbox = dialog.Python3.lint_python3_with_pylint3;
            var failureNode = dialog.Python3.pylint3_failure;
            if (python3Exe && this.pylint3StatusByExecutable[python3Exe]) {
                failureNode.setAttribute("class", "pref_hide");
                checkbox.disabled = false;
            } else {
                checkbox.checked = false;
                checkbox.disabled = true;
                this._updateFailureBox(failureNode, python3Exe, "pylint");
            }
            this.onTogglePylint3Checking(checkbox);
            
            // pep8
            var checkbox = dialog.Python3.lint_python3_with_pep83;
            var failureNode = dialog.Python3.pep83_failure;
            if (python3Exe && this.pep83StatusByExecutable[python3Exe]) {
                failureNode.setAttribute("class", "pref_hide");
                checkbox.disabled = false;
            } else {
                checkbox.checked = false;
                checkbox.disabled = true;
                this._updateFailureBox(failureNode, python3Exe, "pep8");
            }
            this.onTogglePep83Checking(checkbox);
            
            // pyflakes3
            checkbox = dialog.Python3.lint_python3_with_pyflakes3;
            failureNode = dialog.Python3.pyflakes3_failure;
            if (python3Exe && this.pyflakes3StatusByExecutable[python3Exe]) {
                checkbox.disabled = false;
            } else {
                checkbox.checked = false;
                checkbox.disabled = true;
                this._updateFailureBox(failureNode, python3Exe, "pyflakes");
            }
            
            // Update UI for pychecker3
            checkbox = dialog.Python3.lint_python3_with_pychecker3;
            if (checkbox.checked && !dialog.Python3.pychecker3_wrapper_location.value) {
                
                var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
                    getService(Components.interfaces.koISysUtils);
                var path = sysUtils.Which("pychecker3");
                if (path) {
                    dialog.Python3.pychecker3_wrapper_location.value = path;
                }
            }
            this.onTogglePychecker3Checking(checkbox);
        },
            
        onTogglePylint3Checking: function(checkbox) {
            dialog.Python3.pylint3_checking_vbox_rcfile.collapsed = !checkbox.checked;
        },
        onTogglePep83Checking: function(checkbox) {
            dialog.Python3.pep83_checking_vbox_rcfile.collapsed = !checkbox.checked;
        },
        onTogglePychecker3Checking: function(checkbox) {
            var pychecker3Enabled = checkbox.checked;
            dialog.Python3.pychecker3_info_vbox.collapsed = !pychecker3Enabled;
            this.updatePychecker3PathStatus();
            var pychecker3_dangerous = dialog.Python3.pychecker3_dangerous;
            if (pychecker3Enabled) {
                pychecker3_dangerous.setAttribute("class", "pref_show");
            } else {
                pychecker3_dangerous.setAttribute("class", "pref_hide");
            }
        },
        
        updatePychecker3PathStatus: function() {
            var failureNode = dialog.Python3.pychecker3_failure;
            if (dialog.Python3.lint_python3_with_pychecker3.checked) {
                var hasPath = dialog.Python3.pychecker3_wrapper_location.value.length > 0;
                if (hasPath) {
                    failureNode.setAttribute("class", "pref_hide");
                } else {
                    failureNode.setAttribute("class", "pref_show");
                }
            } else {
                failureNode.setAttribute("class", "pref_hide");
            }
        },
    
        loadTextboxFromFilepicker: function(eltID, prompt) {
           return common_loadTextboxFromFilepicker(dialog.Python3[eltID], prompt);
        },
       
        loadPylint3Rcfile: function() {
            this.loadTextboxFromFilepicker("pylint3_checking_rcfile",
                                           "Find a .pylintrc file");
        },
       
        loadPep83Rcfile: function() {
            this.loadTextboxFromFilepicker("pep83_checking_rcfile",
                                           "Find a pep8 config file");
        },

        loadPychecker3RcFile: function() {
            this.loadTextboxFromFilepicker("pychecker3_checking_rcfile",
                                           "Find a .pycheckrc file");
        },
        
        loadPychecker3WrapperFile: function() {
            this.loadTextboxFromFilepicker("pychecker3_wrapper_location",
                                           "Find a pychecker script");
            this.updatePychecker3PathStatus();
        },

        __EOD__:null
    };
}

function SCSS_setup() {
    if (!('SCSS' in dialog)) {
        dialog.SCSS = {};
        [
         "scssLinterType",
         "scssDefaultInterpreter",
         "browse_SCSS"].forEach(function(name) {
            dialog.SCSS[name] = document.getElementById(name);
        });
        languageInfo.SCSS = SCSS_Info('SCSS', 'scss');
    }
    languageInfo.SCSS.populateInterpreters();
    languageInfo.SCSS.updateUI((dialog.SCSS.scssLinterType.selectedItem || {value:"builtin"}).value);
}
languageSetup.SCSS = SCSS_setup;

function Sass_setup() {
    if (!('Sass' in dialog)) {
        dialog.Sass = {};
        [
         "sassLinterType",
         "sassDefaultInterpreter",
         "browse_Sass"].forEach(function(name) {
            dialog.Sass[name] = document.getElementById(name);
        });
        languageInfo.Sass = SCSS_Info('Sass', 'sass'); // Note overload
    }
    languageInfo.Sass.populateInterpreters();
    languageInfo.Sass.updateUI((dialog.Sass.sassLinterType.selectedItem || {value:"builtin"}).value);
}
languageSetup.Sass = Sass_setup;

function SCSS_Info(key, cmd) {
    var interpreterPref = cmd + "DefaultInterpreter";
    var browseButtonId = 'browse_' + key;
    return {
      updateLinterType: function(event) {
        if (event.originalTarget.nodeName != "radio") {
            // Ignore these
            return;
        }
        var radioButtonValue = event.originalTarget.value;
        this.updateUI(radioButtonValue);
      },
      
      updateUI: function(radioButtonValue) {
        var disabled = radioButtonValue !== "path";
        dialog[key][browseButtonId].disabled = disabled;
      },
      
      loadExecutable: function() {
        loadExecutableIntoInterpreterList(interpreterPref);
      },
      
      populateInterpreters: function() {
        var availInterpList = dialog[key][interpreterPref];
    
        availInterpList.removeAllItems();
        var selectedIndex = -1;
        var findOnPathLabel = bundleLang.GetStringFromName("findOnPath.label");
        availInterpList.appendItem(findOnPathLabel, '');
        var preferredPath = g_prefset.getStringPref(interpreterPref);
        if (preferredPath && preferredPath !== findOnPathLabel) {
            availInterpList.appendItem(preferredPath, preferredPath);
            selectedIndex = 1;
        }
        
        // get a list of installed SCSS interpreters (where Ruby is available)
        var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
            getService(Components.interfaces.koISysUtils);
        var osPathSvc = Components.classes['@activestate.com/koOsPath;1'].
            getService(Components.interfaces.koIOsPath);
        var interpsWithRuby, availInterps = sysUtils.WhichAll(cmd, {});
        if (availInterps.length) {
            var ext = osPathSvc.getExtension(availInterps[0]);
            interpsWithRuby = availInterps.filter(function(scss_path) {
                if (scss_path == preferredPath) {
                    return false;
                }
                var dirName = osPathSvc.dirname(scss_path);
                return osPathSvc.exists(osPathSvc.join(dirName, "ruby") + ext);
            });
            // populate the tree listing them
            interpsWithRuby.forEach(function(path) {
                    availInterpList.appendItem(path, path);
            });
        } else {
            interpsWithRuby = [];
        }
        // If dirname(%ruby)/scss exists and isn't in PATH, add it too.
        var rubyPrefExecutable = null;
        var rubyExecutable = parent.hPrefWindow.prefset.getStringPref('rubyDefaultInterpreter');
        if (rubyExecutable) {
            rubyPrefExecutable = osPathSvc.join(osPathSvc.dirname(rubyExecutable), cmd) + osPathSvc.getExtension(rubyExecutable);
            if (!osPathSvc.exists(rubyPrefExecutable)) {
                rubyPrefExecutable = null;
            }
        }
        if (rubyPrefExecutable
            && interpsWithRuby.indexOf(rubyPrefExecutable) === -1
            && rubyPrefExecutable != preferredPath) {
            availInterpList.appendItem(rubyPrefExecutable, rubyPrefExecutable);
            if (selectedIndex === -1) {
                selectedIndex = interpsWithRuby.length + 1;
            }
        } else if (selectedIndex === -1) {
            // Go with the first item, or 'find-on-path'
            selectedIndex = interpsWithRuby.length ? 1 : 0;
        }
        dialog[key][interpreterPref].selectedIndex = selectedIndex;
      }
    };
}
      

