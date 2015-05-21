Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

function koManifestLoader()
{
    this.init();
}

(function() {

    const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
    const { NetUtil }   = Cu.import("resource://gre/modules/NetUtil.jsm", {});
    const { Services }  =   Cu.import("resource://gre/modules/Services.jsm", {});

    var loggingSvc, prefSvc, log, prefs, koResolve;

    var initialized = false;
    
    var loaded = {};

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

            //log.setLevel(10);
            
            koResolve = Cc["@activestate.com/koResolve;1"]
                            .getService(Ci.koIResolve);

            var manifests = this._getManifests();
            log.debug("Loading " + manifests.length + " manifests");

            // Load manifests
            for (let i=0; i<manifests.length; i++)
            {
                this.loadManifest(manifests[i], false);
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
            if ( ! this._validateFile(file))
            {
                return false;
            }
            
            if (uri in loaded)
                this.unloadManifest(uri);

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
            
            loaded[uri] = true;

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
            
            if (uri in loaded)
                delete loaded[uri];

            return true;
        },

        addManifest: function(uri)
        {
            log.debug("Storing " + uri);
            this._addManifest(uri);
        },

        deleteManifest: function(uri)
        {
            log.debug("Deleting " + uri);
            this._deleteManifest(uri);
        },

        _getFile: function(uri)
        {
            var filePath = koResolve.uriToPath(uri);
            if ( ! filePath)
            {
                return false;
            }

            var file = Cc["@mozilla.org/file/local;1"]
                        .createInstance(Components.interfaces.nsILocalFile);
            file.initWithPath(filePath);

            return file;
        },

        _validateFile: function(file)
        {
            if ( ! file)
            {
                log.error("File is not defined");
                return false;
            }

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

        _manifests: false,
        _getManifests: function()
        {
            if ( ! this._manifests)
            {
                var manifests = prefs.getString('runtime_manifests', '[]');

                try
                {
                    this._manifests = JSON.parse(manifests)
                }
                catch (e)
                {
                    log.error("Error parsing manifest JSON: " + e.message);
                    this._manifests = [];
                }
            }

            return this._manifests;
        },

        _addManifest: function(uri)
        {
            this._deleteManifest(uri);
            
            var manifests = this._getManifests();
            manifests.push(uri);
            
            this._setManifests(manifests);
        },

        _deleteManifest: function(uri)
        {
            var manifests = this._getManifests();
            var i = manifests.length;
            while (i--)
            {
                if (manifests[i] == uri)
                {
                    manifests.splice(i, 1);
                }
            }

            this._setManifests(manifests);
        },

        _setManifests: function(manifests)
        {
            prefs.setStringPref("runtime_manifests", JSON.stringify(manifests));
            this._manifests = manifests;
        },

        observe: function() {}
    };

}.call());

var NSGetFactory = XPCOMUtils.generateNSGetFactory([koManifestLoader]);
