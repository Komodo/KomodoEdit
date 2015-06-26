Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

function koResolve()
{
    this.init();
}

(function() {

    const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
    const { NetUtil }   = Cu.import("resource://gre/modules/NetUtil.jsm", {});
    const { Services }  =   Cu.import("resource://gre/modules/Services.jsm", {});

    var loggingSvc, log;
    var nsIChromeReg;

    var cache = {};
    var initialized = false;

    koResolve.prototype =
    {
        classDescription:   "Resolve / translate paths and URI's",
        classID:            Components.ID("{2584BC91-0AEE-4DB1-B73F-2F1610979ED1}"),
        contractID:         "@activestate.com/koResolve;1",
        QueryInterface:     XPCOMUtils.generateQI([Ci.koIResolve, Ci.nsIObserver]),

        init: function()
        {
            if (initialized)
            {
                return;
            }

            // Init Services
            loggingSvc = Cc["@activestate.com/koLoggingService;1"].
                            getService(Ci.koILoggingService);
            log        = loggingSvc.getLogger('koResolve');

            nsIChromeReg = Cc['@mozilla.org/chrome/chrome-registry;1']
                                    .getService(Ci["nsIChromeRegistry"]);

            //log.setLevel(10);

            initialized = true;
        },

        uriToPath: function(fileUri, originalUri)
        {
            if (fileUri in cache)
            {
                return cache[fileUri];
            }
            
            originalUri = originalUri || fileUri;
            
            var filePath = false;
            var match = fileUri.match(/([a-z]{2,})\:/);

            // Handle different file protocols
            switch (match ? match[1] : '')
            {
                // chrome:// uri, convert it and pass it back into _resolveFile
                case 'chrome':
                    var resolvedPath    = Services.io.newURI(fileUri, "UTF-8", null);
                    resolvedPath        = nsIChromeReg.convertChromeURL(resolvedPath);

                    if (resolvedPath instanceof Ci.nsINestedURI)
                    {
                        resolvedPath = resolvedPath.innermostURI;
                        if (resolvedPath instanceof Ci.nsIFileURL)
                        {
                            return this.uriToPath(resolvedPath.file.path, originalUri);
                        }
                    }
                    else
                    {
                        return this.uriToPath(resolvedPath.spec, originalUri);
                    }
                    break;

                // resource:// uri, load it up and return the path
                case 'resource':
                    filePath = Services.io.newURI(fileUri, null,null)
                                .QueryInterface(Ci.nsIFileURL).file.path;
                    break;

                // file:// uri, just strip the prefix and get on with it
                case 'file':
                    filePath = NetUtil.newURI(fileUri)
                                      .QueryInterface(Ci.nsIFileURL)
                                      .file.path;
                    break;

                // Looks like we already have the correct path
                case '':
                    filePath = fileUri
                    break;
            }

            // Check if we received a path
            if ( ! filePath)
            {
                log.error('File uri could not be resolved: ' + fileUri);
                return false;
            }

            log.debug('Resolved "' + originalUri + '" as "' + filePath + '"');

            cache[originalUri] = filePath;

            return filePath;
        }
    };

}.call());

var NSGetFactory = XPCOMUtils.generateNSGetFactory([koResolve]);
