if (koSkin.shouldFlushCaches)
{
    ko.prefs.setStringPref(
        koSkin.PREF_CUSTOM_ICONS,
        "chrome://iconset-classic/content/manifest/chrome.manifest"
    );
}
