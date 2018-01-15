/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * Profile javascript code
 *
 * This produces profiler logs that are compatible with [Cleopatra](https://github.com/mozilla/cleopatra)
 *
 * @module ko/profiler
 */
(function ()
{
    const {Cc, Ci}  = require("chrome");

    var profiler = Cc["@mozilla.org/tools/profiler;1"].getService(Ci.nsIProfiler);
    var prefs = require("ko/prefs");
    var enabled = prefs.getBoolean("profilerEnabled", false);
    var activeProfiler = null;

    /**
     * Enable profiling, none of the other methods in this module will do anything
     * otherwise
     *
     * @returns {Void}
     */
    this.enable = () =>
    {
        enabled = true;
    }

    /**
     * Disable profiling, does not stop already active profilers
     *
     * @returns {Void}
     */
    this.disable = () =>
    {
        enabled = false;
    }

    /**
     * Start profiling
     *
     * If a name is given it will only run if the "profilerEnabledName" is set
     * to the same name.
     *
     * The named profilers are mainly intended for profiling code that runs on startup,
     * for anything else you should just call start() without a name.
     *
     * @param   {String} name   name of profiler (optional)
     *
     * @returns {Void}
     */
    this.start = (name = "") =>
    {
        if (name == "" && ! enabled)
            return;

        if (name)
        {
            if (prefs.getString("profilerEnabledName", "") !== name)
                return;
        }

        this.stop(activeProfiler);
        activeProfiler = name;

        var features = prefs.getString("profilerFeatures", "stackwalk,js").split(",");
        profiler.StartProfiler(
            prefs.getLong("profilerMemory", 10000000),
            prefs.getLong("profilerSampleRate", 1),
            features,
            features.length
        );
    };

    /**
     * Check whether a profiler is running
     *
     * @returns {Boolean}
     */
    this.isActive = () =>
    {
        return profiler.IsActive();
    };

    /**
     * Stop profiling
     *
     * @param   {String} name
     *
     * @returns {Void}
     */
    this.stop = (name = "") =>
    {
        if ( ! profiler.IsActive() || name !== activeProfiler)
            return;

        profiler.StopProfiler();
    };

    /**
     * Pause profiling
     *
     * @param   {String} name
     *
     * @returns {Void}
     */
    this.pause = (name = "") =>
    {
        if ( ! profiler.IsActive() || name !== activeProfiler)
            return;

        profiler.PauseSampling();
    };

    /**
     * Resume profiling
     *
     * @param   {String} name
     *
     * @returns {Void}
     */
    this.resume = (name = "") =>
    {
        if ( ! profiler.IsPaused() || name !== activeProfiler)
            return;

        profiler.ResumeSampling();
    };

    /**
     * Save the log, this should be called before calling stop()
     *
     * Logs are saved to profiledir/profiler
     *
     * @param   {String} name
     *
     * @returns {Void}
     */
    this.save = (name = "") =>
    {
        if ( ! profiler.IsActive() || name !== activeProfiler)
            return;

        if (name == "")
            name = "unnamed";

        var sys = require("sdk/system");
        var koFile = require("ko/file");
        var profileDir = sys.pathFor("ProfD");
        var dir = koFile.join(profileDir, '..', 'profiler');
        koFile.mkpath(dir);

        var profileObj = profiler.getProfileData();
        var file = koFile.open(koFile.join(dir, `${name}-${Date.now()}.cleo`), "w");
        file.write(JSON.stringify(profileObj));
        file.close();
    };

}).apply(module.exports);
