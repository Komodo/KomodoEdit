const {classes: Cc, interfaces: Ci, utils: Cu, results: Cr} = Components;

Cu.import("resource://gre/modules/XPCOMUtils.jsm");
Cu.import("resource://gre/modules/Services.jsm");
Cu.import("resource://gre/modules/NetUtil.jsm");

const prefs     = Cc['@activestate.com/koPrefService;1']
                    .getService(Ci.koIPrefService).prefs;
const loggingSvc= Cc["@activestate.com/koLoggingService;1"].
                    getService(Ci.koILoggingService);
const log       = this.loggingSvc.getLogger('koiconprotocol');
//log.setLevel(10);

var queued = {};

var getIconLib = function()
{
    if ( ! ("cached" in getIconLib))
    {
        var windows = Services.wm.getEnumerator("Komodo");
        while (windows.hasMoreElements())
        {
            let window = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
            getIconLib.cached = window.require("ko/icons");
            break;
        }
    }

    if ( ! ("cached" in getIconLib))
        log.error("Could not find main komodo window");

    return getIconLib.cached;
}

function IconProtocolHandler() {
}

IconProtocolHandler.prototype = {
    scheme: "koicon",
    defaultPort: -1,
    allowPort: function() false,
    protocolFlags:  Ci.nsIProtocolHandler.URI_NON_PERSISTABLE |
                    Ci.nsIProtocolHandler.URI_IS_UI_RESOURCE,

    newURI: function Proto_newURI(aSpec, aOriginCharset)
    {
        let uri = Cc["@mozilla.org/network/simple-uri;1"].createInstance(Ci.nsIURI);
        uri.spec = aSpec;
        return uri;
    },

    newChannel: function Proto_newChannel(aURI)
    {
        var channel = new IconChannel();
        
        log.debug("Opening " + aURI.spec);

        channel.name = aURI.spec;
        channel.originalURI = aURI;
        channel.URI = aURI;

        return channel;
    },

    classID: Components.ID("{A840147B-5194-49B5-A0D5-CF5E3F87CDC5}"),
    QueryInterface: XPCOMUtils.generateQI([Ci.nsIProtocolHandler])
};

function IconChannel() {
}

IconChannel.prototype = {
    _URI: null,

    name: null,
    originalURI: null,
    URI: null,
    contentType: "image/png",
    contentCharset: null,
    contentLength: null,

    owner: null,
    notificationCallbacks: null,
    securityInfo: null,
    status: null,
    loadFlags: null,
    loadGroup: null,
    contentDisposition: null,
    contentDispositionFilename: null,
    contentDispositionHeader: null,

    isPending: function() {
        return true;
    },

    cancel: function() {},
    suspend: function() {},
    resume: function() {},

    asyncOpen: function(aListener, aContext)
    {
        var self = this;

        var listener = new WrapperListener(aListener, self);
        
        var alreadyQueued = false;
        if (self.URI.spec in queued && queued[self.URI.spec].length)
        {
            alreadyQueued = true;
        }
        else
        {
            queued[self.URI.spec] = [];
        }
        
        queued[self.URI.spec].push(
            function(_listener, _aContext, _iconFile)
            {
                self._asyncOpen(_iconFile, _listener, _aContext);
            }.bind(self, listener, aContext)
        );
        if (alreadyQueued) return;
        
        var iconLib = getIconLib();
        var iconFile = "chrome://komodo/skin/images/sad.png";

        if (iconLib)
        {
            try
            {
                iconLib.getIconForUri(self.URI.spec, function(_iconFile)
                {
                    if ( ! (self.URI.spec in queued))
                    {
                        log.warn("Cannot callback, queue is empty: " + self.URI.spec);
                        return;
                    }
                    
                    log.debug("Callback: " + self.URI.spec);
                    
                    if (_iconFile) iconFile = _iconFile;
                    
                    for (let i=0;i<queued[self.URI.spec].length;i++)
                    {
                        queued[self.URI.spec][i](iconFile);
                    }
                    
                    delete queued[self.URI.spec];
                });
            }
            catch (e)
            {
                log.error("Unable to detect icon, falling back on default: " + e.message);
                if ("stack" in e)
                    log.error(e.stack);

                self._asyncOpen(iconFile, listener, aContext);
            }
        }
        else
        {
            log.error("Unable to load icon lib, falling back on default: " + e.message);
            self._asyncOpen(iconFile, listener, aContext);
        }

    },

    _asyncOpen: function(iconFile, listener, aContext)
    {
        var path = (typeof iconFile) == "string" ? iconFile : iconFile.path;
        log.debug("Async Opening: " + path);
        var channel = NetUtil.newChannel(iconFile);
        channel.asyncOpen(listener, aContext);
    },

    classID: Components.ID("{AF736A11-7D06-445A-9F6C-7E330D6508BA}"),
    QueryInterface: XPCOMUtils.generateQI([Ci.nsIChannel,
                                           Ci.nsIRequest])
};

function WrapperListener(listener, channel) {
    this.listener = listener;
    this.channel = channel;
}

WrapperListener.prototype = {
    onStartRequest: function(aRequest, aContext) {
        this.listener.onStartRequest(this.channel, aContext);
    },
    onStopRequest: function(aRequest, aContext, aStatusCode) {
        this.listener.onStopRequest(this.channel, aContext, aStatusCode);
    },
    onDataAvailable: function(aRequest, aContext, aInputStream, aOffset, aCount) {
        this.listener.onDataAvailable(this.channel, aContext, aInputStream,
                                      aOffset, aCount);
    },
    QueryInterface: XPCOMUtils.generateQI([Ci.nsIStreamListener,
                                           Ci.nsIRequestObserver]),
};

this.NSGetFactory = XPCOMUtils.generateNSGetFactory([IconProtocolHandler]);
