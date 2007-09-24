/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
    _boingAvail_px;
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
