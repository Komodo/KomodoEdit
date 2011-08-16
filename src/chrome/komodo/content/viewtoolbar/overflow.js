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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2011
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

/**
 * View toolbar handling.
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (typeof(ko.viewtoolbar)=='undefined') {
    ko.viewtoolbar = {};
}
if (typeof(ko.viewtoolbar.overflow)!='undefined') {
    ko.logging.getLogger('').warn("ko.viewtoolbar.overflow was already loaded, re-creating it.\n");
}
ko.viewtoolbar.overflow = {};

(function() {

    //---- Private variables.

    var log = ko.logging.getLogger("viewtoolbar:overflow");
    //log.setLevel(ko.logging.LOG_DEBUG);

    var viewtoolbarController;

    //---- Private routines.


    //---- Public routines.

    /**
     * Initialize the toolbar overflow menu for the given view.
     * @param {Components.interfaces.koIView} view
     * @param {DOMElement} overflowMenupopup
     */
    this.initializeMenu = function viewtoolbar_overflow_initialzeMenu(view, overflowMenupopup)
    {
        if (!overflowMenupopup.hasAttribute("overflow_menu_initialized")) {
            // Build the menupopup entries.
            var viewtoolbar = view.toolbar;
            for (var i=0; i < viewtoolbar.childNodes.length; i++) {
                let childNode = viewtoolbar.childNodes[i];
                if (childNode.style.visibility == "hidden" &&
                    childNode.localName.substr(0, 7) == "toolbar") {
                    // Add it to the overflow menu.
                    let overflowNode = overflowMenupopup.appendChild(childNode.cloneNode(true));
                    // Make sure it's visible - as it was cloned as not visible.
                    overflowNode.hidden = false;
                    overflowNode.style.visibility = 'visible';
                }
            }
            overflowMenupopup.setAttribute("overflow_menu_initialized", "true");
        }
    }

    /**
     * Tear down the toolbar overflow menu for the given view.
     * @param {Components.interfaces.koIView} view
     * @param {DOMElement} overflowMenupopup
     */
    this.teardownMenu = function viewtoolbar_overflow_initialzeMenu(view, overflowMenupopup)
    {
        // Remove all existing overflow entries.
        while (overflowMenupopup.lastChild) {
            overflowMenupopup.removeChild(overflowMenupopup.lastChild);
        }
        overflowMenupopup.removeAttribute("overflow_menu_initialized");
    }

}).apply(ko.viewtoolbar.overflow);
