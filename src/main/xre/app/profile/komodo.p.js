/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is mozilla.org code.
 *
 * The Initial Developer of the Original Code is 
 * Netscape Communications Corporation.
 * Portions created by the Initial Developer are Copyright (C) 1998
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   ActiveState Software Inc.
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or 
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

#filter substitution

# SYNTAX HINTS:  dashes are delimiters.  Use underscores instead.
#  The first character after a period must be alphabetic.

#ifdef XP_UNIX
#ifndef XP_MACOSX
#define UNIX_BUT_NOT_MAC
#endif
#endif

pref("toolkit.chromeURL","chrome://komodo/content/");
pref("browser.chromeURL","chrome://komodo/content/dialogs/browser.xul");
pref("toolkit.singletonWindowType", "Komodo");
#ifdef XP_MACOSX
// Special hidden window for the Mac, to allow file open dialog copy/paste.
// See bug 85838 for details.
pref("browser.hiddenWindowChromeURL","chrome://komodo/content/hiddenWindow.xul");
#endif

// Less delay for the Add-on install dialog.
pref("security.dialog_enable_delay", 500);

// Preferences for the Get Add-ons pane
pref("extensions.getAddons.showPane", true);
pref("extensions.getAddons.browseAddons", "http://komodoide.com/packages");
pref("extensions.getAddons.maxResults", 5);
pref("extensions.getAddons.recommended.browseURL", "http://komodoide.com/packages");
pref("extensions.getAddons.recommended.url", "http://komodoide.com/packages");
pref("extensions.getAddons.search.browseURL", "http://komodoide.com/packages");
pref("extensions.getAddons.search.url", "http://komodoide.com/packages");
pref("extensions.webservice.discoverURL", "");
// Blocklist preferences
pref("extensions.blocklist.enabled", false);

// App-specific update preferences

// Whether or not app updates are enabled
pref("app.update.enabled", PP_KO_APP_UPDATE_ENABLED);

// This preference turns on app.update.mode and allows automatic download and
// install to take place. We use a separate boolean toggle for this to make
// the UI easier to construct.
pref("app.update.auto", false);

// Update service URL:
pref("app.update.url", "https://komodo.activestate.com/update/2/%PRODUCT%/%VERSION%/%BUILD_ID%/PP_KO_PLATNAME/%LOCALE%/%CHANNEL%/update.xml");
// URL user can browse to manually if for some reason all update installation
// attempts fail.
pref("app.update.url.manual", "PP_KO_UPDATE_MANUAL_URL");
// A default value for the "More information about this update" link
// supplied in the "An update is available" page of the update wizard. 
pref("app.update.url.details", "PP_KO_UPDATE_MANUAL_URL");

// User-settable override to app.update.url for testing purposes.
//pref("app.update.url.override", "");

// Whether or not we show a dialog box informing the user that the update was
// successfully applied. This is off in Firefox by default since we show a 
// upgrade start page instead! Other apps may wish to show this UI, and supply
// a whatsNewURL field in their brand.properties that contains a link to a page
// which tells users what's new in this new update.
pref("app.update.showInstalledUI", false);

// Symmetric (can be overridden by individual extensions) update preferences.
// e.g.
//  extensions.{GUID}.update.enabled
//  extensions.{GUID}.update.url
//  extensions.{GUID}.update.interval
//  .. etc ..
//
pref("extensions.update.enabled", false);
pref("extensions.showMismatchUI", false);
// Change add-on auto updating to once every 5 days (default is 1 day), to
// lessen the community.as.com server load. Note that users can still bypass
// this by manually checking for updates via the add-on dialog.
pref("extensions.update.url", "");
// Non-symmetric (not shared by extensions) extension-specific [update] preferences
pref("extensions.getMoreExtensionsURL", "http://komodoide.com/packages");
pref("extensions.getMoreThemesURL", "http://komodoide.com/packages");
// Add-on metadata query (screenshots, description, ratings, downloads, ...)
// Not used by Komodo - and it actually causes our ads to be blocked - bug 97923.
pref("extensions.getAddons.cache.enabled", false);

pref("xpinstall.whitelist.add", "komodo.activestate.com");

pref("keyword.enabled", true);

pref("general.useragent.locale", "@AB_CD@");
pref("general.skins.selectedSkin", "classic/1.0");

#ifndef XP_WIN
// Show hidden files in the file picker; bug 81075
pref("filepicker.showHiddenFiles", true);
#endif

// Scripts & Windows prefs
pref("dom.disable_open_during_load",              true);
#ifdef DEBUG
pref("javascript.options.showInConsole",          true);
pref("general.warnOnAboutConfig",                 false);
#else
pref("javascript.options.showInConsole",          false);
#endif

// Make the status bar reliably present and unaffected by pages
pref("dom.disable_window_open_feature.status",    true);
// This is the pref to control the location bar, change this to true to 
// force this instead of or in addition to the status bar - this makes 
// the origin of popup windows more obvious to avoid spoofing. We would 
// rather not do it by default because it affects UE for web applications, but
// without it there isn't a really good way to prevent chrome spoofing, see bug 337344
pref("dom.disable_window_open_feature.location",  true);
pref("dom.disable_window_status_change",          true);
// allow JS to move and resize existing windows
pref("dom.disable_window_move_resize",            false);
// prevent JS from monkeying with window focus, etc
pref("dom.disable_window_flip",                   false);

pref("profile.allow_automigration", false);   // setting to false bypasses automigration in the profile code

// replace newlines with spaces when pasting into <input type="text"> fields
pref("editor.singleLine.pasteNewlines", 2);

// The breakpad report server to link to in about:crashes
pref("breakpad.reportURL", "http://crash-stats.activestate.com/report/index/");

// base URL for web-based support pages
pref("app.support.baseURL", "http://support.activestate.com/1/%APP%/%VERSION%/%OS%/%LOCALE%/");

// Disable the extension selection UI at startup - as this mostly contains
// ActiveState add-ons included in the base installation - which we don't want
// the user to uninstall.
pref("extensions.shownSelectionUI", true);

// Allow for skin switching during runtime
pref("extensions.dss.enabled", true);

// Used for the Help window
pref("accessibility.typeaheadfind.flashBar", 1);

// Required for "Web & Browser > Proxy" preferences.
#ifdef XP_WIN
pref("browser.preferences.instantApply", false);
#else
pref("browser.preferences.instantApply", true);
#endif

#ifdef XP_MACOSX
// Horizontal scroll is broken for high-precision scrolling (Mighty Mouse,
// new trackpads) when pixel-scrolling; see bug 97964
pref("mousewheel.enable_pixel_scrolling", false);
#endif

// Disable unresponsive script checking - bug 91614.
pref("dom.max_chrome_script_run_time", 0);

#ifdef MOZ_WIDGET_GTK
// On GTK, we now default to showing the menubar only when alt is pressed:
pref("ui.key.menuAccessKeyFocuses", true);
#endif

// Set plugins as "click to play" by default.
pref("plugins.click_to_play", true);
pref("plugin.default.state", 1);
// Enable scimoz (yes, we give it a different name on each platform!).
pref("plugin.state.scimoz", 2);
pref("plugin.state.npscimoz", 2);
pref("plugin.state.libnpscimoz", 2);
