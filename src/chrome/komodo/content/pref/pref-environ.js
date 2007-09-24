/* Copyright (c) 2005-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */


//---- globals

var log = ko.logging.getLogger("pref-environ");
//log.setLevel(ko.logging.LOG_DEBUG);

var gEnvironUserShellPref = null;




//---- functions for XUL

function PrefEnviron_OnLoad()
{
    log.info("PrefEnviron_OnLoad");
    try {
        parent.hPrefWindow.onpageload();
    } catch(ex) {
        log.exception(ex);
    }
}


// Populate the list of available system shells.
function OnPreferencePageInitalize()
{
    var env_sys = document.getElementById('env-sys');
    env_sys.onpageload();
    env_sys.uservars = document.getElementById('user-env-prefs');
    var environment = Components.classes["@activestate.com/koUserEnviron;1"]
                        .getService(Components.interfaces.koIUserEnviron)
                        .GetEncodedStartupEnvironment();
    env_sys.value = environment;
}


