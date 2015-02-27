Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

function koInterfaceProxy() {}
function koKeyEventDefinition() {}

(function() {

    koInterfaceProxy.prototype =
    {
        classDescription:   "Act as an interface for Mozilla API's that are not exposed via XPCOM",
        classID:            Components.ID("{8B38FCD4-2035-44D2-B32F-68B1CFA780CF}"),
        contractID:         "@activestate.com/koInterfaceProxy;1",
        QueryInterface:     XPCOMUtils.generateQI([Components.interfaces.koIInterfaceProxy, Components.interfaces.nsIObserver]),

        unpackKeyEvent: function(event)
        {
            event = event.QueryInterface(Components.interfaces.nsIDOMKeyEvent);
            return JSON.stringify({
                DOM_VK_RETURN: event.DOM_VK_RETURN,
                DOM_VK_TAB: event.DOM_VK_TAB,
                keyCode: event.keyCode
            });
        }
    };

}.call());

var NSGetFactory = XPCOMUtils.generateNSGetFactory([koInterfaceProxy]);
