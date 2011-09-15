/* Copyright (c) 2000-2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var log = ko.logging.getLogger("pref.pref-syntax-checking");
var dialog = {};
var currentView;

var languageSetup = {}; // Map language names to functions
var languageInfo = {}; // Map language names to objects
var cachedAppInfo = {}; // Map languages to whatever.  Avoid hitting appinfo during each session.
var loadContext;
var g_prefset;

var bundleLang = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
function docSyntaxCheckingOnLoad() {
    try {
        dialog.lintEOLs = document.getElementById("lintEOLs");
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
    currentView = parent.opener.window.ko.views.manager.currentView;
    var languageName;
    dialog.langlist.rebuildMenuTree(loadContext == "view", currentView);
    if (!currentView || !currentView.koDoc) {
        if (loadContext == "project") {
            var project = parent.opener.ko.projects.manager.currentProject;
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
    if (dialog.deck.selectedPanel == dialog.genericLinterFallback) {
        var languageName = dialog.langlist.selection;
        if (languageName) {
            var linterPrefName = "genericLinter:" + languageName;
            if (!prefset.hasPref(linterPrefName)) {
                // Track changes to this pref.
                parent.opener.ko.lint.addLintPreference(linterPrefName, [languageName]);
            } else if (!prefset.hasPrefHere(linterPrefName)) {
                parent.opener.ko.lint.updateDocLintPreferences(prefset, linterPrefName);
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
}
function getMappedName(languageName) {
    return (languageName in _mappedNames
            ? _mappedNames[languageName]
            : null);
}

function showLanguageNamePanel(languageName) {
    var deckID = null;
    if (languageName) {
        if (languageName in languageSetup) {
            languageSetup[languageName](languageName);
        }
        deckID = document.getElementById("langSyntaxCheck-" + languageName);
        if (deckID) {
            dialog.deck.selectedPanel = deckID;
        }
    }
    if (deckID === null) {
        var mappedName = getMappedName(languageName);
        if (mappedName) {
            deckID = document.getElementById("langSyntaxCheck-" + mappedName);
            if (deckID) {
                dialog.deck.selectedPanel = deckID;
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
            descr = dialog.deck.selectedPanel = dialog.deckNoLinterFallback;
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
            descr = dialog.deck.selectedPanel = dialog.genericLinterFallback;
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
}

function changeLanguage(langList) {
    showLanguageNamePanel(langList.selection);
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
            dialog.HTML.lint_html5lib_groupbox.collapsed = languageName == "HTML";
            dialog.HTML.lint_html_perl_html_tidy_groupbox.collapsed = languageName == "HTML5";
            dialog.HTML.lint_html_perl_html_lint_groupbox.collapsed = languageName == "HTML5";
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
         "jshintBrutalMode",
         "jshintGroupbox",
         "jshintOptions",
         "jslintBrutalMode",
         "jslintGoodPartsButton",
         "jslintOptions",
         "jshintPrefsVbox",
         "jslintPrefsVbox",
         "lintWithJSHint",
         "lintWithJSLint"
         ].forEach(function(name) {
            djs[name] = document.getElementById(name);
        });
        languageInfo.JavaScript = javaScriptInfo();
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
    if (languageName === "JavaScript") {
        djs.jshintGroupbox.removeAttribute("collapsed");
        languageInfo.JavaScript.doWarningEnabling(djs.lintWithJSHint);
    } else {
        //  (languageName === "Node.js") {
        djs.jshintGroupbox.setAttribute("collapsed", "true");
    }
}

languageSetup.JavaScript = javaScript_setup;

function javaScriptInfo() {
    return {
        goodPartsFactorySettings: {
            white: "true",
            indent: "4",
            onevar: "true",
            'undef': "true",
            cap: "true",
            nomen: "true",
            regexp: "true",
            plusplus: "true",
            bitwise: "true"
        },

        otherStrictSettings: {
            strict: "true",
            passfail: "true",
            browser: "false",
            devel: "false",
            rhino: "false",
            widget: "false",
            windows: "false",
            'debug': "false",
            evil: "false",
            forin: "false",
            subscript: "false",
            'continue': "false",
            css: "false",
            htmlCase: "false",
            on: "false",
            fragment: "false",
            es5: "false" 
        },

        updateSettings : function(optName, optValue, settingNames, settings) {
            if (settingNames.indexOf(optName) === -1) {
                settingNames.push(optName);
            }
            settings[optName] = optValue;
        },

        setCurrentSettings: function (text, settingNames, settings) {
            var i, idx, opt, optName, optValue;
            var options = text.split(/\s+/);
            for (i = 0; i < options.length; i++) {
                opt = options[i];
                idx = opt.indexOf("=");
                if (idx >= 0) {
                    optName = opt.substr(0, idx);
                    optValue = opt.substr(idx + 1);
                    this.updateSettings(optName, optValue, settingNames, settings);
                } else {
                    settingNames.push(opt);
                }
            }
        },

        addSettings: function(factorySettings, settingNames, settings) {
            var optName, optValue;
            for (optName in factorySettings) {
                optValue = factorySettings[optName].toString();
                this.updateSettings(optName, optValue, settingNames, settings);
            }
        },

        addParts: function(includeOtherStrictSettings) {
            var optName, i, idx, name, newTextParts;
            var textField = dialog.JavaScript.jslintOptions;
            var currentSettings = {};
            var currentSettingNames = [];
            var text = textField.value;
            this.setCurrentSettings(text, currentSettingNames, currentSettings);
            this.addSettings(this.goodPartsFactorySettings, currentSettingNames, currentSettings);
            if (includeOtherStrictSettings) {
                this.addSettings(this.otherStrictSettings, currentSettingNames, currentSettings);
            } else {
                // Remove any factory strict settings from the text view
                for (optName in this.otherStrictSettings) {
                    idx = currentSettingNames.indexOf(optName);
                    if (idx > -1 && currentSettings[optName] === this.otherStrictSettings[optName]) {
                        currentSettingNames.splice(idx, 1);
                    }
                }
            }
            newTextParts = currentSettingNames.map(function (name) {
                if (name in currentSettings) {
                    return name + "=" + currentSettings[name];
                } else {
                    return name;
                }
            });
            textField.value = newTextParts.join(" ");
        },

        addGoodParts: function() {
            this.addParts(false);
        },

        addAllOptions: function() {
            this.addParts(true);
        },

        allJSHintStrictSettings: {
            // adsafe     : true, // if ADsafe should be enforced
            asi: "false", // true if automatic semicolon insertion should be tolerated
            bitwise    : "true", // if bitwise operators should not be allowed
            boss       : "true", // if advanced usage of assignments and == should be allowed
            browser    : "false", // if the standard browser globals should be predefined
            cap        : "false", // if upper case HTML should be allowed
            couch      : "false", // if CouchDB globals should be predefined
            css        : "false", // if CSS workarounds should be tolerated
            curly      : "true", // if curly braces around blocks should be required (even in if/for/while)
            debug      : "false", // if debugger statements should be allowed
            devel      : "false", // if logging should be allowed (console, alert, etc.)
            eqeqeq     : "true", // if === should be required
            es5        : "false", // if ES5 syntax should be allowed
            evil       : "false", // if eval should be allowed
            forin      : "true", // if for in statements must filter
            fragment   : "false", // if HTML fragments should be allowed
            immed      : "true", // if immediate invocations must be wrapped in parens
            jquery     : "false", // if jQuery globals should be predefined
            latedef    : "true", // if the use before definition should not be tolerated
            laxbreak   : "false", // if line breaks should not be checked
            loopfunc   : "false", // if functions should be allowed to be defined within loops
            newcap     : "true", // if constructor names must be capitalized
            noarg      : "true", // if arguments.caller and arguments.callee should be disallowed
            node       : "false", // if the Node.js environment globals should be predefined
            noempty    : "false", // if empty blocks should be disallowed
            nonew      : "false", // if using `new` for side-effects should be disallowed
            nomen      : "false", // if names should be checked
            on         : "true", // if HTML event handlers should be allowed
            onevar     : "false", // if only one var statement per function should be allowed
            passfail   : "true", // if the scan should stop on first error
            plusplus   : "true", // if increment/decrement should not be allowed
            regexp     : "true", // if the . should not be allowed in regexp literals
            rhino      : "false", // if the Rhino environment globals should be predefined
            undef      : "true", // if variables should be declared before used
            safe       : "true", // if use of some browser features should be restricted
            shadow     : "false", // if variable shadowing should be tolerated
            windows    : "false", // if MS Windows-specific globals should be predefined
            strict     : "true", // require the "use strict"; pragma
            sub        : "false", // if all forms of subscript notation are tolerated
            white      : "true", // if strict whitespace rules apply
            widget     : "false"  // if the Yahoo Widgets globals should be predefined
        },


        addAllJSHintOptions: function() {
            var optName, i, idx, name, newTextParts;
            var textField = dialog.JavaScript.jshintOptions;
            var currentSettings = {};
            var currentSettingNames = [];
            var text = textField.value;
            this.setCurrentSettings(text, currentSettingNames, currentSettings);
            this.addSettings(this.allJSHintStrictSettings, currentSettingNames, currentSettings);
            newTextParts = currentSettingNames.map(function (name) {
                if (name in currentSettings) {
                    return name + "=" + currentSettings[name];
                } else {
                    return name;
                }
            });
            textField.value = newTextParts.join(" ");
        },
        
        doWarningEnabling: function(checkbox) {
            var djs = dialog.JavaScript;
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
                pref_setElementEnabledState(djs.jslintGoodPartsButton, isChecked);
                pref_setElementEnabledState(djs.jslintBrutalMode, isChecked);
                pref_setElementEnabledState(djs.jslintOptions, isChecked);
                djs.jslintPrefsVbox.collapsed = !isChecked;
                break;
            case djs.lintWithJSHint:
                pref_setElementEnabledState(djs.jshintBrutalMode, isChecked);
                pref_setElementEnabledState(djs.jshintOptions, isChecked);
                djs.jshintPrefsVbox.collapsed = !isChecked;
                break;
            }
        },
        __EOD__: null
    };
}
languageSetup["Node.js"] = javaScript_setup;

function perl_setup() {
    if (!('Perl' in dialog)) {
        dialog.Perl = {};
        ["perl_lintOption",
         "perl_lintOption_perlCriticLevel",
         "perl_lintOptions_perlCriticBox_label",
         "perl_lintOption_perlCriticLevel",
         "perl_lintOption_perlCriticEnableNote"
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
            } else {
                dialog.Perl.perl_lintOption_perlCriticEnableNote.removeAttribute('collapsed');
            }
        },
        __EOD__:null
    };
}

function python_setup() {
    if (!('Python' in dialog)) {
        dialog.Python = {};
        [
         "lint_python_with_pychecker",
         "lint_python_with_pylint",
         "lint_python_with_pyflakes",
         "pychecker_browse_rcfile",
         "pychecker_browse_wrapper_location",
         "pychecker_checking_rcfile",
         "pychecker_dangerous",
         "pychecker_failure",
         "pychecker_wrapper_location",
         "pyflakes_failure",
         "pylint_browse_rcfile",
         "pylint_checking_rcfile",
         "pylint_checking_rcfile",
         "pylint_failure",
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
    var pyflakesStatusByExecutable = languageInfo.Python.pyflakesStatusByExecutable;
    if (!(pythonExe in pylintStatusByExecutable)
        || !(pythonExe in pyflakesStatusByExecutable)) {
        setTimeout(function() {
                var res;
                if (!(pythonExe in pylintStatusByExecutable)) {
                    res = appInfoEx.haveModules(1, ['pylint']);
                    pylintStatusByExecutable[pythonExe] = res;
                }
                if (!(pythonExe in pyflakesStatusByExecutable)) {
                    res = appInfoEx.haveModules(1, ['pyflakes.scripts.pyflakes']);
                    pyflakesStatusByExecutable[pythonExe] = res;
                }
                languageInfo.Python.updateUI(pythonExe);
            }, 300);
    } else {
        languageInfo.Python.updateUI(pythonExe);
    }
}
languageSetup.Python = python_setup;
function pythonInfo() {
    return {
        pylintStatusByExecutable: {},
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
                this._updateFailureBox(failureNode, pythonExe, "pylint")
            }
            this.onTogglePylintChecking(checkbox);
            
            // pyflakes
            checkbox = dialog.Python.lint_python_with_pyflakes;
            failureNode = dialog.Python.pyflakes_failure;
            if (pythonExe && this.pyflakesStatusByExecutable[pythonExe]) {
                checkbox.disabled = false;
            } else {
                checkbox.checked = false;
                checkbox.disabled = true;
                this._updateFailureBox(failureNode, pythonExe, "pyflakes")
            }
            
            // Update UI for pychecker
            checkbox = dialog.Python.lint_python_with_pychecker;
            this.onTogglePycheckerChecking(checkbox);
        },
            
        onTogglePylintChecking: function(checkbox) {
            var pylintEnabled = checkbox.checked;
            dialog.Python.pylint_checking_rcfile.disabled = !pylintEnabled;
            dialog.Python.pylint_browse_rcfile.disabled = !pylintEnabled;
        },

        onTogglePycheckerChecking: function(checkbox) {
            var pycheckerEnabled = checkbox.checked;
            dialog.Python.pychecker_wrapper_location.disabled = !pycheckerEnabled;
            dialog.Python.pychecker_browse_wrapper_location.disabled = !pycheckerEnabled;
            dialog.Python.pychecker_checking_rcfile.disabled = !pycheckerEnabled;
            dialog.Python.pychecker_browse_rcfile.disabled = !pycheckerEnabled;
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
           var textbox = dialog.Python[eltID];
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
        },
       
        loadPylintRcfile: function() {
            this.loadTextboxFromFilepicker("pylint_checking_rcfile",
                                           "Find a .pylintrc file");
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
