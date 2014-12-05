if (koSkin.shouldFlushCaches)
{
    Services.prefs.setCharPref("general.skins.selectedSkin", "ambiance");
    ko.prefs.setString("iconset-base-color", "#4B4B4B");
    ko.prefs.setString("iconset-toolbar-color", "#C8C8C8");
    ko.prefs.setString("iconset-selected-color", "#EB845A");
}
