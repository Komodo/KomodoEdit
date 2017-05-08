/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * Easily spawn dialogs without fiddling in their markup
 *
 * @module ko/dialogs
 */
(function () {

    const log       = require("ko/logging").getLogger("sdk/dialogs");
    const _         = require('contrib/underscore');
    const prefs     = ko.prefs;

    /**
     * A dialog to query the user for a string in a textbox.
     *
     * Possible opts properties:
     *  "prompt" is text to place before the input textbox.
     *  "label1" is a label to place on the first textbox.
     *  "value1" is a default value for the first textbox.
     *  "label2" is a label to place on the second textbox.
     *  "value2" is a default value for the second textbox.
     *  "title" is the dialog title.
     *  "mruName1" can be specified (a string) to get an MRU on the first text box.
     *      The value of the string is the namespace for the MRU.
     *  "mruName2" can be specified (a string) to get an MRU on the second text box.
     *      The value of the string is the namespace for the MRU.
     *  "validator" is a callable object to validate the current value when the
     *      user presses "OK". It is called with the current value as the only
     *      argument.  If the function returns false the "OK" is ignored.
     *  "multiline1" is a boolean indicating that the first textbox should be
     *      multiline. "mruName1" and "multiline1" are mutually exclusive.
     *  "multiline2" is a boolean indicating that the second textbox should be
     *      multiline. "mruName2" and "multiline2" are mutually exclusive.
     *  "screenX", "screenY" allow one to specify a dialog position other than
     *      the alert position.
     *
     * It returns null if the dialog was cancelled. Otherwise it returns an array
     * containing the two values entered by the user if label2 was provided,
     * otherwise it just returns the first value.
     *
     * @param {String} message  The message
     * @param {Object} opts     Optional object with options
     *
     * @returns {String|Null}
     */
    this.prompt = (message, opts = {}) =>
    {
        var _opts = {};
        var props = ["label", "value", "title", "mruName",
                     "label2", "value2", "mruName2", "multiline2",
                     "validator", "multiline", "screenX", "screenY",
                     "tacType", "tacParam", "tacShowCommentColumn",
                     "selectionStart", "selectionEnd", "classNames",
                     "hidechrome","pin"];

        _.each(props, (prop) => { _opts[prop] = opts[prop] || null });
        _opts.prompt = message;

        if (_opts.mruName && _opts.multiline) {
            log.warn("Cannot use both 'mruName' and 'multiline' on prompt "+
                     "dialogs. 'mruName' will be ignored.");
            _opts.mruName = null;
        }

        window.openDialog("chrome://komodo/content/dialogs/prompt.xul",
                  "_blank",
                  opts.features || "chrome,modal,titlebar,centerscreen",
                  _opts);

        if (_opts.retval == "OK")
        {
            if (_opts.label2)
            {
                return [ _opts.value, _opts.value2 ];
            }
            else
            {
                return _opts.value;
            }
        }
        else
        {
            return null;
        }
    }

    /**
     * Ask the user for confirmation
     *
     * All opts can be left blank or specified as null to get a default value.
     *  "response" is the default response. This button is shown as the default.
     *      Must be one of "Yes" or "No". If left empty or null the default
     *      response is "Yes".
     *  "text" allows you to specify a string of text that will be display in a
     *      non-edittable selectable text box. If "text" is null or no specified
     *      then this textbox will no be shown.
     *  "title" is the dialog title.
     *  "doNotAskPref", uses/requires the following two prefs:
     *      boolean donotask_`<doNotAskPref>`: whether to not show the dialog
     *      string donotask_action_`<doNotAskPref>`: "Yes" or "No"
     *  "helpTopic",  the help topic, to be passed to "ko.help.open()". If
     *      not provided (or null) then no Help button will be shown.
     *  "yes", override the label for the yes button (defaults to Ok)
     *  "no", override the label for the no button (defaults to Cancel)
     *
     * @param {String} message  The message
     * @param {Object} opts     Optional object with options
     *
     * @returns {Boolean}
     */
    this.confirm = (message, opts = {}) =>
    {
        var _opts = {};
        var props = ["response", "text", "title", "doNotAskPref", "helpTopic",
                     "yes", "no", "classNames","hidechrome", "pin"];
        _.each(props, (prop) => { _opts[prop] = opts[prop] || null });
        _opts.prompt = message;

        if ( ! _opts.yes)
        {
            _opts.yes = "Ok";
        }

        if ( ! _opts.no)
        {
            _opts.no = "Cancel";
        }

        // Break out early if "doNotAskPref" prefs so direct.
        if (_opts.doNotAskPref)
        {
            _opts.doNotAskUI = true;
            var bpref = "donotask_"+_opts.doNotAskPref;
            var spref = "donotask_action_"+_opts.doNotAskPref;
            if (prefs.getBoolean(bpref, false))
            {
                var actions = [_opts.yes, _opts.no];
                var action = prefs.getStringPref(spref);
                if (actions.indexOf(action) != -1)
                {
                    return action;
                } else {
                    log.error("illegal action for Yes/No/Cancel dialog in '" +
                                     spref + "' preference: '" + action + "'");
                    // Reset the boolean pref.
                    prefs.deletePref(bpref);
                    prefs.deletePref(spref);
                }
            }
        }

        window.openDialog("chrome://komodo/content/dialogs/yesNo.xul",
                          "_blank",
                          opts.features || "chrome,modal,titlebar,centerscreen",
                          _opts);

        if (_opts.doNotAskPref && _opts.doNotAsk) {
            prefs.setBooleanPref(bpref, true);
            prefs.setStringPref(spref, _opts.response);
            _opts.response = _opts.yes; // Dont ask again means we're confirming next time
        }

        return _opts.response == _opts.yes;
    }
    
    /** Show the user some prompt and request one of a number of responses.
     * 
     * Options:
     *  "prompt" is message to show.
     *  "buttons" is either a list of strings, each a label of a button to show, or
     *      a list of array items [label, accesskey, tooltiptext], where accesskey
     *      and tooltiptext are both optional.
     *      Currently this is limited to three buttons, plus an optional "Cancel"
     *      button. For example to mimic (mostly) ko.dialogs.yesNo use ["Yes", "No"]
     *      and to mimic ko.dialogs.yesNoCancel use ["Yes", "No", "Cancel"].
     *  "response" is the default response. This button is shown as the default.
     *      It must be one of the strings in "buttons" or empty, in which case the
     *      first button is the default.
     *  "text" allows you to specify a string of text that will be display in a
     *      non-edittable selectable text box. If "text" is null or no specified
     *      then this textbox will not be shown.
     *  "title" is the dialog title.
     *  "doNotAskPref", uses/requires the following two prefs:
     *      boolean donotask_<doNotAskPref>: whether to not show the dialog
     *      string donotask_action_<doNotAskPref>: the name of the button pressed
     *  "className", the class attribute to be applied to the dialog icon.
     *
     * @param {String} message  The message to be displayed to the user
     * @param {Object} opts  The options object.  Attributes explained above.
     *
     * @returns {String} returns the name of the button pressed.
     * 
     */
    this.open = (message, opts = {}) =>
    {
        var _opts = {};
        var props = ["response", "text", "title", "doNotAskPref", "helpTopic",
                     "buttons", "classNames","hidechrome", "pin"];
        _.each(props, (prop) => { _opts[prop] = opts[prop] || null; });
        _opts.prompt = message;
        _opts.style = opts.className || "question-icon spaced";
    
        // Break out early if "doNotAskPref" prefs so direct.
        var bpref = null, spref = null;
        if (_opts.doNotAskPref) {
            bpref = "donotask_"+_opts.doNotAskPref;
            spref = "donotask_action_"+_opts.doNotAskPref;
            if (prefs.getBooleanPref(bpref)) {
                return prefs.getStringPref(spref);
            }
        }
    
        window.openDialog("chrome://komodo/content/dialogs/customButtons.xul",
                          "_blank",
                          "chrome,modal,titlebar,centerscreen",
                          _opts);
    
        if (_opts.doNotAskPref && _opts.doNotAsk) {
            prefs.setBooleanPref(bpref, true);
            prefs.setStringPref(spref, _opts.response);
        }
        return _opts.response;
    };

    /**
     * Show an alert message
     *
     * All opts can be left blank or specified as null to get a default value.
     *  "title" is the dialog title.
     * 
     * @param {String} message  The message
     * @param {Object} opts     Optional object with options
     * 
     * @returns {Void}
     */
    this.alert = (message, opts = {}) =>
    {
        var _opts = {};
        var props = ["prompt", "text", "title", "classNames","hidechrome"];
        _.each(props, (prop) => { _opts[prop] = opts[prop] || null });
        _opts.prompt = message;

        window.openDialog("chrome://komodo/content/dialogs/alert.xul",
                          "_blank",
                          opts.features || "chrome,modal,titlebar,centerscreen",
                          _opts);
    };

    this.filepicker = (message, callback, opts) =>
    {
        var ss = require("ko/simple-storage").get("dialogs");
        var  legacy = require("ko/windows").getMain().ko;
        var _opts;

        if (typeof callback == "object")
        {
            _opts = callback;
            callback = opts;
            opts = _opts;
        }

        _opts = {};
        var props = ["type", "path", "callback"];
        _.each(props, (prop) => { _opts[prop] = opts[prop] || null; });

        message = message || "Choose path";
        opts.type = opts.type || "file";
        opts.path = opts.path || ss.storage.filepicker_path || legacy.uriparse.URIToLocalPath(legacy.places.getDirectory());
        opts.callback = callback || opts.callback || function() { log.error("callback not defined"); };

        require("ko/modal").open(
            message,
            {
                path: {
                    type: "filepath",
                    options: { type: opts.type },
                    value: opts.path
                }
            },
            (data) =>
            {
                if ( ! data)
                    return opts.callback();

                ss.storage.filepicker_path = data.path;
                return opts.callback(data.path);
            }
        );
    };

}).apply(module.exports);
