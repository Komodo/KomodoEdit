if (koSkin.skinHasChanged)
{
    ko.prefs.setStringPref(
        koSkin.PREF_CUSTOM_ICONS,
        "chrome://iconset-light/content/manifest/chrome.manifest"
    );
}
