if (koSkin.iconsetHasChanged)
{
    var prefs = Components.classes['@mozilla.org/preferences-service;1']
                .getService()
                .QueryInterface(Components.interfaces.nsIPrefBranch);
    prefs.setStringPref("general.skins.selectedSkin", "orange");
}