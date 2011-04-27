/*
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Initial Developer of the Original Code is
# Davide Ficano.
# Portions created by the Initial Developer are Copyright (C) 2007
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Davide Ficano <davide.ficano@gmail.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
*/
if (typeof(extensions) == 'undefined') {
    var extensions = {};
}

if (typeof(extensions.dafizilla) == 'undefined') {
    extensions.dafizilla = {};
}

if (typeof(extensions.dafizilla.klint) == 'undefined') {
    extensions.dafizilla.klint = {};
}

extensions.dafizilla.klint.commonUtils = {};

(function() {
    var locale = Components.classes["@mozilla.org/intl/stringbundle;1"]
        .getService(Components.interfaces.nsIStringBundleService)
        .createBundle("chrome://klint/locale/klint.properties");

    this.getLocalizedMessage = function(msg) {
        return locale.GetStringFromName(msg);
    };

    this.getFormattedMessage = function(msg, ar) {
        return locale.formatStringFromName(msg, ar, ar.length);
    };

    this.getObserverService = function () {
        const CONTRACTID_OBSERVER = "@mozilla.org/observer-service;1";
        const nsObserverService = Components.interfaces.nsIObserverService;

        return Components.classes[CONTRACTID_OBSERVER].getService(nsObserverService);
    };

    this.log = function(message) {
        ko.logging.getLogger("klint").warn((new Date()) + ": " + message);
    };

    this.debug = function(message) {
        Components.classes["@mozilla.org/consoleservice;1"]
            .getService(Components.interfaces.nsIConsoleService)
                .logStringMessage(message);
    };
}).apply(extensions.dafizilla.klint.commonUtils);