if (koSkin.skinHasChanged)
{
    ko.prefs.setStringPref(
        koSkin.PREF_CUSTOM_ICONS,
        "chrome://iconset-ambiance/content/manifest/chrome.manifest"
    );
}
