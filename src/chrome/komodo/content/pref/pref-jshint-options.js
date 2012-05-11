/* Copyright (c) 2000-2012 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/**
 * Build a readable list of jslint/jshint options to select the currently
 * supported options based on the actual js code we're going to run.
 */
var log = ko.logging.getLogger("pref.pref-jshint-options");
var gObj, gOptions, gValOptions, gOptionDict = {}, gAllJSHintStrictSettings;
var gPrefNumByName = {};
const BOOLEAN_NAME = "boolean";
const INT_NAME = "int";

function JSLintOption(name, typeName, defaultValue, comment) {
    this.name = name;
    this.typeName = typeName;
    this.defaultValue = defaultValue;
    this.comment = comment;
    gOptionDict[name] = this;
}

function onLoad() {
    gObj = window.arguments[0];
    // Use stringified default values for numeric items
    gValOptions = {'maxlen':'', 'indent':'4', 'maxerr':'50'};
    try {
        initOptions();
        gAllJSHintStrictSettings = {
            // adsafe     : true, // if ADsafe should be enforced
            asi: "false", // true if automatic semicolon insertion should be tolerated
            bitwise    : "true", // if bitwise operators should not be allowed
            boss       : "true", // if advanced usage of assignments and == should be allowed
            curly      : "true", // if curly braces around blocks should be required (even in if/for/while)
            debug      : "false", // if debugger statements should be allowed
            devel      : "false", // if logging should be allowed (console, alert, etc.)
            eqeqeq     : "true", // if === should be required
            eqnull     : "false", // if == null comparisons should be tolerated
            es5        : "true", // if ES5 syntax should be allowed
            esnext      :"true", // if es.next specific syntax should be allowed
            evil       : "false", // if eval should be allowed
            expr        : "true", // if ExpressionStatement should be allowed as Programs
            forin      : "true", // if for in statements must filter
            funcscope   : "true", // if only function scope should be used for scope tests
            globalstrict: "true", // if global "use strict"; should be allowed (also
            immed      : "true", // if immediate invocations must be wrapped in parens
            iterator    : "false", // if the `__iterator__` property should be allowed
            lastsemic   : "false", // if semicolons may be ommitted for the trailing
                                // statements inside of a one-line blocks.
            latedef    : "true", // if the use before definition should not be tolerated
            laxbreak   : "true", // if line breaks should not be checked
            laxcomma   : "true", // if line breaks should not be checked around commas
            loopfunc   : "false", // if functions should be allowed to be defined within loops
            multistr    : "false", // allow multiline strings
            newcap     : "true", // if constructor names must be capitalized
            noarg      : "true", // if arguments.caller and arguments.callee should be disallowed
            noempty    : "false", // if empty blocks should be disallowed
            nonew      : "false", // if using `new` for side-effects should be disallowed
            nonstandard : "false", // if non-standard (but widely adopted) globals should
                                // be predefined
            nomen      : "true", // if names should be checked
            onevar     : "true", // if only one var statement per function should be allowed
            onecase     : "false", // if one case switch statements should be allowed
            passfail   : "false", // if the scan should stop on first error
            plusplus   : "true", // if increment/decrement should not be allowed
            proto       : "true", // if the `__proto__` property should be allowed
            regexdash   : "false", // if unescaped first/last dash (-) inside brackets
                                // should be tolerated
            regexp     : "true", // if the . should not be allowed in regexp literals
            undef      : "true", // if variables should be declared before used
            scripturl   : "false", // if script-targeted URLs should be tolerated
            shadow     : "false", // if variable shadowing should be tolerated
            smarttabs   : "false", // if smarttabs should be tolerated
                                // (http://www.emacswiki.org/emacs/SmartTabs)
            strict     : "false", // require the "use strict"; pragma
            sub        : "false", // if all forms of subscript notation are tolerated
            supernew    : "false", // if `new function () { ... };` and `new Object;`
                                // should be tolerated
            trailing    : "true", // if trailing whitespace rules apply
            validthis   : "true", // if 'this' inside a non-constructor function is valid.
                                // This is a function scoped option only.
            withstmt    : "false", // if with statements should be allowed
            white      : "true", // if strict whitespace rules apply
        };
    } catch(ex) {
        log.exception(ex, "Error in pref-jshint-options.js: ");
    }
}

function onUnload() {
}

function OK() {
    var newValues = {};
    gObj.newValues = newValues;
    var eltNum = 0, widget, prefName, option, currentValue;
    while (true) {
        eltNum += 1;
        widget = document.getElementById("jshint-option-widget-" + eltNum);
        if (!widget) {
            break;
        }
        prefName = widget.getAttribute("prefName");
        option = gOptionDict[prefName];
        // Store each option only if it doesn't have the default value
        if (option.typeName == BOOLEAN_NAME) {
            // Default values and option values are strings, checked is a boolean
            if (widget.checked === (option.defaultValue === "false")) {
                // store if checked, default is false
                //       or not checked, default is true
                newValues[prefName] = widget.checked ? "true" : "false";
            }
        } else if (option.typeName == INT_NAME) {
            currentValue = widget.value.replace(/^\s+/, "").replace(/\s+$/, "");
            if (option.defaultValue !== currentValue) {
                newValues[prefName] = widget.value;
            }
        }
    }
    var predef = document.getElementById("pref-jshint-predef");
    var predefText = predef.value.replace(/^\s+/, "").replace(/\s+$/, "");
    if (predefText) {
        newValues.predef = predefText;
    }
    gObj.result = true;
    return true;
}

function Cancel() {
    gObj.result = false;
    return true;
}

function stringCompare(s1, s2) {
    if (s1 < s2) return -1;
    if (s1 > s2) return 1;
    return 0;
}

function initOptions() {
    var koFileEx = Components.classes["@activestate.com/koFileEx;1"]
        .createInstance(Components.interfaces.koIFileEx);
    koFileEx.path = gObj.path;
    koFileEx.open('r');
    var data = koFileEx.readfile();
    koFileEx.close();
    var currentValues = gObj.currentValues;
    var options = [];
    if (gObj.isJSHint) {
        var m1 = /\n\s*boolOptions\s*=\s*\{\s*?\n((?:\n|.)*?)\s*\},/.exec(data);
        var firstLinePtn = /\s*(\w+)\s*:\s*(true|false)\s*,\s*\/\/\s*(.*)\s*/;
        var nextLinePtn =  /\s*\/\/\s*(.*)/;
        var line, lines = m1[1].split(/\r?\n/);
        var m, name, comment = "", defaultValue;
        for (var i = 0; i < lines.length; i++) {
            line = lines[i];
            if (!!(m = firstLinePtn.exec(line))) {
                if (comment) {
                    options.push(new JSLintOption(name, BOOLEAN_NAME, defaultValue, comment));
                }
                name = m[1];
                defaultValue = 'false'; // stringification makes comparison easier.
                comment = m[2] + " " + m[3];
            } else if (!!(m = nextLinePtn.exec(line))) {
                comment += " " + m[1];
            } else {
                log.debug("jshint options: can't figure out what to do with line <<" + line + ">>");
            }
        }
        if (comment) {
            options.push(new JSLintOption(name, BOOLEAN_NAME, defaultValue, comment));
        }
        for (var name in gValOptions) {
            options.push(new JSLintOption(name, INT_NAME, gValOptions[name], ""));
        }
        options.sort(function(a, b) {return stringCompare(a.name, b.name)});
        var rowsTarget = document.getElementById("pref-jshint-rows");
        var targetNode = document.getElementById("pref-jshint-predef-label");
        var newItem, newLabel, newRow, newHbox;
        var eltNum = 0;
        for each (var option in options) {
            eltNum += 1;
            name = option.name;
            gPrefNumByName[name] = eltNum;
            newRow = document.createElement("row");
            newRow.setAttribute("id", "jshint-option-row-" + eltNum);
            newLabel = document.createElement("label");
            newLabel.setAttribute("id", "jshint-option-comment" + eltNum);
            newLabel.setAttribute("value", name);
            newLabel.control = "jshint-option-widget-" + eltNum;
            newRow.appendChild(newLabel);
            switch(option.typeName) {
                case BOOLEAN_NAME:
                    newItem = document.createElement("checkbox");
                    newItem.setAttribute("id", "jshint-option-widget-" + eltNum);
                    newItem.setAttribute("label", option.comment || "");
                    newItem.setAttribute("prefName", option.name);
                    // remember all values are stringified
                    if (name in currentValues) {
                        newItem.setAttribute('checked', currentValues[name] === "true");
                    } else {
                        newItem.setAttribute('checked', option.defaultValue === "true");
                    }
                    newRow.appendChild(newItem);
                    break;
                case INT_NAME:
                    newHbox = document.createElement("hbox");
                    newHbox.setAttribute("id", "jshint-option-hbox-" + eltNum);
                    newItem = document.createElement("textbox");
                    newItem.setAttribute("id", "jshint-option-widget-" + eltNum);
                    newItem.setAttribute("label", option.comment || "");
                    newItem.setAttribute("prefName", option.name);
                    newItem.setAttribute("cols", "4");
                    newItem.setAttribute("style", "width: 6em;");
                    if (name in currentValues) {
                        newItem.setAttribute('value', currentValues[name]);
                    } else {
                        newItem.setAttribute('value', option.defaultValue);
                    }
                    newHbox.appendChild(newItem);
                    newItem = document.createElement("spacer");
                    newItem.setAttribute("flex", "1");
                    newHbox.appendChild(newItem);
                    newRow.appendChild(newHbox);
                    break;
                default:
                    log.debug("Unexpected option: name: " + option.name + ", type:" + option.typeName);
                    continue;
            }
            rowsTarget.appendChild(newRow);
        }
        if ('predef' in currentValues) {
            document.getElementById("pref-jshint-predef").value = currentValues.predef;
        }
    } else {
        // Do jslint stuff.
    }
}

function ApplyStrictness() {
    try {
    var prefName, checkbox;
    for (prefName in gAllJSHintStrictSettings) {
        var num = gPrefNumByName[prefName];
        if (num !== undefined) {
            checkbox = document.getElementById("jshint-option-widget-" + num);
            if (checkbox) {
                checkbox.checked = gAllJSHintStrictSettings[prefName] === "true";
            }
        }
    }
    } catch(ex) {
        log.exception(ex, "ApplyStrictness problem.");
    }
}
