const {classes: Cc, interfaces: Ci, utils: Cu, results: Cr} = Components;

Cu.import("resource://gre/modules/NetUtil.jsm");
Cu.import("resource://gre/modules/Services.jsm");
Cu.import("resource://gre/modules/XPCOMUtils.jsm");
Cu.import("resource://gre/modules/FileUtils.jsm");

var koLess;

function LessProtocolHandler() {
}

LessProtocolHandler.prototype = {
    scheme: "less",
    defaultPort: -1,
    allowPort: function() false,
    protocolFlags:  Ci.nsIProtocolHandler.URI_IS_LOCAL_RESOURCE |
                    Ci.nsIProtocolHandler.URI_NON_PERSISTABLE |
                    Ci.nsIProtocolHandler.URI_SYNC_LOAD_IS_OK |
                    Ci.nsIProtocolHandler.URI_IS_UI_RESOURCE,

    newURI: function Proto_newURI(aSpec, aOriginCharset) {
        let uri = Cc["@mozilla.org/network/simple-uri;1"].createInstance(Ci.nsIURI);
        uri.spec = aSpec;
        return uri;
    },

    newChannel: function Proto_newChannel(aURI) {
        var channel = new LessChannel();

        channel._URI = aURI.spec.replace(/^less/, 'chrome');
        channel.name = aURI.spec;
        channel.originalURI = aURI;
        channel.URI = aURI;
        
        return channel;
    },

    classID: Components.ID("{6877A557-982B-469F-9689-D66A917BE4E4}"),
    QueryInterface: XPCOMUtils.generateQI([Ci.nsIProtocolHandler])
};

function LessChannel() {
}

LessChannel.prototype = {
    _URI: null,

    name: null,
    originalURI: null,
    URI: null,
    contentType: "text/css",
    contentCharset: "UTF-8",
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

    open: function() {
        try {
            if (!koLess) {
                koLess = Cu.import("chrome://komodo/content/library/less.js").koLess;
            }

            var file;
            koLess.loadSheet({href: this._URI}, function(_file) {
                file = _file;
            }, true); // isInternalCall

            if ( ! file) {
                file = NetUtil.newURI('data:text/plain,');
            }

            var channel = NetUtil.newChannel(file, null, null);
           
            this.contentType = channel.contentType;
            this.contentCharset = channel.contentCharset;

            if (channel.contentLength < 0) {
                // content length unknown; this *must* be known for the sync
                // load service to work...
                this.contentLength = file.fileSize;
            } else {
                this.contentLength = channel.contentLength;
            }

            return channel.open();
        } catch (ex) {
            Cu.reportError(ex);
            throw new Components.Exception("Failed to open stream",
                                           Cr.NS_ERROR_FAILURE);
        }
    },

    asyncOpen: function(aListener, aContext) {
        try {
            if (!koLess) {
                koLess = Cu.import("chrome://komodo/content/library/less.js").koLess;
            }

            var listener = new WrapperListener(aListener, this);

            koLess.loadSheet({href: this._URI}, function(file) {
                if ( ! file) {
                    file = NetUtil.newURI('data:text/plain,');
                }

                var channel = NetUtil.newChannel(file, null, null);

                this.contentType = channel.contentType;
                this.contentCharset = channel.contentCharset;
                this.contentLength = channel.contentLength;

                channel.asyncOpen(listener, aContext);
            }, true, true); // isInternalCall, async
        } catch (ex) {
            Cu.reportError(ex);
            throw new Components.Exception("Failed to open async stream",
                                           Cr.NS_ERROR_FAILURE);
        }
    },
    
    classID: Components.ID("{55DA7157-3B1C-43AB-98BA-0DB65A31AC9F}"),
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

this.NSGetFactory = XPCOMUtils.generateNSGetFactory([LessProtocolHandler]);
