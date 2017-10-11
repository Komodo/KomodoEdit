/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * Easily spawn dialogs without fiddling in their markup
 *
 * @module ko/dialogs
 */
(function () {

    const log       = require("ko/logging").getLogger("sdk/dialogs");
    const _         = require('contrib/underscore');
    const prefs     = require("ko/prefs");

    /**
     * A dialog to query the user for a string in a textbox.
     *
     * @param {String}      [message]               The message
     * @param {Object=}     [opts]                  Optional object with options
     * @param {string}      [opts.prompt]           text to place before the input textbox.
     * @param {string}      [opts.label1]           label to place on the first textbox.
     * @param {string}      [opts.value1]           default value for the first textbox.
     * @param {string}      [opts.label2]           label to place on the second textbox.
     * @param {string}      [opts.value2]           default value for the second textbox.
     * @param {string}      [opts.title]            dialog title.
     * @param {string}      [opts.mruName1]         get an MRU on the first text box.The value of the
                                                    string is the namespace for the MRU.
     * @param {string}      [opts.mruName2]         get an MRU on the second text box. The value of the
                                                    string is the namespace for the MRU.
     * @param {function}    [opts.validator]        `function(value){}` is a callable object to validate
                                                    the current value when the user presses "OK". It is called with the
                                                    current value as the only argument. If the function returns false the
                                                    "OK" is ignored.
     * @param {boolean}     [opts.multiline1]       indicates that the first textbox should be multiline
     * @param {boolean}     [opts.multiline2]       indicates that the second textbox should be multiline
     * @param {integer}     [opts.screenX]          position to open the dialog at
     * @param {integer}     [opts.screenY]          position to open the dialog at
     *
     * @returns {Array|Null}    It returns null if the dialog was cancelled. Otherwise it returns an array
     *                          containing the two values entered by the user if label2 was provided,
     *                          otherwise it just returns the first value.
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

        var w = opts.window || window;

        w.openDialog("chrome://komodo/content/dialogs/prompt.xul",
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
     * @param {string}      message                 The message
     * @param {object=}     [opts]                  Optional object with options
     * @param {string}      [opts.response]         The default response. This button is shown as the default.
     *                                              Must be one of "Yes" or "No". If left empty or null the default
     *                                              response is "Yes".
     * @param {string}      [opts.text]             Allows you to specify a string of text that will be display in a
     *                                              non-edittable selectable text box. If "text" is null or no specified
     *                                              then this textbox will no be shown.
     * @param {string}      [opts.title]            dialog title
     * @param {string}      [opts.doNotAskPref]     prefname to use that stores whether the user chose not to give this prompt
     *                                              again. If no prefname is given the prompt will always be shown.
     * @param {string}      [opts.yes]              override the label for the yes button (defaults to Ok)
     * @param {string}      [opts.no]               override the label for the no button (defaults to Cancel)
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

        w = opts.window || window;

        w.openDialog("chrome://komodo/content/dialogs/yesNo.xul",
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
     * @param {String}      message                 The message to be displayed to the user
     * @param {Object=}     opts                    The options object.  Attributes explained above.
     * @param {object=}     [opts]                  Optional object with options
     * @param {string}      [opts.prompt]           Message to show as the prompt
     * @param {string|array} [opts.buttons]         Either a list of strings, each a label of a button
     *                                              to show, or a list of array items [label, accesskey, tooltiptext], 
     *                                              where accesskey and tooltiptext are both optional. Currently this is
     *                                              limited to three buttons, plus an optional "Cancel" button. For 
     *                                              example to mimic (mostly) ko.dialogs.yesNo use ["Yes", "No"] and to mimic
     *                                              ko.dialogs.yesNoCancel use ["Yes", "No", "Cancel"].
     * @param {string}      [opts.response]         The default response. This button is shown as the default.
     *                                              Must be one of "Yes" or "No". If left empty or null the default
     *                                              response is "Yes".
     * @param {string}      [opts.text]             Allows you to specify a string of text that will be display in a
     *                                              non-edittable selectable text box. If "text" is null or no specified
     *                                              then this textbox will no be shown.
     * @param {string}      [opts.title]            dialog title
     * @param {boolean}     [opts.doNotAskPref]     prefname to use that stores whether the user chose not to give this prompt 
     *                                              again. If no prefname is given the prompt will always be shown.
     * @param {string}      [opts.class]                 the class attribute to be applied to the dialog icon.
     *
     * @returns {String} returns the name of the button pressed.
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
     * @param {String}      message                 The message
     * @param {Object=}     opts                    Optional object with options
     * @param {string}      [opts.title]            dialog title
     */
    this.alert = (message, opts = {}) =>
    {
        var _opts = {};
        var props = ["prompt", "text", "title", "classNames","hidechrome"];
        _.each(props, (prop) => { _opts[prop] = opts[prop] || null });
        _opts.prompt = message;

        w = opts.window || window;

        w.openDialog("chrome://komodo/content/dialogs/alert.xul",
                          "_blank",
                          opts.features || "chrome,modal,titlebar,centerscreen",
                          _opts);
    };

    /**
     * Pick a file or Folder from the file system.
     *
     * @param {String}      message                 The message
     * @param {function}    callback                function to handle
     * @param {Object=}     opts                    Optional object with options
     * @param {string}      [opts.message]          The message
     * @param {string}      [opts.path]             Location to open file picker at
     * @param {string}      [opts.type=file|folder] Type of file system item we're looking for
     */
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
                    options: { filetype: opts.type },
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
