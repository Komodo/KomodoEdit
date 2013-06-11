if (koSkin.skinHasChanged)
{
    ko.prefs.setStringPref(
        koSkin.PREF_CUSTOM_ICONS,
        "chrome://iconset-radiance/content/manifest/chrome.manifest"
    );
}
