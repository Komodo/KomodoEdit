const {classes: Cc, interfaces: Ci, utils: Cu, results: Cr} = Components;

Cu.import("resource://gre/modules/Services.jsm");
Cu.import("resource://gre/modules/XPCOMUtils.jsm");

var koLess;

function LessProtocolHandler() {
}

LessProtocolHandler.prototype = {
    scheme: "less",
    defaultPort: -1,
    allowPort: function() false,
    protocolFlags:  Ci.nsIProtocolHandler.URI_IS_LOCAL_RESOURCE |
                    Ci.nsIProtocolHandler.URI_NON_PERSISTABLE |
                    Ci.nsIProtocolHandler.URI_SYNC_LOAD_IS_OK,

    newURI: function Proto_newURI(aSpec, aOriginCharset) {
        let uri = Cc["@mozilla.org/network/simple-uri;1"].createInstance(Ci.nsIURI);
        uri.spec = aSpec;
        return uri;
    },

    newChannel: function Proto_newChannel(aURI) {
        var URI = Services.io.newURI(aURI.spec.replace(/^less/, 'chrome'), null, null);

        var channel = new LessChannel();
        channel.name = URI.spec;
        channel.originalURI = URI;
        channel.URI = URI;
        
        return channel;
    },

    classID: Components.ID("{6877A557-982B-469F-9689-D66A917BE4E4}"),
    QueryInterface: XPCOMUtils.generateQI([Ci.nsIProtocolHandler])
};

function LessChannel() {
}

LessChannel.prototype = {
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

    asyncOpen: function(aListener, aContext) {
        if ( ! koLess) koLess = Cu.import("chrome://komodo/content/library/less.js").koLess;

        var listener = new WrapperListener(aListener, this);

        koLess.loadSheet({href: this.URI.spec}, function(file) {
            this.contentLength = file.fileSize;
            var uri = Services.io.newFileURI(file);
            var channel = Services.io.newChannelFromURI(uri);

            this.contentType = channel.contentType;
            this.contentCharset = channel.contentCharset;
            this.contentLength = channel.contentLength;

            channel.asyncOpen(listener, aContext);
        }.bind(this), true);
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
