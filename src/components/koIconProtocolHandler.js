const {classes: Cc, interfaces: Ci, utils: Cu, results: Cr} = Components;

Cu.import("resource://gre/modules/XPCOMUtils.jsm");
Cu.import("resource://gre/modules/Services.jsm");
Cu.import("resource://gre/modules/NetUtil.jsm");

var loggingSvc = Cc["@activestate.com/koLoggingService;1"].
                    getService(Ci.koILoggingService);
var log = this.loggingSvc.getLogger('koiconprotocol');

var getFileIconLib = function()
{
    if ( ! ("cached" in getFileIconLib))
    {
        var windows = Services.wm.getEnumerator("Komodo");
        while (windows.hasMoreElements())
        {
            let window = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
            getFileIconLib.cached = window.require("ko/fileicons");
            break;
        }
    }

    if ( ! ("cached" in getFileIconLib))
        log.error("Could not find main komodo window");

    return getFileIconLib.cached;
}

function IconProtocolHandler() {
}

IconProtocolHandler.prototype = {
    scheme: "koicon",
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
        var iconLib = getFileIconLib();
        var iconFile = aURI.spec.replace(/^koicon/, 'moz-icon');

        if (iconLib)
        {
            try
            {
                var _iconFile = iconLib.getIconForUri(aURI.spec);
                iconFile = _iconFile;
            }
            catch (e)
            {
                log.error("Unable to detect icon, falling back on moz-icon: " + e.message);
                if ("stack" in e)
                    log.error(e.stack);
            }
        }

        return NetUtil.newChannel(iconFile);
    },

    classID: Components.ID("{A840147B-5194-49B5-A0D5-CF5E3F87CDC5}"),
    QueryInterface: XPCOMUtils.generateQI([Ci.nsIProtocolHandler])
};

this.NSGetFactory = XPCOMUtils.generateNSGetFactory([IconProtocolHandler]);
