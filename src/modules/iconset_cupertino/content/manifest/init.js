if (koSkin.shouldFlushCaches)
{
    Services.prefs.setCharPref("general.skins.selectedSkin", "cupertino");
    ko.prefs.setString("iconset-base-defs", "cupertino");
    ko.prefs.setString("iconset-selected-defs", "cupertino-blue");
}
