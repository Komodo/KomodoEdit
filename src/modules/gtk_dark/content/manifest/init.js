if (koSkin.skinHasChanged)
{
    Components.utils.import("resource://gre/modules/Services.jsm");
    var file = Services.io.newURI("chrome://iconset-" +
                                  "light" +
                                  "/content/manifest/chrome.manifest", null,null)
                .QueryInterface(Components.interfaces.nsIFileURL).file;
    ko.prefs.setStringPref(koSkin.PREF_CUSTOM_ICONS, file.path);
}
