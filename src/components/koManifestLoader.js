Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

function koManifestLoader()
{
    this.init();
}

(function() {

    const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
    const { NetUtil }   = Cu.import("resource://gre/modules/NetUtil.jsm", {});
    const { Services }  =   Cu.import("resource://gre/modules/Services.jsm", {});

    var loggingSvc, prefSvc, log, prefs, manifests;

    var initialized = false;

    koManifestLoader.prototype =
    {
        classDescription:   "Load manifests at runtime",
        classID:            Components.ID("{C1549B73-14A9-4C6E-BC1A-3D0698460378}"),
        contractID:         "@activestate.com/koManifestLoader;1",
        QueryInterface:     XPCOMUtils.generateQI([Ci.koIManifestLoader, Ci.nsIObserver]),

        init: function()
        {
            if (initialized)
            {
                return;
            }

            // Init Services
            loggingSvc = Cc["@activestate.com/koLoggingService;1"].
                            getService(Ci.koILoggingService);
            prefSvc    = Cc["@activestate.com/koPrefService;1"].
                            getService(Ci.koIPrefService);

            log        = loggingSvc.getLogger('koManifestLoader');
            prefs      = prefSvc.prefs;

            manifests  = prefs.getPref('stored_runtime_manifests')
                                .QueryInterface(Ci.koIOrderedPreference);

            log.setLevel(10);
            
            log.debug("Loading " + manifests.length + " manifests");

            // Load manifests
            for (let i=0; i<manifests.length; i++)
            {
                this.loadManifest(manifests.getStringPref(i), false);
            }

            initialized = true;
        },

        observe: function(subject, topic, data)
        {
            log.debug('Observe: ' + topic);
        },

        loadManifest: function(uri, store = false)
        {
            log.debug("Loading " + uri);

            var file = this._getFile(uri);

            if ( ! file ||  ! this._validateFile(file))
            {
                return false;
            }

            try
            {
                Components.manager.addBootstrappedManifestLocation(file.parent);
            }
            catch (e)
            {
                log.error("Failed loading manifest: '" + file.path + "'. " + e.message);
                return false;
            }

            if (store)
            {
                this.addManifest(uri);
            }

            return true;
        },

        unloadManifest: function(uri, del = false)
        {
            log.debug("Unloading " + uri);

            var file = this._getFile(uri);

            if ( ! file ||  ! this._validateFile(file))
            {
                return false;
            }

            try
            {
                Components.manager.removeBootstrappedManifestLocation(file.parent);
            }
            catch (e)
            {
                log.error("Failed unloading manifest: '" + file.path + "'. " + e.message);
                return false;
            }

            if (del)
            {
                this.deleteManifest(uri);
            }

            return true;
        },

        addManifest: function(uri)
        {
            this.deleteManifest(uri);

            log.debug("Storing " + uri);

            manifests.appendStringPref(uri);
            prefs.setPref('stored_runtime_manifests', manifests);
        },

        deleteManifest: function(uri)
        {
            log.debug("Deleting " + uri);

            manifests.findAndDeleteStringPref(uri);
            prefs.setPref('stored_runtime_manifests', manifests);
        },

        _getFile: function(uri)
        {
            try
            {

                var match = uri.match(/([a-z]{2,})\:/);

                switch (match ? match[1] : '')
                {
                    case 'resource':
                        var file = Services.io.newURI(uri, null,null)
                                    .QueryInterface(Ci.nsIFileURL).file;
                        break;

                    case 'file':
                        var file = NetUtil.newURI(uri)
                                    .QueryInterface(Ci.nsIFileURL)
                                    .file;
                        break;

                    default:
                        var file = Cc["@mozilla.org/file/local;1"]
                                    .createInstance(Components.interfaces.nsILocalFile);
                        file.initWithPath(uri);
                        break;
                }

                return file;

            }
            catch(e)
            {
                log.error("Error retrieving file: " + uri + ": " + e.message);
                return false;
            }

            return file;
        },

        _validateFile: function(file)
        {
            if ( ! (file instanceof Components.interfaces.nsIFile))
            {
                log.error("File should be instance of nsIFile");
                return false;
            }

            if ( ! file.exists())
            {
                log.error("File does not exist: " + file.path);
                return false;
            }

            if (file.leafName != 'chrome.manifest')
            {
                log.error("Filename should be 'chrome.manifest'");
                return false;
            }

            return true;
        },

        observe: function() {}
    };

}.call());

var NSGetFactory = XPCOMUtils.generateNSGetFactory([koManifestLoader]);
