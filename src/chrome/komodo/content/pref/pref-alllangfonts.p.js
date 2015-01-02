/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
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

/* Left to do in order of priority
  - Test on linux
*/

xtk.include("domutils");
var enumerator = Components.classes["@mozilla.org/gfx/fontenumerator;1"].createInstance();
if( enumerator )
    enumerator = enumerator.QueryInterface(Components.interfaces.nsIFontEnumerator);

var gDialog;
var log = ko.logging.getLogger('pref-allfonts');

var gFontTypes   = ["serif","sans-serif", /*"cursive", "fantasy",*/"monospace"];
var gFontLanguages = ['x-western','x-central-euro','ja','zh-TW',
                      'zh-CN','zh-HK','ko','x-cyrillic','x-baltic','el',
                      'tr','x-unicode','x-user-def','th','he','ar',
                      'x-devanagari','x-tamil'];
var gFontNames;

var gLanguageRegistry = Components.classes["@activestate.com/koLanguageRegistryService;1"]
            .getService(Components.interfaces.koILanguageRegistryService);
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"].
            getService(Components.interfaces.nsIStringBundleService).
            createBundle("chrome://komodo/locale/pref/pref-alllangfonts.properties");

function PrefLangFonts_OnLoad()  {
    try {
        scintillaOverlayOnLoad();

        gDialog = initDialog();
        gDialog.bufferView.initWithBuffer("", "Text");
        onSampleBlur();
        parent.hPrefWindow.onpageload();
    } catch (e) {
        log.error(e);
    }
}

function PrefLangFonts_OnUnload()  {
    try {
        var view = document.getElementById('sample');
        // The "close" method ensures the scintilla view is properly cleaned up.
        view.close();
        scintillaOverlayOnUnload();
    } catch (e) {
        log.error(e);
    }
}

function initDialog() {
    // Get a handle on the UI widgets
    var dialog = {};
    dialog.modified = false;
    dialog.bufferView = document.getElementById('sample');
    dialog.deleteButton = document.getElementById('deleteScheme');
    dialog.schemeslist = document.getElementById('schemeslist');
    dialog.schemespopup = document.getElementById('schemespopup');
    dialog.fixedOrPropMenu = document.getElementById('fixedOrPropMenu');
    dialog.fontList = document.getElementById('fontlist');
    dialog.fontSize = document.getElementById('fontSize');
    dialog.fontBold = document.getElementById('fontBold');
    dialog.fontItalic = document.getElementById('fontItalic');
    dialog.fontColorPickerFore = document.getElementById('fontColorPickerFore');
    dialog.fontColorPickerBack = document.getElementById('fontColorPickerBack');
    dialog.fontLineSpacing = document.getElementById('fontLineSpacing');
    dialog.tabbox = document.getElementById('tabbox');
    dialog.current_tab_id = null;
    // second tab: colors
    dialog.extracolors = document.getElementById('extracolors');
    dialog.schemeColorPicker = document.getElementById('schemeColorPicker');
    dialog.useSelFore = document.getElementById('useSelFore');
    dialog.caretLineVisible = document.getElementById('caretLineVisible');
    // third tab: common
    dialog.commonlist = document.getElementById('commonlist')
    dialog.commonFore = document.getElementById('commonColorPickerFore')
    dialog.commonBack = document.getElementById('commonColorPickerBack')
    dialog.commonSize = document.getElementById('commonSize');
    dialog.commonFaceType = document.getElementById('fixedOrPropCommon');
    dialog.commonBold = document.getElementById('commonBold')
    dialog.commonItalic = document.getElementById('commonItalic')
    // fourth tab: specific
    dialog.specificlist = document.getElementById('specificlist')
    dialog.specificFore = document.getElementById('specificColorPickerFore')
    dialog.specificBack = document.getElementById('specificColorPickerBack')
    dialog.specificBackBySubLanguage = document.getElementById('specificColorPickerSubLanguageBack');
    dialog.useGlobalSubLanguageBackground = document.getElementById('useGlobalSubLanguageBackground');
        
    dialog.specificBold = document.getElementById('specificBold')
    dialog.specificItalic = document.getElementById('specificItalic')
    dialog.languageList = document.getElementById('languageList');
    dialog.specificSize = document.getElementById('specificSize');
    dialog.specificFaceType = document.getElementById('fixedOrPropSpecific');
    // fifth tab: indicators
    dialog.indicator_menulist = document.getElementById('indicator_menulist');
    dialog.indicator_style_menulist = document.getElementById('indicator_style_menulist');
    dialog.indicator_alpha_textbox = document.getElementById('indicator_alpha_textbox');
    dialog.indicator_color = document.getElementById('indicator_color');
    dialog.indicator_draw_underneath_checkbox = document.getElementById('indicator_draw_underneath_checkbox');


    return dialog;
}

function SetDefaultLanguage() {
    try {
        var prefset = gDialog.prefset;
        var selectedLanguageName;
        var p = "prefs.fontsColorsLanguages.langSpecific.lang";
        try {
            if (prefset.hasStringPref(p)) {
                selectedLanguageName = prefset.getStringPref(p);
            } else {
                selectedLanguageName = getKoObject('views').manager.currentView.koDoc.language;
            }
        } catch(ex) {
            selectedLanguageName = "Python";
        }
        // Verify the language exists
        var ok;
        try {
            let koLang = gLanguageRegistry.getLanguage(selectedLanguageName);
            ok = !!koLang;
            if (ok) {
                // The language service can return a language that has a
                // different name (i.e. "Python" when the language does not exist).
                selectedLanguageName = koLang.name;
            }
        } catch(ex) {
            ok = false;
        }
        if (!ok) {
            selectedLanguageName = "Python";
        }
        gDialog.currentLanguage = selectedLanguageName;
        var schemeName = prefset.getStringPref('editor-scheme');
        gDialog.schemeService = Components.classes['@activestate.com/koScintillaSchemeService;1'].getService()
        gDialog.currentScheme = gDialog.schemeService.getScheme(schemeName);
        gDialog.languageList.selection = selectedLanguageName;
    } catch (e) {
        log.error(e);
    }
}

function OnPreferencePageLoading(prefset) {
    try {
        generateFontList();
        gDialog.prefset = prefset;
        SetDefaultLanguage();
        var scimoz = gDialog.bufferView.scimoz;
        // Hide all margins.
        for (var i=0; i <= scimoz.SC_MAX_MARGIN; i++) {
            scimoz.setMarginWidthN(i, 0);
        }

        setupSchemes();

        var listElement;
        var p = "prefs.fontsColorsLanguages.whichTab";
        if (prefset.hasLongPref(p)) {
            gDialog.tabbox.selectedIndex = prefset.getLongPref(p);
        }

        p = "prefs.fontsColorsLanguages.colors.extraColors";
        if (prefset.hasLongPref(p)) {
            listElement = document.getElementById("extracolors");
            listElement.selectedIndex = prefset.getLongPref(p);
            if (listElement.selectedIndex == -1) {
                listElement.selectedIndex = 0;
            }
        }
        initFontsMenulist();
        changeLanguage();
        updateFromScheme();
        loadColorpickerPreferences(prefset);
    } catch (e) {
        log.exception(e);
    }
}

function _saveCurrentState(prefset) {
    try {
        prefset.setLongPref("prefs.fontsColorsLanguages.whichTab",
                            gDialog.tabbox.selectedIndex);
        prefset.setStringPref("prefs.fontsColorsLanguages.langSpecific.lang",
                              document.getElementById("languageList").selection);
        prefset.setLongPref("prefs.fontsColorsLanguages.langSpecific.elementTypeIndex",
                            document.getElementById("specificlist").selectedIndex);
        prefset.setLongPref("prefs.fontsColorsLanguages.colors.extraColors",
                            document.getElementById("extracolors").selectedIndex);
        prefset.setLongPref("prefs.fontsColorsLanguages.common.elementList",
                            document.getElementById("commonlist").selectedIndex);
        prefset.setLongPref("prefs.fontsColorsLanguages.indicators.menulist",
                            document.getElementById("indicator_menulist").selectedIndex);

    } catch(ex) {
        dump("_saveCurrentState: exception: " + ex + "\n");
    }
}

function _restorePopupMenuIndex(menuList, labels, pref) {
    if (gDialog.prefset.hasLongPref(pref)) {
        menuList.selectedIndex = gDialog.prefset.getLongPref(pref);
        if (menuList.selectedIndex == -1) {
            menuList.value = labels[0];
        }
    } else {
        menuList.value = labels[0];
    }
}

/**
 * Save the position prefs in this routine so they're captured,
 * even if the user pressed Cancel.
 * Ref bug 83357
 */
function OnPreferencePageClosing(prefset, leavingOnOK) {
    _saveCurrentState(prefset);
}

function OnPreferencePageOK(prefset)  {
    var log = ko.logging.getLogger('pref-allfonts');
    try {
        var schemeName = gDialog.currentScheme.name;
        // If we are dealing with a new scheme or a scheme we've changed, then save it.
        if (gDialog.currentScheme.unsaved || gDialog.currentScheme.isDirty) {
            gDialog.currentScheme.save()
        }
        var oldScheme = prefset.getStringPref('editor-scheme');
        if (oldScheme != schemeName) {
            prefset.setStringPref('editor-scheme', schemeName);
        } else if (gDialog.modified) {
            var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                            getService(Components.interfaces.nsIObserverService);
            observerSvc.notifyObservers(this, 'scheme-changed', schemeName);
        }
        return true;
    } catch(e) {
        log.exception(e);
        var message = _bundle.formatStringFromName("attemptToSaveSchemeFailed.format",
                                                   [schemeName], 1);
        return ignorePrefPageOKFailure(prefset, message, e.toString());
    }
}

function OnPreferencePageCancel(prefset)  {
    try {
        var schemeName = gDialog.currentScheme.name;
        // If we've modified an existing scheme, revert it
        if (!gDialog.currentScheme.unsaved && gDialog.currentScheme.isDirty) {
            gDialog.currentScheme.revert();
        }
        var schemeService = Components.classes['@activestate.com/koScintillaSchemeService;1'].getService();
        schemeService.purgeUnsavedSchemes();
    } catch (e) {
        log.exception(e);
    }
    return true;
}

function loadSample()
{
    var language = gDialog.currentLanguage;
    var sample = gLanguageRegistry.getLanguage(language).sample;
    if (! sample) {
        sample = "No sample for " + language + " available.";
    }
    gDialog.bufferView.setBufferText(sample);
    gDialog.bufferView.language = language;
    gDialog.bufferView.anchor = sample.length/4;
    gDialog.bufferView.currentPos = sample.length/2;
}

function onSampleClick()
{
    onPosChanged(gDialog.bufferView.scimoz.currentPos);
}

function onPosChanged(position)
{
    // As of Scintilla 2.0.2, the only way to get to this function
    // is via a mouse click.  But the onPosChanged callback wasn't
    // working, and was implemented incorrectly anyway.
    try {
        var styleno = gDialog.bufferView.scimoz.getStyleAt(position);
        var common = gDialog.currentScheme.getCommonName(gDialog.currentLanguage,
                                                        styleno);
        if (common) {
            gDialog.commonlist.value = common;
            updateCommonStyle();
        }
        var specific = gDialog.currentScheme.getSpecificName(gDialog.currentLanguage,
                                                            styleno);
        if (specific) {
            gDialog.specificlist.value = specific;
            updateSpecificStyle();
        }
    } catch (e) {
        log.error(e);
    }
}

// This function builds the 'scheme' menulist from the schemeservice
function setupSchemes()
{
    try {
        var schemes = new Array();
        gDialog.schemeService.getSchemeNames(schemes, new Object());
        var menuitem;
        var s, scheme;
        for (var i = 0; i < schemes.value.length; i++) {
            scheme = schemes.value[i];
            menuitem = document.createElement('menuitem');
            s = gDialog.schemeService.getScheme(scheme);
            if (!s) {
                continue;
            }
            if (! s.writeable) {
                menuitem.setAttribute('class','primary_menu_item');
            }
            menuitem.setAttribute('label', scheme);
            menuitem.setAttribute('id', scheme);
            menuitem.setAttribute('value', scheme);
            gDialog.schemespopup.appendChild(menuitem);
        }
        gDialog.schemeslist.value = gDialog.currentScheme.name;
    } catch (e) {
        log.error(e);
    }
}

function updateDelete()
{
    if (gDialog.currentScheme.writeable) {
        if (gDialog.deleteButton.hasAttribute('disabled')) {
            gDialog.deleteButton.removeAttribute('disabled');
        }
    } else {
        gDialog.deleteButton.setAttribute('disabled', 'true');
    }
}

function updateFromScheme()
{
    try {
        gDialog.fixedOrPropMenu.value = (gDialog.currentScheme.preferFixed ? "1" : "0");
        gDialog.useSelFore.setAttribute('checked',
                                        gDialog.currentScheme.useSelFore);
        updateMenuitemAndCheckbox('useSelFore', 'selFore', false);
        gDialog.caretLineVisible.setAttribute('checked',
                                             gDialog.currentScheme.caretLineVisible);
        updateMenuitemAndCheckbox('caretLineVisible', 'caretLineBack', false);
        updateScintilla();
        updateSchemeColor(gDialog.extracolors.selectedItem.getAttribute('id'));
        updateFonts();
        updateDelete();
        updateCommonPopup();
        updateSpecificPopup();
        updateIndicatorPopup();
    } catch (e) {
        log.error(e);
    }
}

function updateScintilla()
{
    var scheme = gDialog.currentScheme;
    var scintilla = gDialog.bufferView.scimoz;
    var encoding = 'unused';
    var alternateType = false;
    scheme.applyScheme(scintilla, gDialog.currentLanguage, encoding, alternateType);
}

function preferFixed(truefalse)
{
    if (!ensureWriteableScheme()) return;
    gDialog.currentScheme.preferFixed = truefalse;
    updateScintilla();
}

function setColour(colorpicker)
{
    var colorid;
    var color = colorpicker.color;
    var colorpickerid = colorpicker.getAttribute('id')
    if (!ensureWriteableScheme()) {
        return;
    }
    if (colorpickerid == 'schemeColorPicker') {
        colorid = gDialog.extracolors.selectedItem.getAttribute('id')
        gDialog.currentScheme.setColor(colorid, color);
        updateScintilla();
    } else if (colorpickerid == 'indicator_color') {
        setIndicator();
        return;
    } else {
        colorid = colorpickerid;
        switch (colorid) {
            case 'fontColorPickerFore':
                gDialog.currentScheme.setFore('', faceIdentifier(1), color);
                break;
            case 'fontColorPickerBack':
                gDialog.currentScheme.setBack('', faceIdentifier(1), color);
                break;
            case 'commonColorPickerFore':
                gDialog.currentScheme.setFore('',
                                             gDialog.currentCommonStyle,
                                             color);
                break;
            case 'commonColorPickerBack':
                gDialog.currentScheme.setBack('',
                                             gDialog.currentCommonStyle,
                                             color);
                break;
            case 'specificColorPickerFore':
                gDialog.currentScheme.setFore(gDialog.currentLanguage,
                                             gDialog.currentSpecificStyle,
                                             color);
                break;
            case 'specificColorPickerBack':
                gDialog.currentScheme.setBack(gDialog.currentLanguage,
                                             gDialog.currentSpecificStyle,
                                             color);
                break;
            case 'specificColorPickerSubLanguageBack':
                gDialog.currentScheme.setSubLanguageDefaultBackgroundColor(gDialog.currentLanguage,
                                             color);
                break;
            default:
                log.error("setColour called with unknown colorid: " + colorid);
        }
        updateScintilla();
        updateCommonStyle();
    }
}

function setLineSpacing(fontStyle)
{
    if (!ensureWriteableScheme()) return;

    var style = faceIdentifier();
    var value = gDialog.fontLineSpacing.value;
    gDialog.currentScheme.setLineSpacing(style, value);
    updateScintilla();
    updateCommonStyle();
}

function onClickBoldOrItalic(button)
{
    try {
        if (!ensureWriteableScheme()) {
            // undo the change
            if (button.hasAttribute('checked')) {
                button.removeAttribute('checked');
            } else {
                button.setAttribute('checked', 'true');
            }
            return;
        }
        var updateCommon = false;
        var updateSpecific = false;
        var id = button.getAttribute('id');
        var checked = button.hasAttribute('checked') ? true : false;
        switch (id) {
            case 'fontBold':
                gDialog.currentScheme.setBold('',
                                             faceIdentifier(1),
                                             checked);
                updateCommon = true;
                break;
            case 'fontItalic':
                gDialog.currentScheme.setItalic('',
                                               faceIdentifier(1),
                                               checked);
                updateCommon = true;
                break;
            case 'commonItalic':
                gDialog.currentScheme.setItalic('',
                                               gDialog.currentCommonStyle,
                                               checked);
                updateSpecific = true;
                break;
            case 'commonBold':
                gDialog.currentScheme.setBold('',
                                             gDialog.currentCommonStyle,
                                             checked);
                updateSpecific = true;
                break;
            case 'specificItalic':
                gDialog.currentScheme.setItalic(gDialog.currentLanguage,
                                               gDialog.currentSpecificStyle,
                                               checked);
                break;
            case 'specificBold':
                gDialog.currentScheme.setBold(gDialog.currentLanguage,
                                             gDialog.currentSpecificStyle,
                                             checked);
                break;
        }
        updateScintilla();
        if (updateCommon) {
            updateCommonStyle();
        } else if (updateSpecific) {
            updateSpecificStyle();
        }
    } catch (e) {
        log.error(e);
    }
}

function onChangeFont()
{
    try {
        if (!ensureWriteableScheme()) return;
        var face = gDialog.fontList.value;
        gDialog.currentScheme.setFont(faceIdentifier(1), face);
        updateScintilla();
    } catch (e) {
        log.error(e);
    }
}

function onChangeFontSize()
{
    try {
        if (!ensureWriteableScheme()) return;
        var size = gDialog.fontSize.value;
        gDialog.currentScheme.setSize('', faceIdentifier(1), size);
        updateScintilla();
    } catch (e) {
        log.error(e);
    }
}

function onClickCommonSize()
{
    try {
        if (!ensureWriteableScheme()) return;
        var size = gDialog.commonSize.value;
        gDialog.currentScheme.setSize('',
                                     gDialog.currentCommonStyle,
                                     size);
        updateScintilla();
        updateSpecificStyle();
    } catch (e) {
        log.error(e);
    }
}

function onClickSpecificSize()
{
    try {
        if (!ensureWriteableScheme()) return;
        var size = gDialog.specificSize.value;
        gDialog.currentScheme.setSize(gDialog.currentLanguage,
                                     gDialog.currentSpecificStyle,
                                     size);
        updateScintilla();
    } catch (e) {
        log.error(e);
    }
}
function schemePick(event) {
    try {
        // If the current menuitem is the 'blank' one, then delete it
        // -- the scheme will get deleted automatically.
        gDialog.currentScheme = gDialog.schemeService.getScheme(gDialog.schemeslist.value);
        updateFromScheme();
    } catch (e) {
        log.error(e);
    }
}

function doDelete()
{
    try {
        var name = gDialog.currentScheme.name
        if (ko.dialogs.yesNo("Are you sure you want to delete the scheme '" + name +"'?  This action cannot be undone.") == 'No') {
            return;
        }
        gDialog.currentScheme.remove();
        gDialog.currentScheme = gDialog.schemeService.getScheme('Default');
        var oldScheme = gDialog.prefset.getStringPref('editor-scheme');
        if (oldScheme == name) {
            // we _must_ change the pref, since that scheme is gone even before the OK.
            gDialog.prefset.setStringPref('editor-scheme', 'Default');
            // We must do it on the global pref set because of the pref dialog's handling of prefs--
            // our prefset is ignored on Cancel.
            Components.classes["@activestate.com/koPrefService;1"].
                getService(Components.interfaces.koIPrefService).prefs.setStringPref('editor-scheme', 'Default');
        }
        // need to remove it from the popup
        var menuitem = document.getElementById(name);
        menuitem.parentNode.removeChild(menuitem);
        gDialog.schemeslist.value = gDialog.currentScheme.name
        updateFromScheme();
    } catch (e) {
        log.exception(e);
    }
}

function doNew()
{
    try {
        if (gDialog.currentScheme.unsaved) {
            var answer = ko.dialogs.yesNoCancel("Save current scheme before creating new one?");
            if (answer == "Cancel") {
                return false;
            }
            if (answer == "Yes") {
                gDialog.currentScheme.save()
            }
        }
        var newSchemeName;
        var schemes = {};
        gDialog.schemeService.getSchemeNames(schemes, {});
        schemes = schemes.value;
        var _viewsBundle = Components.classes["@mozilla.org/intl/stringbundle;1"].
            getService(Components.interfaces.nsIStringBundleService).
            createBundle("chrome://komodo/locale/views.properties");
        while (1) {
            var msg = _viewsBundle.formatStringFromName(
                "enterNewSchemeNameBasedOnScheme.template",
                [gDialog.currentScheme.name], 1);
            newSchemeName = ko.dialogs.prompt(msg,
                _viewsBundle.GetStringFromName("newSchemeName.label"),
                                              newSchemeName // default value
                                              );
            if (!newSchemeName) {
                return false;
            }
            // Check to make sure that the name isn't already taken and that it can be written to disk.
            if (schemes.indexOf(newSchemeName) >= 0) {
                msg = (_viewsBundle.formatStringFromName(
                       "schemeExists.template",
                       [newSchemeName], 1));
            } else if (!gDialog.schemeService.schemeNameIsValid(newSchemeName)) {
                msg = (_viewsBundle.formatStringFromName(
                       "schemeNameHasInvalidCharacters.template",
                       [newSchemeName], 1))
            } else {
                break;
            }
            alert(msg);
        }

        var newScheme = gDialog.currentScheme.clone(newSchemeName);
        var menuitem = document.createElement('menuitem');
        menuitem.setAttribute('label', newSchemeName);
        menuitem.setAttribute('id', newSchemeName);
        menuitem.setAttribute('value', newSchemeName);
        gDialog.schemespopup.appendChild(menuitem);
        gDialog.schemeslist.selectedItem = menuitem;
        gDialog.currentScheme = newScheme;
        updateScintilla();
        updateDelete();
        return true;
    } catch (e) {
        log.exception(e);
    }
    return false;
}

function ensureWriteableScheme()
{
    if (gDialog.currentScheme.writeable) {
        // Nothing to do, the current scheme can handle it.
        gDialog.modified = true;
        return true;
    }
    if (!doNew()) {
        updateFromScheme();
        return false;
    } else {
        gDialog.modified = true;
        return true;
    }
}

function pickFaceType(menulist)
{
    try {
        if (!ensureWriteableScheme()) return;
        var id = menulist.getAttribute('id');
        var useFixed = menulist.selectedItem.getAttribute('value') == '1';
        if (id == 'fixedOrPropCommon') {
            gDialog.currentScheme.setFaceType('',
                                             gDialog.currentCommonStyle,
                                             useFixed);
        } else {
            gDialog.currentScheme.setFaceType(gDialog.currentLanguage,
                                             gDialog.currentSpecificStyle,
                                             useFixed);
        }
        updateScintilla();
        updateCommonStyle();
    } catch (e) {
        log.error(e);
    }
}

function onResetCommon(event)
{
    try {
        if (!ensureWriteableScheme()) return;
        gDialog.currentScheme.resetStyle('',
                                        gDialog.currentCommonStyle);
        updateScintilla();
        updateCommonStyle();
    } catch (e) {
        log.error(e);
    }
}

function onResetSpecific(event)
{
    try {
        if (!ensureWriteableScheme()) return;
        gDialog.currentScheme.resetStyle(gDialog.currentLanguage,
                                        gDialog.currentSpecificStyle);
        updateScintilla();
        updateSpecificStyle();
    } catch (e) {
        log.error(e);
    }
}


function toggleMenuitem(checked, menuid)
{
    var menuitem = document.getElementById(menuid);
    if (checked) {
        if (menuitem.hasAttribute('disabled')) {
            menuitem.removeAttribute('disabled');
        }
    } else {
        menuitem.setAttribute('disabled', 'true');
        if (gDialog.extracolors.selectedItem == menuitem) {
            gDialog.extracolors.selectedItem = document.getElementById('caretFore');
            updateSchemeColor('caretFore')
        }
    }
}

function updateMenuitemAndCheckbox(checkboxid, menuid, updateScheme)
{
    try {
        var checkbox = document.getElementById(checkboxid);
        var checked = checkbox.getAttribute('checked') == "true";
        toggleMenuitem(checked, menuid);
        if (updateScheme) {
            // gDialog.currentScheme[checkboxid] = checked;
            switch (checkboxid) {
                case 'useSelFore':
                    gDialog.currentScheme.useSelFore = checked;
                    break;
                case 'caretLineVisible':
                    gDialog.currentScheme.caretLineVisible = checked;
                    break;
                default:
                    log.exception("got updateMenuitemAndCheckbox with unknown checkboxid: "+ checkboxid);
            }
        }
    } catch (e) {
        log.error(e);
    }
}

function clickCheckbox(id, menuid)
{
    try {
        if (!ensureWriteableScheme()) return;
        updateMenuitemAndCheckbox(id, menuid, true);
        updateScintilla();
    } catch (e) {
        log.error(e);
    }
}

function updateCommonPopup()
{
    try{
        var labels = new Array();
        gDialog.schemeService.getCommonStyles(labels, new Object());
        labels = labels.value;
        var popup = document.getElementById('commonpopup');
        // clean out whatever may be there
        while (popup.firstChild) {
            popup.removeChild(popup.firstChild);
        }
        for (var i=0; i< labels.length; i++) {
            var item = document.createElement('menuitem');
            item.setAttribute('value',labels[i]);
            item.setAttribute('label',labels[i]);
            popup.appendChild(item);
        }
        _restorePopupMenuIndex(gDialog.commonlist, labels,
                               "prefs.fontsColorsLanguages.common.elementList");
        updateCommonStyle();
    } catch (e) {
        log.error(e);
    }
}

function updateSpecificPopup()
{
    try{
        // Grab a list of available styles.
        var labels = new Array();
        gDialog.schemeService.getLanguageStyles(gDialog.currentLanguage, labels, new Object());
        labels = labels.value;
        var popup = document.getElementById('specificpopup');
        // Remove whatever is in the menu
        var children = popup.childNodes;
        var i, child
        // We start by cleaning out old menu items (keeping the 'keep' marked ones)
        for (i = children.length-1; i >= 0; i--) {
            child = children[i];
            popup.removeChild(child);
        }
        // Now we add what this language needs.
        for (i = 0; i < labels.length; i++) {
            var item = document.createElement('menuitem');
            item.setAttribute('value',labels[i]);
            item.setAttribute('label',labels[i]);
            popup.appendChild(item);
        }
        _restorePopupMenuIndex(gDialog.specificlist, labels,
                               "prefs.fontsColorsLanguages.langSpecific.elementTypeIndex");
        updateSpecificStyle();
    } catch (e) {
        log.error(e);
    }
}

function updateCommonStyle()
{
    try {
        var style = gDialog.currentCommonStyle = document.getElementById('commonlist').value;
        if (!style) {
            return;
        }
        var fore, back, bold, italic, facetype, size;
        fore = gDialog.currentScheme.getFore('', style);
        gDialog.commonFore.color = fore;
        back = gDialog.currentScheme.getBack('', style);
        gDialog.commonBack.color = back;
        bold = gDialog.currentScheme.getBold('', style);
        setCheckboxButton(gDialog.commonBold, bold);
        italic = gDialog.currentScheme.getItalic('', style);
        setCheckboxButton(gDialog.commonItalic, italic);
        size = gDialog.currentScheme.getSize('', style);
        gDialog.commonSize.value = size;
        var useFixed = gDialog.currentScheme.getFaceType('', style);
        //dump("got useFixed = " + useFixed + '\n');
        gDialog.commonFaceType.selectedIndex = 1-useFixed;
        //ko.logging.dumpDOM(gDialog.commonFaceType);
        // Whenever the common style may have changed, the specific style may have changed
        updateSpecificStyle();
    } catch (e) {
        log.error(e);
    }
}

function setCheckboxButton(element, checked)
{
    //ko.logging.dumpDOM(element);
    if (checked) {
        //element.setAttribute('checkState', '1');
        element.setAttribute('checked', 'true');
    } else {
        //element.setAttribute('checkState', '0');
        if (element.hasAttribute('checked')) {
            element.removeAttribute('checked');
        }
    }
}

function updateSpecificStyle()
{
    var style = gDialog.currentSpecificStyle = document.getElementById('specificlist').value;
    if (!style) return;
    var fore, back, bold, italic, facetype, size;
    fore = gDialog.currentScheme.getFore(gDialog.currentLanguage, style);
    gDialog.specificFore.color = fore;
    back = gDialog.currentScheme.getBack(gDialog.currentLanguage, style);
    gDialog.specificBack.color = back;
    gDialog.specificBackBySubLanguage.color = 
                gDialog.currentScheme.getSubLanguageDefaultBackgroundColor(gDialog.currentLanguage);
    gDialog.useGlobalSubLanguageBackground.checked = 
        gDialog.currentScheme.getGlobalSubLanguageBackgroundEnabled(gDialog.currentLanguage);
    updateSubLanguageBackgroundField(gDialog.useGlobalSubLanguageBackground);
                               
    bold = gDialog.currentScheme.getBold(gDialog.currentLanguage, style);
    setCheckboxButton(gDialog.specificBold, bold);
    italic = gDialog.currentScheme.getItalic(gDialog.currentLanguage, style);
    setCheckboxButton(gDialog.specificItalic, italic);
    size = gDialog.currentScheme.getSize(gDialog.currentLanguage, style);
    gDialog.specificSize.value = size;
    facetype = gDialog.currentScheme.getFaceType(gDialog.currentLanguage, style);
    gDialog.specificFaceType.selectedIndex = 1-facetype;
}

function updateSchemeColor(colorid) {
    try {
        var colorvalue = gDialog.currentScheme.getColor(colorid);
        gDialog.schemeColorPicker.color = colorvalue;
    } catch (e) {
        log.error(e);
    }
}

function updateSubLanguageBackgroundField(checkbox)
{
    if (checkbox.checked) {
        gDialog.specificBackBySubLanguage.removeAttribute("disabled");
        document.getElementById("specificColorPickerSubLanguageBack_customColorPicker").removeAttribute("disabled");
        document.getElementById("specificColorPickerSubLanguageBack_label").removeAttribute("disabled");
    } else {
        gDialog.specificBackBySubLanguage.setAttribute("disabled", true);
        document.getElementById("specificColorPickerSubLanguageBack_customColorPicker").setAttribute("disabled", true);
        document.getElementById("specificColorPickerSubLanguageBack_label").setAttribute("disabled", true);
    }
}

function checkSubLanguageBackground(checkbox) {
    if (!ensureWriteableScheme()) return;
    gDialog.currentScheme.setGlobalSubLanguageBackgroundEnabled(gDialog.currentLanguage,
                                                         checkbox.checked);
    updateSubLanguageBackgroundField(checkbox);
}

function generateFontList()
{
try {
    // get all the fonts on the system
    var strFontSpecs;
    var j;
    var fontmap = {};
    var re = /^([^-]+)-([^-]+)/;
    var fMono = {};
    var fName = "";
    for (var i=0;i<gFontLanguages.length;i++) {
// #if PLATFORM == 'linux'
        strFontSpecs = enumerator.EnumerateFonts(gFontLanguages[i],
                                                 'sans',
                                                 new Object());
        var fontspec;
        for (j=0; j < strFontSpecs.length; j++) {
            if (typeof(fontmap[strFontSpecs[j]])=='undefined' ||
                !fontmap[strFontSpecs[j]]) {
                fontmap[strFontSpecs[j]] = strFontSpecs[j];
            }
        }
// #else
        for (var t = 0; t < gFontTypes.length; t++ )
        {
            // build and populate the font list for the newly chosen font type
            strFontSpecs = enumerator.EnumerateFonts(gFontLanguages[i],
                                                     gFontTypes[t],
                                                     new Object());
            for (j=0; j < strFontSpecs.length; j++) {
                fName = strFontSpecs[j];
                if (typeof(fontmap[fName])=='undefined' ||
                    !fontmap[fName]) {
                    fontmap[fName]=fName;
                }
            }
        }
// #endif
    }
// #if PLATFORM == 'win' or PLATFORM == 'darwin'
    // Did we miss any?
    // Assume unrecognized fonts are proportional
    var allLanguages = enumerator.EnumerateAllFonts({});
    var lang;
    var lim = allLanguages.length;
    for (i = 0; i < lim; i++) {
        fName = allLanguages[i];
        if (!fName) continue;
        fontmap[fName]=fName;
    }
// #endif

    gFontNames = Object.keys(fontmap);

} catch (e) {
    log.exception(e);
}
}

function initFontsMenulist()  {
    // Do all fonts list first
    var fontsElement = new listElement( 'fontlist' );
    fontsElement.clearList();
    fontsElement.appendStrings(gFontNames, null);
}

function customColor(colorpickerid) {
    var colorpicker = document.getElementById(colorpickerid);
    var color = "#" + colorpicker.color.replace(/^#/, "");
    // Prefer the locally preferenced color picker:
    var picker = null;
    var cid = gDialog.prefset.getStringPref("colorpicker_cid");
    if (cid) {
        try {
            picker = Components.classes[cid]
                               .getService(Components.interfaces.koIColorPickerAsync);
        } catch (ex) {
            log.exception(ex, "Unable to load the colorpicker with CID: " + cid);
            picker = null;
        }
    }
    if (!picker) {
        // Use the sysUtils color picker then:
        picker = Components.classes['@activestate.com/koSysUtils;1']
                           .getService(Components.interfaces.koIColorPickerAsync);
    }
    picker.pickColorAsync(function(newcolor) {
        if (newcolor) {
            if (!ensureWriteableScheme()) return;
            colorpicker.color = newcolor;
            setColour(colorpicker);
        }
    }, color, 1.0, colorpicker.boxObject.screenX, colorpicker.boxObject.screenY);
}

function updateLanguage()
{
    try {
        loadSample();
        updateSpecificPopup();
    } catch (e) {
        log.error(e);
    }
}

function changeLanguage() {
    gDialog.currentLanguage = gDialog.languageList.selection;
    updateLanguage();
    updateScintilla();
}

function updateFonts()  {
    // order is font, size, back, fore, italic, bold

    var fLabel = gDialog.currentScheme.getFont(faceIdentifier());
    var fSize = gDialog.currentScheme.getSize('', faceIdentifier());
    var fSpace = gDialog.currentScheme.getLineSpacing(faceIdentifier());

    gDialog.fontList.setAttribute('label', fLabel);
    gDialog.fontList.selectedIndex = gFontNames.indexOf(fLabel);
    gDialog.fontSize.setAttribute('label', fSize);
    gDialog.fontSize.selectedItem = document.getElementById('fontSize_'+fSize);

    var fore, back, italic, bold, face;
    // do fixed width
    fore = gDialog.currentScheme.getFore('', faceIdentifier());
    gDialog.fontColorPickerFore.color = fore;
    back = gDialog.currentScheme.getBack('', faceIdentifier());
    gDialog.fontColorPickerBack.color = back;
    // bold/italic
    var fontBold = gDialog.currentScheme.getBold('', faceIdentifier());
    setCheckboxButton(gDialog.fontBold, fontBold);
    var fontItalic = gDialog.currentScheme.getItalic('', faceIdentifier());
    setCheckboxButton(gDialog.fontItalic, fontItalic);
    // line spacing
    gDialog.fontLineSpacing.value = fSpace;
}

function faceIdentifier() {
    return 'default_' + (gDialog.currentScheme.preferFixed ? 'fixed' : 'proportional');
}

function onSampleBlur() {
    //dump("got onSampleBlur\n");
    try {
        gDialog.bufferView.scimoz.caretPeriod = 0;
    } catch (e) {
        log.error(e);
    }
}

function onSampleFocus()
{
    try {
        //dump('in focus\n');
        gDialog.bufferView.scimoz.caretPeriod = 500;
    } catch (e) {
        log.error(e);
    }
}

function listElement( aListID )
{
    this.listElement = document.getElementById( aListID );
}

listElement.prototype =
{
    clearList:
      function ()
        {
          // removing the menupopup node child of the menulist seems to die!
          // so just remove all *its* child nodes.
          var popup = this.listElement.firstChild;
          while (popup.childNodes.length)
              popup.removeChild( popup.firstChild );
        },

    appendString:
      function ( aString )
        {
          var popupNode;
          popupNode = this.listElement.firstChild;
          if (!popupNode)  {  //clearList may have been called
              popupNode = document.createElement( "menupopup" );
          }

          var itemNode = document.createElement( "menuitem" );
          itemNode.setAttribute( "value", aString );
          itemNode.setAttribute( "label", aString );
          this.listElement.removeAttribute( "disabled" );
          popupNode.appendChild( itemNode );
          this.listElement.appendChild( popupNode );
        },

    appendStrings:
      function ( faces, specs )
        {
          var popupNode;
          popupNode = this.listElement.firstChild;
          if (!popupNode)  {  //clearList may have been called
              log.error("This should never be called - we no longer ever delete the menupopup!!!\n");
              popupNode = document.createElement( "menupopup" );
              this.listElement.appendChild( popupNode );
          }

          // Be sure to add the current font
          var currFont = gDialog.currentScheme.getFont(faceIdentifier());
          if (faces.indexOf(currFont) == -1) {
              faces.push(currFont);
          }
          faces.sort();
          for( var i = 0; i < faces.length; i++ )
            {
              if( faces[i] == "" )
                {
                  this.listElement.setAttribute( "value", "" );
                  this.listElement.setAttribute( "label", "No fonts available for this language" );
                  this.listElement.setAttribute( "disabled", "true" );
                }
              else
                {
                  var itemNode = document.createElement( "menuitem" );
                  if (specs) {
                    itemNode.setAttribute( "value", specs[faces[i]] );
                  } else {
                    itemNode.setAttribute( "value", faces[i] );
                  }
                  itemNode.setAttribute( "label", faces[i] );
                  // for debug purposes, you may want the fontspec
                  //itemNode.setAttribute( "label", specs[faces[i]] );
                  this.listElement.removeAttribute( "disabled" );
                  popupNode.appendChild( itemNode );
                }
            }
        }
};

function loadIndicatorSample()
{
    var names = new Array();
    gDialog.schemeService.getIndicatorNames(names, new Object());
    names = names.value;
    gDialog.bufferView.initWithBuffer("", "Text");
    /**
     * @type {Components.interfaces.ISciMoz}
     */
    var scimoz = gDialog.bufferView.scimoz;
    var text_prefix = _bundle.GetStringFromName("indicator_sample.prefix.text");
    var text_suffix = _bundle.GetStringFromName("indicator_sample.suffix.text");
    var marker_start, marker_length;
    var indic_no;
    var indic_name;
    for (var i=0; i< names.length; i++) {
        indic_no = gDialog.schemeService.getIndicatorNoForName(names[i]);
        scimoz.addText(ko.stringutils.bytelength(text_prefix), text_prefix);
        marker_start = scimoz.length;
        indic_name = _bundle.GetStringFromName(names[i]);
        marker_length = ko.stringutils.bytelength(indic_name);
        scimoz.addText(marker_length, indic_name);
        scimoz.addText(ko.stringutils.bytelength(text_suffix), text_suffix);
        scimoz.newLine();
        if (indic_no >= 0) {
            scimoz.indicatorCurrent = indic_no;
            scimoz.indicatorFillRange(marker_start, marker_length);
        }
    }
    gDialog.bufferView.anchor = 0;
    gDialog.bufferView.currentPos = 0;
}

function updateIndicatorStyle()
{
    var indicator_name = gDialog.indicator_menulist.value;
    if (!indicator_name) {
        return;
    }
    var style = {};
    var color = {};
    var alpha = {};
    var draw_underneath = {};
    gDialog.currentScheme.getIndicator(indicator_name, style, color,
                                       alpha, draw_underneath);
    style = style.value;
    color = color.value;
    alpha = alpha.value;
    draw_underneath = draw_underneath.value;

    gDialog.indicator_style_menulist.value = style;
    gDialog.indicator_color.color = color;
    gDialog.indicator_alpha_textbox.value = alpha;
    gDialog.indicator_draw_underneath_checkbox.checked = draw_underneath;
}

function setIndicator() {
    if (!ensureWriteableScheme()) {
        return;
    }
    var indic_name = gDialog.indicator_menulist.value;
    var style = gDialog.indicator_style_menulist.value;
    var color = gDialog.indicator_color.color;
    var alpha = parseInt(gDialog.indicator_alpha_textbox.value);
    var draw_underneath = gDialog.indicator_draw_underneath_checkbox.checked;
    gDialog.currentScheme.setIndicator(indic_name, style, color, alpha,
                                       draw_underneath);
    updateScintilla();
}

function updateIndicatorPopup()
{
    try {
        var labels = new Array();
        gDialog.schemeService.getIndicatorNames(labels, new Object());
        labels = labels.value;
        var popup = document.getElementById('indicator_popup');
        // clean out whatever may be there
        while (popup.firstChild) {
            popup.removeChild(popup.firstChild);
        }
        for (var i=0; i< labels.length; i++) {
            var item = document.createElement('menuitem');
            item.setAttribute('value', labels[i]);
            // Localize the menu label.
            item.setAttribute('label', _bundle.GetStringFromName(labels[i]));
            popup.appendChild(item);
        }
        _restorePopupMenuIndex(gDialog.indicator_menulist, labels,
                               "prefs.fontsColorsLanguages.indicators.menulist");
        updateIndicatorStyle();
    } catch (e) {
        log.error(e);
    }
}

// Fired when the tab/tabpanel is changed.
function tabChanged() {
    if (!gDialog) {
        // Dialog is still loading.
        return;
    }
    var tabId = gDialog.tabbox.selectedTab.getAttribute("id");
    if (tabId == "indicator_tab") {
        // Switched to the indicator tab. Fire this in a timeout, in order
        // to ensure this is called after the changeLanguage() call, which
        // gets fires on the initial page load.
        window.setTimeout(loadIndicatorSample, 1);
    } else if (gDialog.current_tab_id == "indicator_tab") {
        // Switched from the indicator tab.
        changeLanguage();
    }
    gDialog.current_tab_id = tabId;
}

function _get_registered_colorpickers() {
    var result = [];
    var catMgr = Components.classes["@mozilla.org/categorymanager;1"].
                    getService(Components.interfaces.nsICategoryManager);
    var category = 'colorpicker';
    var names = catMgr.enumerateCategory(category);
    var nameObj;
    var name;
    var cid;
    var shortPlatName = navigator.platform.substr(0, 3);
    while (names.hasMoreElements()) {
        nameObj = names.getNext();
        nameObj.QueryInterface(Components.interfaces.nsISupportsCString);
        name = nameObj.data;
        cid = catMgr.getCategoryEntry(category, name);
        if ((name == "windows_system_color_picker" && shortPlatName == "Win") ||
            (name == "macosx_system_color_picker" && shortPlatName == "Mac")) {
            // We want the default system color picker to be first in the list.
            result.splice(0, 0, {"name": name, "cid": cid});
        } else {
            result.push({"name": name, "cid": cid});
        }
    }
    return result;
}

function loadColorpickerPreferences(prefset) {
    var menulist = document.getElementById("colorpicker_menulist");
    var menupopup = document.getElementById("colorpicker_menupopup");
    var menuitem;
    var colorpicker_cid = prefset.getStringPref("colorpicker_cid");
    var colorpickers = _get_registered_colorpickers();
    var selectedIndex = 0;
    for (var i=0; i < colorpickers.length; i++) {
        menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", colorpickers[i].name);
        menuitem.setAttribute("cid", colorpickers[i].cid);
        menupopup.appendChild(menuitem);
        if (colorpicker_cid == colorpickers[i].cid) {
            selectedIndex = i;
        }
    }
    menulist.selectedIndex = selectedIndex;
}

function setFontQuality() {
    var menulist = document.getElementById("editor_font_quality");
    if (menulist.selectedItem) {
        let scimoz = gDialog.bufferView.scimoz;
        scimoz.fontQuality = parseInt(menulist.selectedItem.getAttribute("data"));
    }
}

function setColorpicker() {
    var menulist = document.getElementById("colorpicker_menulist");
    if (menulist.selectedItem) {
        gDialog.prefset.setStringPref("colorpicker_cid", menulist.selectedItem.getAttribute("cid"));
    }
}

function testColorpicker() {
    var menulist = document.getElementById("colorpicker_menulist");
    if (menulist.selectedItem) {
        var cid = menulist.selectedItem.getAttribute("cid");
        try {
            var cp = Components.classes[cid]
                               .createInstance(Components.interfaces.koIColorPickerAsync);
            cp.pickColorAsync(function(){}, "#00ACDC", 1.0,
                              menulist.boxObject.screenX,
                              menulist.boxObject.screenY);
        } catch (ex) {
            ko.dialogs.alert("Could not instantiate this color picker", ex);
        }
    }
}
