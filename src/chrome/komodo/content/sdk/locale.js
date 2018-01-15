/**
 * This module interfaces with Mozilla's nsIStringBundleService, it allows you
 * to use it with as little logic as possible.
 *
 * If used from a module you can place your properties file in locale/en-US/modulename.properties
 * to bypass having to call .use()
 *
 * @module ko/locale
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @example
 * var l = require("ko/locale").use("path/to/file.properties");
 * console.log(l.get("hello", "world"));
 */
(function() {

    const {Cc, Ci} = require("chrome");
    const bundleSvc = Cc["@mozilla.org/intl/stringbundle;1"].getService(Ci.nsIStringBundleService);
    const log = require("ko/logging").getLogger("ko_locale");
    //log.setLevel(10);

    const locale = this;

    var used = {};

    /**
     * Use the given locale properties file
     *
     * @param   {String} [properties]   Properties file,  this is optional when used from an addon context that has a properly structured localization file
     *
     * @returns {object}  Returns an object with an equivalent of the {@link module:ko/locale~get} method
     */
    this.use = function(properties)
    {
        if ( ! properties)
        {
            properties = this.getBundleURI();
        }

        log.debug("Using " + properties);

        if (properties in used)
        {
            return used[properties];
        }

        var bundle = bundleSvc.createBundle(properties);
        return {
            get: function(name)
            {
                var args = Array.prototype.slice.call(arguments);
                args.shift();

                try
                {
                    if ( ! args.length)
                    {
                        if (args.length == 1 && Array.isArray(args[0]))
                        {
                            args = args[0];
                        }

                        return bundle.GetStringFromName(name);
                    }
                    else
                    {
                        args = Array.prototype.slice.call(args);
                        return bundle.formatStringFromName(name, args, args.length);
                    }
                }
                catch (e)
                {
                    log.warn("Locale not found, returning default for " + name + " in " + properties);
                    return name;
                }
            }
        }
    }

    /**
     * retrieve the matched bundle (properties) file uri for the current context
     *
     * @returns {String}
     */
    this.getBundleURI = function()
    {
        var stack = require("ko/console")._parseStack((new Error()).stack);
        var invoker = stack.slice(2,3)[0].fileName;

        var sdkUrl = require("sdk/url");

        try
        {
            var url = sdkUrl.URL(invoker);
        }
        catch (e)
        {
            log.error("Invoker does not have a valid URL: " + invoker, false);
            return false;
        }

        var bundleUri = url.protocol + "//" + url.host + "/locale/" + url.host + ".properties";
        return bundleUri;
    }

    /**
     * Get localization string
     *
     * @param   {String} name
     * @param   {String} args..    Formatted strings
     *
     * @returns {String}
     */
    this.get = function(name)
    {
        var bundleUri = this.getBundleURI();
        if ( ! bundleUri)
        {
            return name;
        }

        return this.use(bundleUri).get.apply(this, arguments);
    }

}).apply(module.exports);
