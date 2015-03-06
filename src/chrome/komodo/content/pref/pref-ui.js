function PrefUi_OnLoad() {
    
    const {interfaces: Ci} = Components;
    Components.utils.import("resource://gre/modules/Services.jsm");

    var iconSelector    = document.getElementById('koSkin_custom_icons');
    var skinSelector    = document.getElementById('koSkin_custom_skin')

    /*
     * Update the selected icon set relative to the selected skin
     */
    var updateIconSetSel = function()
    {
        var iconSet = skinSelector.selectedItem.getAttribute('iconset');
        if ( ! iconSet)
        {
            return;
        }

        var iconSetElem = iconSelector.querySelector('menuitem#pref_appearance_iconset_' + iconSet);
        if (iconSetElem)
        {
            iconSelector.selectedItem = iconSetElem;
        }
    };

    // Update the selected iconset when a skin is changed (if required)
    skinSelector.addEventListener('select', updateIconSetSel);

    // Hide the skin selector if there are no skins
    var items = skinSelector.querySelectorAll('menuitem');
    document.getElementById('pref_appearance_skin_hbox').collapsed = (items.length == 0);

    // If gtk detection is true, disable the skin selection
    if (window.navigator.platform.toLowerCase().indexOf("linux") != -1)
    {
        var checkboxDetect  = document.getElementById('koSkin_use_gtk_detection');
        var menuSkin        = document.getElementById('koSkin_custom_skin');
        var menuIcons       = document.getElementById('koSkin_custom_icons');

        var setSkinState = function()
        {
            menuSkin.disabled = checkboxDetect.checked;
            menuIcons.disabled = checkboxDetect.checked;

            // If gtk detection is enabled, detect the current gtk theme
            // and select the relevant komodo skin (if available)
            if (checkboxDetect.checked)
            {
                getKoObject('skin').gtk.getThemeInfo(function(themeInfo)
                {
                    var skinFile = getKoObject('skin').gtk.resolveSkin(themeInfo);
                    var menuItemValue =  "";
                    if (skinFile)
                    {
                        menuItemValue = skinFile;
                    }

                    var menuItem = skinSelector.querySelector('menuitem[value="' + menuItemValue + '"]');
                    if (menuItem)
                    {
                        if (skinSelector.selectedItem == menuItem)
                        {
                            updateIconSetSel();
                        }
                        else
                        {
                            skinSelector.selectedItem = menuItem;
                        }
                    }
                });
            }
        }

        checkboxDetect.addEventListener('click', setSkinState);
    }
    
    var ssCheck = document.getElementById('koSkin_scheme_skinning');
    var csCheck = document.getElementById('koSkin_use_custom_scrollbars');
    
    var setSchemeSkinningState = function()
    {
        if ( ! ssCheck.checked) csCheck.checked = false;
        csCheck.disabled = ! ssCheck.checked;
    }
    
    ssCheck.addEventListener('click', setSchemeSkinningState);

    // Run default actions (load prefs and their selected state)
    parent.hPrefWindow.onpageload();

    if (window.navigator.platform.toLowerCase().indexOf("linux") != -1)
    {
        setSkinState();
    }
    
    setSchemeSkinningState();
}
