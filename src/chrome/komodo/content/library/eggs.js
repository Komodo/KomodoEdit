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

if (typeof(ko)=='undefined') {
    var ko = {};
}
ko.eggs = {};
(function() {
var _boingInterval = null;
var _boingA, _boingV, _boingT, _boingC, _boingPxPerM, _boingD,
    _boingAvail_px, _boingRemainder_px, _boingD_px, _boingBouncedLastStep,
    _boingStep;

this.boing = function() {
    _boingA = 9.81; // gravity
    _boingV = 0.0; // initial y velocity (positive is down)
    _boingT = 0.010; //time interval
    _boingC = 0.8; //coefficient of energy loss on _boingA bounce
    _boingPxPerM = 200.0;
    _boingD = 0.0;
    _boingRemainder_px =0.0;
    _boingD_px = 0.0;
    _boingBouncedLastStep = 0;
    _boingStep = 0;

    if (_boingInterval != null) {
        window.clearInterval(_boingInterval);
        _boingInterval = null;
    }
    _boingInterval = window.setInterval(_BoingABit, 10)
}

function _BoingABit() {
    if (_boingStep >= 500) {
        window.clearInterval(_boingInterval);
        _boingInterval = null;
        return
    }

    // how far to fall (or rise)
    _boingD = _boingV * _boingT;
    _boingD_px = _boingD * _boingPxPerM + _boingRemainder_px;

    // save remainder for next _boingStep (or could .round() to try to even out)
    if (_boingD_px < 0.0) { // workaround JS's broken modulus operator
        _boingRemainder_px = 1.0 - (Math.abs(_boingD_px) % 1.0);
    } else {
        _boingRemainder_px = _boingD_px % 1.0;
    }
    _boingD_px = Math.floor(_boingD_px);

    // handle _boingA bounce and move
    _boingAvail_px = screen.availHeight - (window.screenY + window.outerHeight)
    if (_boingD_px >= _boingAvail_px) { // bounce
        _boingV = -_boingV*_boingC;
        _boingD_px = _boingAvail_px - (_boingD_px-_boingAvail_px)*_boingC;
        if (_boingBouncedLastStep) {
            window.clearInterval(_boingInterval);
            _boingInterval = null;
            return;
        }
        _boingBouncedLastStep = 1;
    } else {
        _boingBouncedLastStep = 0;
    }

    //dump("_boingStep " + _boingStep + ": _boingV=" + _boingV + ", _boingD_px=" + _boingD_px + " _boingRemainder_px=" + _boingRemainder_px + '\n');
    window.moveBy(0, _boingD_px);

    _boingStep += 1;
    _boingV += _boingA * _boingT; // accelerate
}
}).apply(ko.eggs);
